# -*- coding: utf-8 -*-
"""Scheduled recovery carts visible on merchant dashboard before first WhatsApp send."""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone

from extensions import db
from main import (
    _dashboard_recovery_store_row,
    _normal_recovery_merchant_lightweight_alert_list_for_api,
)
from models import (
    AbandonedCart,
    CartRecoveryLog,
    CartRecoveryReason,
    RecoverySchedule,
    Store,
)
from services.merchant_cart_row_classifier import WAITING_STATUS_LABEL_AR


class ScheduledRecoveryDashboardVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]

    def tearDown(self) -> None:
        try:
            db.session.query(RecoverySchedule).filter(
                RecoverySchedule.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(CartRecoveryReason).filter(
                CartRecoveryReason.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%-{self._suffix}")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_reason_and_schedule_visible_before_send_without_abandoned_row(self) -> None:
        slug = f"nr-pre-send-{self._suffix}"
        sid = f"s-pre-send-{self._suffix}"
        zid = f"z-pre-send-{self._suffix}"
        rk = f"{slug}:{sid}"
        now = datetime.now(timezone.utc)
        due = now + timedelta(minutes=5)

        st = Store(
            zid_store_id=slug,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()

        dash = _dashboard_recovery_store_row()
        if dash is not None:
            dash.zid_store_id = slug
            dash.recovery_attempts = 1

        db.session.add(
            CartRecoveryReason(
                store_slug=slug,
                session_id=sid,
                reason="price_high",
                customer_phone="966501234567",
                updated_at=now,
                created_at=now,
            )
        )
        db.session.add(
            RecoverySchedule(
                recovery_key=rk,
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                reason_tag="price_high",
                customer_phone="966501234567",
                scheduled_at=now,
                due_at=due,
                effective_delay_seconds=300.0,
                delay_source="test",
                status="scheduled",
                step=1,
            )
        )
        db.session.commit()

        self.assertEqual(
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid)
            .count(),
            0,
        )

        rows, _prof = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=50,
            page_offset=0,
            nr_session=sid,
            lifecycle="active",
            dash_store=st,
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(
            (row.get("merchant_coarse_status") or "").strip(), "pending"
        )
        self.assertEqual(
            (row.get("merchant_status_label_ar") or "").strip(),
            WAITING_STATUS_LABEL_AR,
        )
        self.assertEqual(
            (row.get("customer_lifecycle_state") or "").strip(),
            "waiting_first_send",
        )
        self.assertTrue(
            row.get("next_attempt_due_at")
            or row.get("customer_lifecycle_next_followup_line_ar")
        )

    def test_sent_cart_still_shows_customer_waiting_label(self) -> None:
        slug = f"nr-sent-{self._suffix}"
        sid = f"s-sent-{self._suffix}"
        zid = f"z-sent-{self._suffix}"
        now = datetime.now(timezone.utc)

        st = Store(
            zid_store_id=slug,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        db.session.add(
            AbandonedCart(
                store_id=int(st.id),
                zid_cart_id=zid,
                recovery_session_id=sid,
                customer_phone="966509999999",
                status="abandoned",
                cart_value=40.0,
                last_seen_at=now,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=zid,
                phone="966509999999",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=now,
                sent_at=now,
            )
        )
        db.session.commit()

        rows, _prof = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=50,
            page_offset=0,
            nr_session=sid,
            lifecycle="active",
            dash_store=st,
        )
        self.assertEqual(len(rows), 1)
        self.assertIn(
            "تفاعل",
            (rows[0].get("merchant_status_label_ar") or ""),
        )


if __name__ == "__main__":
    unittest.main()
