# -*- coding: utf-8 -*-
"""Customer lifecycle states v1 — dashboard truth classification."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone

from extensions import db
from models import MerchantCartLifecycleArchive, RecoverySchedule
from schema_merchant_cart_lifecycle_archive import (
    ensure_merchant_cart_lifecycle_archive_schema,
    reset_merchant_cart_lifecycle_archive_schema_guard_for_tests,
)
from schema_recovery_truth_timeline import (
    ensure_recovery_truth_timeline_schema,
    reset_recovery_truth_timeline_schema_guard_for_tests,
)
from services.customer_lifecycle_states_v1 import (
    STATE_ARCHIVED,
    STATE_CUSTOMER_ENGAGED,
    STATE_CUSTOMER_REPLY,
    STATE_RETURN_TO_SITE,
    STATE_WAITING_CUSTOMER_REPLY,
    STATE_WAITING_NEXT_SCHEDULED,
    STATE_WAITING_PURCHASE_WINDOW,
    attach_customer_lifecycle_state_v1,
    classify_customer_lifecycle_state_v1,
)
from services.merchant_cart_lifecycle_archive_v1 import (
    archive_recovery_key,
    is_merchant_archived,
    reopen_recovery_key,
)
from services.recovery_restart_survival import STATUS_SCHEDULED
from services.recovery_truth_timeline_v1 import (
    STATUS_CONTINUATION_STARTED,
    STATUS_CUSTOMER_REPLY,
    STATUS_PROVIDER_SENT,
    record_recovery_truth_event,
)


class CustomerLifecycleStatesV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        reset_recovery_truth_timeline_schema_guard_for_tests()
        reset_merchant_cart_lifecycle_archive_schema_guard_for_tests()

    def setUp(self) -> None:
        db.create_all()
        ensure_recovery_truth_timeline_schema(db)
        ensure_merchant_cart_lifecycle_archive_schema(db)
        self._suffix = uuid.uuid4().hex[:8]

    def tearDown(self) -> None:
        try:
            db.session.query(RecoverySchedule).filter(
                RecoverySchedule.recovery_key.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(MerchantCartLifecycleArchive).filter(
                MerchantCartLifecycleArchive.recovery_key.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_customer_reply_shows_engaged_not_waiting(self) -> None:
        rk = f"demo:lc-reply-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CUSTOMER_REPLY,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CONTINUATION_STARTED,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            sent_count=1,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
        )
        self.assertEqual(lc.state_key, STATE_CUSTOMER_ENGAGED)
        self.assertIn("تفاعل العميل", lc.label_ar)
        self.assertIn("متابعة", lc.label_ar)
        self.assertNotIn("بانتظار تفاعل العميل", lc.label_ar)

    def test_customer_reply_without_continuation_is_reply_only(self) -> None:
        rk = f"demo:lc-reply-only-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CUSTOMER_REPLY,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            sent_count=1,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent"}),
            coarse="replied",
            behavioral={"customer_replied": True},
        )
        self.assertEqual(lc.state_key, STATE_CUSTOMER_REPLY)
        self.assertEqual(lc.label_ar, "رد العميل")
        self.assertNotIn("تفاعل العميل", lc.label_ar)

    def test_return_to_site_not_customer_engaged(self) -> None:
        rk = f"demo:lc-return-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            phase_key="customer_returned",
            coarse="returned",
            sent_count=1,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent", "returned_to_site"}),
            behavioral={"customer_returned_to_site": True},
        )
        self.assertEqual(lc.state_key, STATE_WAITING_PURCHASE_WINDOW)
        self.assertIn("أوقفنا المتابعة مؤقتًا", lc.label_ar)
        self.assertNotIn("تفاعل العميل", lc.label_ar)
        self.assertNotIn("أرسل النظام متابعة", lc.system_did_ar)
        self.assertEqual(lc.dashboard_action, "none")
        self.assertNotIn("مؤرشفة", lc.label_ar)

    def test_return_after_send_stays_active_not_terminal_history(self) -> None:
        rk = f"demo:lc-ret-active-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        payload: dict[str, object] = {}
        lc = attach_customer_lifecycle_state_v1(
            payload,
            recovery_key=rk,
            phase_key="customer_returned",
            coarse="returned",
            sent_count=1,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent", "returned_to_site"}),
            behavioral={"user_returned_to_site": True},
            terminal_history_archived=True,
        )
        self.assertEqual(lc.state_key, STATE_WAITING_PURCHASE_WINDOW)
        self.assertTrue(payload.get("merchant_cart_is_active"))
        self.assertFalse(payload.get("merchant_cart_is_terminal"))
        self.assertFalse(payload.get("customer_lifecycle_is_archived_visual"))

    def test_ignored_with_future_schedule_waiting_next(self) -> None:
        rk = f"demo:lc-ign-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        due = datetime.now(timezone.utc) + timedelta(days=2)
        row = RecoverySchedule(
            recovery_key=rk,
            store_slug="demo",
            session_id=f"s_{self._suffix}",
            scheduled_at=datetime.now(timezone.utc),
            due_at=due,
            effective_delay_seconds=172800.0,
            delay_source="test",
            status=STATUS_SCHEDULED,
            step=2,
            multi_slot_index=-1,
        )
        db.session.add(row)
        db.session.commit()
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            phase_key="ignored",
            coarse="ignored",
            sent_count=1,
            attempt_cap=3,
            log_statuses=frozenset({"mock_sent"}),
        )
        self.assertEqual(lc.state_key, STATE_WAITING_NEXT_SCHEDULED)
        self.assertIn("المتابعة القادمة بعد", lc.next_followup_line_ar)
        self.assertNotIn("مغلق", lc.label_ar)

    def test_exhausted_no_reply_stays_waiting_after_sequence_skip_log(self) -> None:
        rk = f"demo:lc-exh-{self._suffix}"
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            sent_count=2,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent", "skipped_attempt_limit"}),
            coarse="sent",
        )
        self.assertEqual(lc.state_key, STATE_WAITING_CUSTOMER_REPLY)
        self.assertNotEqual(lc.state_key, STATE_ARCHIVED)

    def test_full_sequence_sent_without_skip_log_stays_sent_not_archived(self) -> None:
        """All templates sent (sent_count == cap) must not auto-archive."""
        rk = f"demo:lc-full-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            sent_count=2,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent", "mock_sent"}),
            coarse="sent",
        )
        self.assertEqual(lc.state_key, STATE_WAITING_CUSTOMER_REPLY)
        self.assertNotEqual(lc.state_key, STATE_ARCHIVED)

    def test_manual_archive_and_reopen(self) -> None:
        rk = f"demo:lc-arch-{self._suffix}"
        out = archive_recovery_key(recovery_key=rk, store_slug="demo")
        self.assertTrue(out.get("ok"))
        self.assertTrue(is_merchant_archived(rk))
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            merchant_archived=True,
        )
        self.assertEqual(lc.state_key, STATE_ARCHIVED)
        self.assertEqual(lc.dashboard_action, "reopen")
        self.assertTrue(lc.to_payload_fields()["customer_lifecycle_is_archived_visual"])
        reopen = reopen_recovery_key(rk)
        self.assertTrue(reopen.get("ok"))
        self.assertFalse(is_merchant_archived(rk))

    def test_sent_without_reply_waiting_customer(self) -> None:
        rk = f"demo:lc-wait-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            sent_count=1,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
        )
        self.assertEqual(lc.state_key, STATE_WAITING_CUSTOMER_REPLY)

    def test_provider_sent_not_archived_when_attempt_limit_skip_early(self) -> None:
        """Step-2 skip log must not archive after first send (cap=1 or partial cap)."""
        rk = f"demo:lc-cap1-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            sent_count=1,
            attempt_cap=1,
            log_statuses=frozenset({"mock_sent", "skipped_attempt_limit"}),
            coarse="sent",
            terminal_history_archived=True,
        )
        self.assertEqual(lc.state_key, STATE_WAITING_CUSTOMER_REPLY)
        self.assertNotEqual(lc.state_key, STATE_ARCHIVED)

    def test_terminal_history_with_provider_sent_stays_waiting(self) -> None:
        rk = f"demo:lc-term-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            sent_count=1,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent", "skipped_attempt_limit"}),
            coarse="sent",
            terminal_history_archived=True,
        )
        self.assertEqual(lc.state_key, STATE_WAITING_CUSTOMER_REPLY)

    def test_reopen_idempotent_without_persisted_row(self) -> None:
        rk = f"demo:lc-reopen-{self._suffix}"
        out = reopen_recovery_key(rk)
        self.assertTrue(out.get("ok"))
        self.assertFalse(out.get("archived"))


if __name__ == "__main__":
    unittest.main()
