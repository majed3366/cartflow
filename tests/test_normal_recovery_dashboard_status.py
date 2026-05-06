# -*- coding: utf-8 -*-
"""Normal Recovery dashboard reads successful sends from CartRecoveryLog (mock_sent / sent_real)."""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone

from extensions import db
from main import (
    _normal_recovery_phase_steps_payload,
    _NORMAL_RECOVERY_SENT_LOG_STATUSES,
)
from models import AbandonedCart, CartRecoveryLog


class NormalRecoveryDashboardStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_mock_sent_counts_for_phase_and_coarse_status(self) -> None:
        sid = f"nr-dash-{self._suffix}-a"
        zid = f"zid-nr-{self._suffix}-a"
        ac = AbandonedCart(
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
        self.assertTrue(payload["normal_recovery_hide_automation_cta"])

    def test_sent_real_also_counts(self) -> None:
        self.assertIn("mock_sent", _NORMAL_RECOVERY_SENT_LOG_STATUSES)
        self.assertIn("sent_real", _NORMAL_RECOVERY_SENT_LOG_STATUSES)
        sid = f"nr-dash-{self._suffix}-b"
        zid = f"zid-nr-{self._suffix}-b"
        ac = AbandonedCart(
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
        sid = f"nr-dash-{self._suffix}-c"
        zid = f"zid-nr-{self._suffix}-c"
        ac = AbandonedCart(
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
        self.assertEqual(payload["normal_recovery_phase_label_ar"], "تم إرسال الرسالة")
        self.assertEqual(payload["normal_recovery_status"], "sent")


if __name__ == "__main__":
    unittest.main()
