# -*- coding: utf-8 -*-
"""Normal Recovery dashboard reads successful sends from CartRecoveryLog (mock_sent / sent_real)."""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone

from extensions import db
from main import (
    _normal_recovery_phase_steps_payload,
    _NORMAL_RECOVERY_SENT_LOG_STATUSES,
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
        self.assertIn("نفهمك", payload.get("normal_recovery_suggested_reply_ar") or "")
        self.assertIn(
            "تأكيد",
            payload.get("normal_recovery_suggested_strategy_ar") or "",
        )
        self.assertTrue(payload.get("normal_recovery_suggestion_reason_ar"))
        self.assertEqual(payload.get("normal_recovery_optional_offer_type"), "value_framing")
        self.assertEqual(payload.get("normal_recovery_suggested_action_key"), "reassure_price")

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
        self.assertIn("التوصيل", payload.get("normal_recovery_suggested_reply_ar") or "")
        self.assertIn("طمأنة", payload.get("normal_recovery_suggested_strategy_ar") or "")
        self.assertTrue(payload.get("normal_recovery_suggestion_reason_ar"))
        self.assertEqual(payload.get("normal_recovery_suggested_action_key"), "clarify_shipping")

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
        self.assertEqual(payload.get("normal_recovery_followup_hint_ar"), "توقفت: لا يوجد سبب")
        self.assertEqual(payload.get("normal_recovery_last_skip_reason"), "missing_reason")

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


if __name__ == "__main__":
    unittest.main()
