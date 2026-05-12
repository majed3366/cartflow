# -*- coding: utf-8 -*-
"""Normal Recovery dashboard reads successful sends from CartRecoveryLog (mock_sent / sent_real)."""

from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from extensions import db, remove_scoped_session
from main import (
    app,
    _dashboard_recovery_store_row,
    _normal_recovery_cart_alert_list,
    _normal_recovery_merchant_lightweight_alert_list,
    _normal_recovery_phase_steps_payload,
    _NORMAL_RECOVERY_SENT_LOG_STATUSES,
    _vip_dashboard_cart_alert_dict_from_group,
)
from models import AbandonedCart, CartRecoveryLog, Store


class NormalRecoveryDashboardStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]

    def _store_attempts_1(self) -> Store:
        """عزل عن ‎Store‎ لوحة التاجر التي قد تكون ‎recovery_attempts > 1‎ من اختبارات سابقة."""
        st = Store(
            zid_store_id=f"nr-tst-{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        return st

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"nr-tst-{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%-{self._suffix}")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_interactive_mode_dashboard_payload(self) -> None:
        import json

        st = self._store_attempts_1()
        sid = f"nr-int-{self._suffix}"
        zid = f"zid-nr-int-{self._suffix}"
        raw = {
            "cf_behavioral": {
                "customer_replied": True,
                "interactive_mode": True,
                "recovery_conversation_state": "engaged",
                "last_customer_reply_preview": "كم السعر؟",
                "last_customer_reply_at": "2026-01-15T12:00:00+00:00",
                "recovery_reply_intent": "price",
                "latest_customer_message": "كم السعر؟",
                "latest_customer_reply_at": "2026-01-15T12:00:00+00:00",
                "recovery_adaptive_stage": "price_objection",
                "recovery_adaptive_turn_count": 1,
                "recovery_last_transition_reason_ar": "أول رد تفاعلي — بداية المسار وفق نية آخر رسالة.",
                "recovery_adaptive_path_label_ar": "اعتراض سعر → طمأنة → (بديل / عرض ناعم)",
                "recovery_last_offer_strategy_key": "soft_offer_window",
            }
        }
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="+966501111111",
            status="abandoned",
            vip_mode=False,
            cart_value=50.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone="966501111111",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()

        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload["normal_recovery_phase_key"], "behavioral_replied")
        self.assertEqual(payload["normal_recovery_status"], "replied")
        self.assertTrue(payload.get("normal_recovery_interactive_mode"))
        self.assertEqual(payload.get("normal_recovery_conversation_state_key"), "engaged")
        self.assertEqual(payload.get("normal_recovery_reply_intent_key"), "price")
        self.assertTrue(payload.get("normal_recovery_reply_intent_label_ar"))
        reply_ar = payload.get("normal_recovery_suggested_reply_ar") or ""
        self.assertIsInstance(reply_ar, str)
        self.assertGreater(len(reply_ar.strip()), 0)
        strat_ar = payload.get("normal_recovery_suggested_strategy_ar") or ""
        self.assertIsInstance(strat_ar, str)
        self.assertGreater(len(strat_ar.strip()), 0)
        self.assertTrue(payload.get("normal_recovery_suggestion_reason_ar"))
        self.assertEqual(payload.get("normal_recovery_optional_offer_type"), "value_framing")
        self.assertEqual(payload.get("normal_recovery_suggested_action_key"), "reassure_price")
        self.assertIn("normal_recovery_suggestion_ux_badge_ar", payload)
        self.assertIsInstance(payload.get("normal_recovery_suggestion_ux_badge_ar"), str)
        self.assertTrue(payload.get("normal_recovery_offer_decision_type_ar"))
        self.assertTrue(payload.get("normal_recovery_offer_confidence_ar"))
        self.assertTrue(payload.get("normal_recovery_offer_decision_rationale_ar"))
        self.assertTrue(payload.get("normal_recovery_offer_persuasion_ar"))
        self.assertIn("normal_recovery_checkout_push_mode", payload)
        self.assertIsInstance(payload.get("normal_recovery_checkout_push_mode"), bool)
        self.assertEqual(int(payload.get("normal_recovery_adaptive_turn_count") or 0), 1)
        self.assertEqual(
            payload.get("normal_recovery_adaptive_stage_key"), "price_objection"
        )
        self.assertTrue(payload.get("normal_recovery_adaptive_stage_ar"))
        self.assertTrue(payload.get("normal_recovery_adaptive_transition_ar"))
        self.assertTrue(payload.get("normal_recovery_adaptive_path_ar"))

    def test_interactive_dashboard_includes_delivery_suggestion(self) -> None:
        import json

        st = self._store_attempts_1()
        sid = f"nr-int-del-{self._suffix}"
        zid = f"zid-nr-del-{self._suffix}"
        raw = {
            "cf_behavioral": {
                "customer_replied": True,
                "interactive_mode": True,
                "recovery_conversation_state": "engaged",
                "last_customer_reply_preview": "متى التوصيل؟",
                "last_customer_reply_at": "2026-01-15T12:00:00+00:00",
                "recovery_reply_intent": "delivery",
                "latest_customer_message": "متى التوصيل؟",
            }
        }
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="+966501111112",
            status="abandoned",
            vip_mode=False,
            cart_value=40.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone="966501111112",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()

        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload.get("normal_recovery_reply_intent_key"), "delivery")
        del_reply_ar = payload.get("normal_recovery_suggested_reply_ar") or ""
        self.assertIsInstance(del_reply_ar, str)
        self.assertGreater(len(del_reply_ar.strip()), 0)
        del_strat_ar = payload.get("normal_recovery_suggested_strategy_ar") or ""
        self.assertIsInstance(del_strat_ar, str)
        self.assertGreater(len(del_strat_ar.strip()), 0)
        self.assertTrue(payload.get("normal_recovery_suggestion_reason_ar"))
        self.assertEqual(payload.get("normal_recovery_suggested_action_key"), "clarify_shipping")
        self.assertIn("normal_recovery_suggestion_ux_badge_ar", payload)
        self.assertIsInstance(payload.get("normal_recovery_suggestion_ux_badge_ar"), str)
        self.assertTrue(payload.get("normal_recovery_offer_decision_type_ar"))
        self.assertIn("normal_recovery_checkout_push_mode", payload)
        self.assertIsInstance(payload.get("normal_recovery_checkout_push_mode"), bool)

    def test_mock_sent_counts_for_phase_and_coarse_status(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-a"
        zid = f"zid-nr-{self._suffix}-a"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=50.0,
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=None,
                phone="966512345678",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()

        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload["normal_recovery_phase_key"], "first_message_sent")
        self.assertEqual(payload["normal_recovery_phase_label_ar"], "تم إرسال الرسالة الأولى")
        self.assertEqual(payload["normal_recovery_status"], "sent")
        self.assertNotIn("normal_recovery_hide_automation_cta", payload)

    def test_sent_real_also_counts(self) -> None:
        self.assertIn("mock_sent", _NORMAL_RECOVERY_SENT_LOG_STATUSES)
        self.assertIn("sent_real", _NORMAL_RECOVERY_SENT_LOG_STATUSES)
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-b"
        zid = f"zid-nr-{self._suffix}-b"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=40.0,
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=None,
                phone="966512345678",
                message="m1",
                status="sent_real",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload["normal_recovery_phase_key"], "first_message_sent")
        self.assertEqual(payload["normal_recovery_status"], "sent")

    def test_second_successful_send_reminder_phase(self) -> None:
        st = Store(
            zid_store_id=f"nr-tst-{self._suffix}-two-send",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add(st)
        db.session.flush()
        sid = f"nr-dash-{self._suffix}-c"
        zid = f"zid-nr-{self._suffix}-c"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=30.0,
        )
        db.session.add(ac)
        db.session.flush()
        now = datetime.now(timezone.utc)
        for step in (1, 2):
            db.session.add(
                CartRecoveryLog(
                    store_slug="demo",
                    session_id=sid,
                    cart_id=None,
                    phone="966512345678",
                    message=f"m{step}",
                    status="mock_sent",
                    step=step,
                    created_at=now,
                    sent_at=now,
                )
            )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload["normal_recovery_phase_key"], "reminder_sent")
        self.assertEqual(
            payload["normal_recovery_phase_label_ar"],
            "تم إرسال الرسالة الثانية",
        )
        self.assertEqual(payload["normal_recovery_status"], "sent")

    def test_pending_second_when_max_attempts_gte_2(self) -> None:
        st = Store(
            zid_store_id=f"nr-tst-{self._suffix}-2",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add(st)
        db.session.flush()
        sid = f"nr-dash-{self._suffix}-d"
        zid = f"zid-nr-{self._suffix}-d"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=25.0,
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=None,
                phone="966512345678",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload["normal_recovery_phase_key"], "pending_second_attempt")
        self.assertEqual(
            payload["normal_recovery_phase_label_ar"],
            "بانتظار المحاولة الثانية",
        )
        self.assertEqual(payload["normal_recovery_status"], "pending")

    def test_latest_skipped_anti_spam_is_returned(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-e"
        zid = f"zid-nr-{self._suffix}-e"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=20.0,
        )
        db.session.add(ac)
        db.session.flush()
        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=None,
                phone=None,
                message="x",
                status="skipped_anti_spam",
                step=1,
                created_at=now,
                sent_at=None,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload["normal_recovery_phase_key"], "customer_returned")
        self.assertEqual(payload["normal_recovery_phase_label_ar"], "عاد للموقع — تم إيقاف التسلسل")
        self.assertEqual(payload["normal_recovery_status"], "returned")
        self.assertEqual(payload.get("normal_recovery_blocker_key"), "user_returned")
        self.assertEqual(payload.get("normal_recovery_followup_hint_ar"), "عاد العميل للموقع")

    def test_behavioral_return_overrides_stale_duplicate_latest_log(self) -> None:
        import json

        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-dupret"
        zid = f"zid-nr-{self._suffix}-dupret"
        raw = {"cf_behavioral": {"user_returned_to_site": True}}
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=20.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.flush()
        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="x",
                status="skipped_duplicate",
                step=1,
                created_at=now,
                sent_at=None,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload.get("normal_recovery_blocker_key"), "user_returned")
        hint = (payload.get("normal_recovery_operational_hint_ar") or "").strip()
        self.assertIn("تلقائي", hint)
        mc_head = payload.get("merchant_clarity_headline_ar") or ""
        self.assertIn("موقع", mc_head)
        self.assertEqual(
            payload.get("merchant_lifecycle_primary_key"), "customer_returned"
        )
        self.assertIn(
            "عاد",
            (payload.get("merchant_lifecycle_customer_behavior_ar") or ""),
        )

    def test_alert_card_merges_cf_behavioral_from_older_duplicate_row(self) -> None:
        """
        /dashboard/normal-carts يمرّ عبر تجميع صفوف AbandonedCart؛ الصف الأحدث قد لا يحمل cf_behavioral
        بينما صف أقدم يحمل user_returned_to_site — يجب أن تظهر بطاقة العودة وليس انتظار التوقيت.
        """
        st = self._store_attempts_1()
        slug = (st.zid_store_id or "demo").strip()
        sid = f"nr-dupbh-{self._suffix}"
        z_old = f"zid-old-{self._suffix}"
        z_new = f"zid-new-{self._suffix}"
        t_old = datetime.now(timezone.utc) - timedelta(minutes=5)
        t_new = datetime.now(timezone.utc)
        raw_old = {"cf_behavioral": {"user_returned_to_site": True}}
        ac_old = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=z_old,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=11.0,
            raw_payload=json.dumps(raw_old, ensure_ascii=False),
            last_seen_at=t_old,
            first_seen_at=t_old,
        )
        ac_new = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=z_new,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=11.0,
            raw_payload=None,
            last_seen_at=t_new,
            first_seen_at=t_new,
        )
        db.session.add(ac_old)
        db.session.add(ac_new)
        db.session.flush()
        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=z_old,
                phone="9665111222333",
                message="m",
                status="mock_sent",
                step=1,
                created_at=now - timedelta(seconds=10),
                sent_at=now - timedelta(seconds=10),
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=z_new,
                phone=None,
                message="q",
                status="queued",
                step=2,
                created_at=now,
                sent_at=None,
            )
        )
        db.session.commit()
        grp_sorted = sorted([ac_new, ac_old], key=lambda a: a.last_seen_at, reverse=True)
        self.assertIs(grp_sorted[0], ac_new)
        dash = _dashboard_recovery_store_row()
        card = _vip_dashboard_cart_alert_dict_from_group(
            grp_sorted, dash, recovery_card_tier="normal"
        )
        self.assertEqual(
            card.get("merchant_lifecycle_primary_key"),
            "customer_returned",
            card.get("merchant_lifecycle_internal"),
        )
        self.assertIn("عاد", card.get("merchant_lifecycle_customer_behavior_ar") or "")
        diag = card.get("normal_recovery_diagnostics")
        self.assertIsInstance(diag, dict)
        self.assertEqual(diag.get("grouped_abandoned_cart_row_ids_count"), 2)

    def test_normal_cart_list_includes_session_when_store_id_mismatch_but_log_slug_matches(
        self,
    ) -> None:
        """جلسة بسجلات للمتجر الحالي يجب أن تظهر حتى لو ‎AbandonedCart.store_id‎ يشير لصف ‎Store‎ أقدم."""
        slug_new = f"nr-scope-new-{self._suffix}"
        slug_old = f"nr-scope-old-{self._suffix}"
        st_old = Store(
            zid_store_id=slug_old,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        st_new = Store(
            zid_store_id=slug_new,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st_old)
        db.session.add(st_new)
        db.session.flush()
        self.assertGreater(int(st_new.id), int(st_old.id))
        sid = f"sid-scope-{self._suffix}"
        zid = f"zid-scope-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st_old.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=12.0,
        )
        db.session.add(ac)
        db.session.flush()
        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug=slug_new,
                session_id=sid,
                cart_id=zid,
                phone="9665111222333",
                message="m",
                status="mock_sent",
                step=1,
                created_at=now,
                sent_at=now,
            )
        )
        db.session.commit()
        dash = _dashboard_recovery_store_row()
        self.assertEqual((dash.zid_store_id or "").strip(), slug_new)
        alerts = _normal_recovery_cart_alert_list(nr_session=sid, audience="ops")
        self.assertEqual(len(alerts), 1)
        d = alerts[0].get("normal_recovery_diagnostics") or {}
        self.assertEqual(d.get("session_id"), sid)
        self.assertEqual(d.get("cart_id"), zid)

    def test_normal_recovery_payload_includes_diagnostics_dict(self) -> None:
        st = self._store_attempts_1()
        zid = f"zid-diag-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=f"sid-diag-{self._suffix}",
            status="abandoned",
            vip_mode=False,
            cart_value=9.0,
            customer_phone="9665111222333",
        )
        db.session.add(ac)
        db.session.commit()
        p = _normal_recovery_phase_steps_payload(ac)
        d = p.get("normal_recovery_diagnostics")
        self.assertIsInstance(d, dict)
        self.assertEqual(d.get("selected_abandoned_cart_id"), int(ac.id))
        self.assertEqual(d.get("grouped_abandoned_cart_row_ids_count"), 1)
        self.assertIn("session_id", d)
        self.assertIn("merchant_lifecycle_primary_key", d)

    def test_skip_missing_reason_after_first_send_not_ignored(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-skip2"
        zid = f"zid-nr-{self._suffix}-skip2"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=18.0,
        )
        db.session.add(ac)
        db.session.flush()
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=2)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone="9665111222333",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=t0,
                sent_at=t0,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="x",
                status="skipped_missing_reason_tag",
                step=2,
                created_at=t1,
                sent_at=None,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload["normal_recovery_phase_key"], "first_message_sent")
        self.assertEqual(payload.get("normal_recovery_followup_hint_ar"), "سبب التردد غير معروف")
        self.assertEqual(payload.get("normal_recovery_last_skip_reason"), "missing_reason")
        self.assertEqual(payload.get("normal_recovery_blocker_key"), "missing_reason")
        blk = payload.get("normal_recovery_blocker")
        self.assertIsInstance(blk, dict)
        self.assertEqual(blk.get("label_ar"), "سبب التردد غير معروف")

    def test_blocker_missing_customer_phone_step1(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-nophone"
        zid = f"zid-nr-{self._suffix}-nophone"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=22.0,
        )
        db.session.add(ac)
        db.session.flush()
        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="x",
                status="skipped_no_verified_phone",
                step=1,
                created_at=now,
                sent_at=None,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload.get("normal_recovery_blocker_key"), "missing_customer_phone")
        self.assertEqual(
            payload.get("normal_recovery_phase_key"),
            "blocked_missing_customer_phone",
        )
        self.assertEqual(payload.get("normal_recovery_status"), "blocked")
        self.assertEqual(payload.get("normal_recovery_followup_hint_ar"), "لا يوجد رقم عميل")
        self.assertEqual(
            payload.get("normal_recovery_phase_label_ar"),
            "بانتظار رقم العميل",
        )
        self.assertNotEqual(
            payload.get("normal_recovery_phase_label_ar"),
            "بانتظار الإرسال",
        )
        self.assertNotEqual(payload.get("normal_recovery_status"), "sent")
        self.assertIsNone(payload.get("normal_recovery_sequence_label_ar"))

    def test_blocker_whatsapp_failed(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-wafail"
        zid = f"zid-nr-{self._suffix}-wafail"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=33.0,
        )
        db.session.add(ac)
        db.session.flush()
        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone="966599900011",
                message="m",
                status="whatsapp_failed",
                step=1,
                created_at=now,
                sent_at=None,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload.get("normal_recovery_blocker_key"), "whatsapp_failed")
        self.assertEqual(payload.get("normal_recovery_followup_hint_ar"), "فشل إرسال واتساب")
        blk = payload.get("normal_recovery_blocker")
        self.assertIsInstance(blk, dict)
        self.assertEqual(blk.get("severity"), "error")

    def test_blocker_customer_replied_followup(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-crep"
        zid = f"zid-nr-{self._suffix}-crep"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=28.0,
        )
        db.session.add(ac)
        db.session.flush()
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=2)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone="966599900022",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=t0,
                sent_at=t0,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="x",
                status="skipped_followup_customer_replied",
                step=2,
                created_at=t1,
                sent_at=None,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload.get("normal_recovery_blocker_key"), "customer_replied")
        self.assertEqual(payload.get("normal_recovery_followup_hint_ar"), "العميل رد")

    def test_no_blocker_when_latest_log_is_success(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-ok"
        zid = f"zid-nr-{self._suffix}-ok"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=40.0,
        )
        db.session.add(ac)
        db.session.flush()
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=2)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="x",
                status="skipped_no_verified_phone",
                step=1,
                created_at=t0,
                sent_at=None,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone="966599900033",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=t1,
                sent_at=t1,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertIsNone(payload.get("normal_recovery_blocker"))
        self.assertIsNone(payload.get("normal_recovery_blocker_key"))

    def test_latest_skipped_missing_reason_is_ignored(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-f"
        zid = f"zid-nr-{self._suffix}-f"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=15.0,
        )
        db.session.add(ac)
        db.session.flush()
        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=None,
                phone=None,
                message="x",
                status="skipped_missing_reason_tag",
                step=1,
                created_at=now,
                sent_at=None,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload["normal_recovery_phase_key"], "ignored")
        self.assertEqual(payload["normal_recovery_status"], "ignored")

    def test_blocker_missing_phone_when_latest_log_is_queued(self) -> None:
        """Queued row must not hide an earlier skipped_no_verified_phone for the dashboard."""
        st = self._store_attempts_1()
        sid = f"nr-dash-{self._suffix}-qphone"
        zid = f"zid-nr-{self._suffix}-qphone"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=22.0,
        )
        db.session.add(ac)
        db.session.flush()
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=3)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="skip",
                status="skipped_no_verified_phone",
                step=1,
                created_at=t0,
                sent_at=None,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="queued",
                status="queued",
                step=1,
                created_at=t1,
                sent_at=None,
            )
        )
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(payload.get("normal_recovery_blocker_key"), "missing_customer_phone")
        self.assertEqual(
            payload.get("normal_recovery_phase_key"),
            "blocked_missing_customer_phone",
        )
        self.assertEqual(payload.get("normal_recovery_status"), "blocked")
        self.assertEqual(payload.get("normal_recovery_phase_label_ar"), "بانتظار رقم العميل")
        hints = (payload.get("normal_recovery_followup_hint_ar") or "") + (
            payload.get("normal_recovery_operational_hint_ar") or ""
        )
        self.assertTrue(
            "بانتظار رقم العميل" in hints or "لا يوجد رقم عميل" in hints,
            hints,
        )

    def test_normal_carts_dashboard_html_shows_missing_phone_copy(self) -> None:
        """Regression: missing-phone operational copy must appear in rendered HTML."""
        st = self._store_attempts_1()
        sid = f"nr-html-{self._suffix}"
        zid = f"zid-html-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=18.0,
        )
        db.session.add(ac)
        db.session.commit()
        client = TestClient(app)
        from urllib.parse import quote

        r = client.get(
            "/dashboard/normal-carts/operations?nr_lifecycle=archived&nr_session="
            + quote(sid, safe="")
        )
        self.assertEqual(r.status_code, 200, (r.text or "")[:2000])
        html = r.text or ""
        self.assertTrue(
            ("بانتظار رقم العميل" in html) or ("لا يوجد رقم عميل" in html),
            html[:4000],
        )
        self.assertIn(
            'data-normal-recovery-phase-key="blocked_missing_customer_phone"',
            html,
        )
        self.assertIn('data-normal-recovery-status="blocked"', html)
        self.assertIn("data-merchant-lifecycle-primary", html, html[:6000])
        self.assertIn("data-normal-recovery-diagnostics", html, html[:8000])

    def test_http_abandon_without_phone_resolves_blocked_dominant_phase(self) -> None:
        """API reason + abandon without phone → payload phase is blocked (not pending_send)."""
        from unittest.mock import patch

        from main import _dashboard_recovery_store_row

        st = self._store_attempts_1()
        slug = (st.zid_store_id or "demo").strip()
        db.session.commit()  # Release SQLite write lock before TestClient request threads write.
        remove_scoped_session()  # Avoid test-thread session pinning the DB across ASGI threads.
        sid = f"nr-http-{self._suffix}"
        zid = f"zid-http-{self._suffix}"
        client = TestClient(app)
        with (
            patch("main.send_whatsapp", return_value={"ok": True}),
            patch("main.recovery_uses_real_whatsapp", return_value=False),
            patch("main.get_recovery_delay", return_value=0),
            patch("main._persist_cart_recovery_log"),
        ):
            rr = client.post(
                "/api/cart-recovery/reason",
                json={
                    "store_slug": slug,
                    "session_id": sid,
                    "reason_tag": "price",
                },
            )
            self.assertEqual(rr.status_code, 200, rr.text)
            ra = client.post(
                "/api/cart-event",
                json={
                    "event": "cart_abandoned",
                    "store": slug,
                    "session_id": sid,
                    "cart_id": zid,
                    "cart": [{"name": "item", "price": 40}],
                },
            )
            self.assertEqual(ra.status_code, 200, ra.text)
        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
        self.assertIsNotNone(ac)
        payload = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(
            payload.get("normal_recovery_phase_key"),
            "blocked_missing_customer_phone",
        )
        self.assertEqual(payload.get("normal_recovery_status"), "blocked")
        self.assertEqual(payload.get("normal_recovery_blocker_key"), "missing_customer_phone")
        ds = _dashboard_recovery_store_row()
        if ds is not None and int(ac.store_id or 0) == int(ds.id):
            from urllib.parse import quote

            rd = client.get(
                "/dashboard/normal-carts/operations?nr_lifecycle=archived&nr_session="
                + quote(sid, safe="")
            )
            self.assertEqual(rd.status_code, 200)
            html = rd.text or ""
            self.assertIn(
                'data-normal-recovery-phase-key="blocked_missing_customer_phone"',
                html,
            )
            self.assertIn('data-normal-recovery-status="blocked"', html)

    def test_normal_recovery_lifecycle_replied_archived_not_active(self) -> None:
        st = self._store_attempts_1()
        slug = (st.zid_store_id or "demo").strip()
        sid = f"nr-lc-arch-{self._suffix}"
        zid = f"zid-lc-arch-{self._suffix}"
        raw = {"cf_behavioral": {"customer_replied": True}}
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501111114",
            status="abandoned",
            vip_mode=False,
            cart_value=33.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                phone="966501111114",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        active = _normal_recovery_cart_alert_list(
            nr_session=sid, lifecycle="active", limit_groups=20, audience="ops"
        )
        self.assertEqual(len(active), 0)
        archived = _normal_recovery_cart_alert_list(
            nr_session=sid, lifecycle="archived", limit_groups=20, audience="ops"
        )
        self.assertEqual(len(archived), 1)
        self.assertEqual(
            (archived[0].get("normal_recovery_status") or "").strip(), "replied"
        )

    def test_normal_recovery_lifecycle_pending_in_active(self) -> None:
        st = self._store_attempts_1()
        sid = f"nr-lc-pen-{self._suffix}"
        zid = f"zid-lc-pen-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501111115",
            status="abandoned",
            vip_mode=False,
            cart_value=44.0,
        )
        db.session.add(ac)
        db.session.commit()
        active = _normal_recovery_cart_alert_list(
            nr_session=sid, lifecycle="active", limit_groups=20, audience="ops"
        )
        self.assertEqual(len(active), 1)
        self.assertEqual(
            (active[0].get("normal_recovery_status") or "").strip(), "pending"
        )

    def test_normal_carts_query_filter_redirects_to_operations(self) -> None:
        remove_scoped_session()
        client = TestClient(app)
        r = client.get(
            "/dashboard/normal-carts?nr_session=x_sess&nr_lifecycle=active",
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("/dashboard/normal-carts/operations", loc)
        self.assertIn("nr_session=x_sess", loc)

    def test_merchant_normal_carts_has_no_session_filter_field(self) -> None:
        remove_scoped_session()
        client = TestClient(app)
        r = client.get("/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('name="nr_session"', r.text or "")

    def test_operations_normal_carts_has_session_filter_field(self) -> None:
        remove_scoped_session()
        client = TestClient(app)
        r = client.get("/dashboard/normal-carts/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn('name="nr_session"', r.text or "")

    def test_stale_sent_cart_archived_for_merchant_not_active(self) -> None:
        from unittest.mock import patch

        st = self._store_attempts_1()
        slug = (st.zid_store_id or "").strip()
        sid = f"nr-stale-{self._suffix}"
        zid = f"zid-stale-{self._suffix}"
        t_old = datetime.now(timezone.utc) - timedelta(hours=3)
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501111117",
            status="abandoned",
            vip_mode=False,
            cart_value=55.0,
            last_seen_at=t_old,
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                phone="966501111117",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=t_old,
                sent_at=t_old,
            )
        )
        db.session.commit()

        tiny = {
            "active_sent_window_minutes": 1,
            "active_pending_window_minutes": 1,
            "stale_archive_enabled": True,
        }
        with patch(
            "services.normal_recovery_merchant_stale.normal_recovery_merchant_stale_config",
            return_value=tiny,
        ):
            active = _normal_recovery_merchant_lightweight_alert_list(
                nr_session=sid, lifecycle="active", limit_groups=20
            )
            archived = _normal_recovery_merchant_lightweight_alert_list(
                nr_session=sid,
                lifecycle="archived",
                limit_groups=20,
            )
        self.assertEqual(len(active), 0)
        self.assertEqual(len(archived), 1)
        self.assertIn("لم يُكمل", archived[0].get("merchant_history_note_ar") or "")
        self.assertEqual(
            (archived[0].get("merchant_business_state_ar") or "").strip(), "تم التواصل"
        )

    def test_stale_not_when_queued_followup_after_activity(self) -> None:
        from unittest.mock import patch

        st = self._store_attempts_1()
        slug = (st.zid_store_id or "").strip()
        sid = f"nr-q-{self._suffix}"
        zid = f"zid-q-{self._suffix}"
        t_old = datetime.now(timezone.utc) - timedelta(hours=3)
        t_q = t_old + timedelta(minutes=15)
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501111118",
            status="abandoned",
            vip_mode=False,
            cart_value=56.0,
            last_seen_at=t_old,
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                phone="966501111118",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=t_old,
                sent_at=t_old,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="queued",
                status="queued",
                step=2,
                created_at=t_q,
                sent_at=None,
            )
        )
        db.session.commit()
        tiny = {
            "active_sent_window_minutes": 1,
            "active_pending_window_minutes": 1,
            "stale_archive_enabled": True,
        }
        with patch(
            "services.normal_recovery_merchant_stale.normal_recovery_merchant_stale_config",
            return_value=tiny,
        ):
            active = _normal_recovery_merchant_lightweight_alert_list(
                nr_session=sid, lifecycle="active", limit_groups=20
            )
        self.assertEqual(len(active), 1)

    def test_ops_audience_sets_recovery_ops_detail_view_on_stale_archived(self) -> None:
        from unittest.mock import patch

        st = self._store_attempts_1()
        slug = (st.zid_store_id or "").strip()
        sid = f"nr-ops-{self._suffix}"
        zid = f"zid-ops-{self._suffix}"
        t_old = datetime.now(timezone.utc) - timedelta(hours=3)
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501111119",
            status="abandoned",
            vip_mode=False,
            cart_value=57.0,
            last_seen_at=t_old,
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                phone="966501111119",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=t_old,
                sent_at=t_old,
            )
        )
        db.session.commit()
        tiny = {
            "active_sent_window_minutes": 1,
            "active_pending_window_minutes": 1,
            "stale_archive_enabled": True,
        }
        with patch(
            "services.normal_recovery_merchant_stale.normal_recovery_merchant_stale_config",
            return_value=tiny,
        ):
            archived = _normal_recovery_cart_alert_list(
                nr_session=sid,
                lifecycle="archived",
                limit_groups=20,
                audience="ops",
            )
        self.assertEqual(len(archived), 1)
        self.assertTrue(archived[0].get("recovery_ops_detail_view"))
        self.assertEqual(archived[0].get("recovery_ops_session_id"), sid)


if __name__ == "__main__":
    unittest.main()
