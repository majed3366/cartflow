# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from models import AbandonedCart
from services import cartflow_lifecycle_guard as lg
from services import cartflow_runtime_health as rh
from services.behavioral_recovery.state_store import merge_behavioral_state


class CartflowLifecycleConsistencyTests(unittest.TestCase):
    def tearDown(self) -> None:
        lg.reset_lifecycle_guard_for_tests()
        rh.clear_runtime_anomaly_buffer_for_tests()
        try:
            from services.cartflow_session_consistency import (
                reset_session_consistency_for_tests,
            )

            reset_session_consistency_for_tests()
        except Exception:
            pass

    def test_valid_transition_chain(self) -> None:
        self.assertTrue(lg.is_valid_transition(lg.STATE_ABANDONED, lg.STATE_QUEUED))
        self.assertTrue(lg.is_valid_transition(lg.STATE_QUEUED, lg.STATE_SENT))

    def test_invalid_transition_conversion_to_sent(self) -> None:
        self.assertFalse(
            lg.is_valid_transition(lg.STATE_CONVERTED, lg.STATE_SENT),
        )

    def test_explain_send_after_patterns(self) -> None:
        self.assertEqual(
            lg.explain_invalid_transition_pair(lg.STATE_CONVERTED, lg.STATE_SENT),
            "sent_after_conversion",
        )
        self.assertEqual(
            lg.explain_invalid_transition_pair(lg.STATE_REPLIED, lg.STATE_SEND_STARTED),
            "send_after_reply",
        )

    def test_validate_and_log_emits(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            ok = lg.validate_and_log_transition(
                lg.STATE_CONVERTED,
                lg.STATE_SENT,
                store_slug="demo",
                session_id="s",
                cart_id="c",
            )
        self.assertFalse(ok)
        out = buf.getvalue()
        self.assertTrue("[CARTFLOW LIFECYCLE]" in out or "[CARTFLOW STATE CONFLICT]" in out)

    def test_reconcile_duplicate_suppressed_after_send(self) -> None:
        r = lg.reconcile_normal_recovery_dashboard_hints(
            store_slug="demo",
            session_id="s1",
            cart_id="c1",
            phase_key="first_message_sent",
            sent_ct=1,
            latest_log_status="skipped_duplicate",
            behavioral={},
            blocker_key="duplicate_attempt_blocked",
            blocker_bundle={"key": "duplicate_attempt_blocked", "label_ar": "محاولة مكررة"},
            seq_label_ar="تم إرسال الرسالة الأولى",
            operational_hint_ar=None,
        )
        self.assertIsNone(r.get("blocker_key"))
        self.assertIn("suppressed_duplicate_after_send", r.get("lifecycle_notes") or [])

    def test_reconcile_duplicate_replaced_with_user_returned_when_behavioral_return(self) -> None:
        r = lg.reconcile_normal_recovery_dashboard_hints(
            store_slug="demo",
            session_id="s-ur",
            cart_id="c-ur",
            phase_key="pending_send",
            sent_ct=0,
            latest_log_status="skipped_duplicate",
            behavioral={"user_returned_to_site": True},
            blocker_key="duplicate_attempt_blocked",
            blocker_bundle={"key": "duplicate_attempt_blocked", "label_ar": "محاولة مكررة"},
            seq_label_ar=None,
            operational_hint_ar=None,
        )
        self.assertEqual(r.get("blocker_key"), "user_returned")

    def test_reconcile_duplicate_replaced_when_durable_return_in_log_union(self) -> None:
        r = lg.reconcile_normal_recovery_dashboard_hints(
            store_slug="demo",
            session_id="s-dur",
            cart_id="c-dur",
            phase_key="pending_second_attempt",
            sent_ct=0,
            latest_log_status="skipped_duplicate",
            behavioral={},
            blocker_key="duplicate_attempt_blocked",
            blocker_bundle={"key": "duplicate_attempt_blocked", "label_ar": "محاولة مكررة"},
            seq_label_ar=None,
            operational_hint_ar=None,
            recovery_log_statuses=frozenset({"returned_to_site", "skipped_duplicate"}),
        )
        self.assertEqual(r.get("blocker_key"), "user_returned")
        bb = r.get("blocker_bundle")
        self.assertIsInstance(bb, dict)
        assert isinstance(bb, dict)
        self.assertEqual(bb.get("key"), "user_returned")
        self.assertIn("عاد", str(bb.get("label_ar") or ""))
        self.assertIn(
            "presentation_explicit_stop_after_duplicate",
            r.get("lifecycle_notes") or [],
        )

    def test_reconcile_automation_disabled_replaced_with_user_returned_when_behavioral_return(
        self,
    ) -> None:
        from services.recovery_blocker_display import get_recovery_blocker_display_state

        r = lg.reconcile_normal_recovery_dashboard_hints(
            store_slug="demo",
            session_id="s-ad",
            cart_id="c-ad",
            phase_key="first_message_sent",
            sent_ct=1,
            latest_log_status="skipped_attempt_limit",
            behavioral={"customer_returned_to_site": True},
            blocker_key="automation_disabled",
            blocker_bundle=dict(get_recovery_blocker_display_state("automation_disabled")),
            seq_label_ar=None,
            operational_hint_ar=None,
        )
        self.assertEqual(r.get("blocker_key"), "user_returned")
        bb = r.get("blocker_bundle")
        self.assertIsInstance(bb, dict)
        assert isinstance(bb, dict)
        self.assertEqual(bb.get("key"), "user_returned")
        self.assertIn(
            "presentation_user_return_over_automation_disabled",
            r.get("lifecycle_notes") or [],
        )

    def test_reconcile_conversion_clears_send_seq_label(self) -> None:
        r = lg.reconcile_normal_recovery_dashboard_hints(
            store_slug="demo",
            session_id="s2",
            cart_id="c2",
            phase_key="stopped_purchase",
            sent_ct=1,
            latest_log_status="stopped_converted",
            behavioral={},
            blocker_key="purchase_completed",
            blocker_bundle={"key": "purchase_completed", "label_ar": "شراء"},
            seq_label_ar="تم إرسال الرسالة الأولى",
            operational_hint_ar=None,
        )
        self.assertIsNone(r.get("sequence_label_ar"))

    def test_prune_behavioral_weakens_reply(self) -> None:
        out = lg.prune_behavioral_merge_fields(
            {"customer_replied": True},
            {"customer_replied": False, "user_returned_to_site": True},
            session_id="s",
            cart_id="c",
        )
        self.assertNotIn("customer_replied", out)
        self.assertTrue(out.get("user_returned_to_site") is True)

    def test_merge_behavioral_state_respects_prune(self) -> None:
        ac = AbandonedCart()
        ac.recovery_session_id = "prune-s"
        ac.zid_cart_id = "prune-c"
        ac.raw_payload = json.dumps(
            {"cf_behavioral": {"customer_replied": True}},
            ensure_ascii=False,
        )
        setattr(ac, "id", 999001)
        merge_behavioral_state(ac, customer_replied=False, user_returned_to_site=True)
        data = json.loads(ac.raw_payload or "{}")
        bh = data.get("cf_behavioral") or {}
        self.assertTrue(bh.get("customer_replied") is True)
        self.assertTrue(bh.get("user_returned_to_site") is True)

    def test_runtime_snapshot_has_lifecycle_section(self) -> None:
        snap = rh.build_runtime_health_snapshot()
        self.assertIn("lifecycle_consistency_runtime", snap)
        self.assertIn("lifecycle_runtime_ok", snap["lifecycle_consistency_runtime"])

    def test_merchant_constants_non_empty(self) -> None:
        self.assertIn("تجاهل", lg.MERCHANT_SOFT_IGNORE_INCONSISTENT_AR)


if __name__ == "__main__":
    unittest.main()
