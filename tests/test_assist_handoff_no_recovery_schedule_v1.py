# -*- coding: utf-8 -*-
"""Assist handoff must not arm a second recovery lifecycle."""
from __future__ import annotations

import uuid
from unittest.mock import patch

import unittest

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryReason, RecoverySchedule, RecoveryTruthTimelineEvent
from schema_widget import ensure_store_widget_schema


class AssistHandoffNoRecoveryScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        ensure_store_widget_schema(db)
        self.client = TestClient(app)
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        try:
            db.session.query(RecoveryTruthTimelineEvent).filter(
                RecoveryTruthTimelineEvent.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(RecoverySchedule).filter(
                RecoverySchedule.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(CartRecoveryReason).filter(
                CartRecoveryReason.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    @patch("main.asyncio.create_task")
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_human_support_after_price_does_not_rearm_schedule(
        self,
        _delay: object,
        _ur: object,
        _send: object,
        _pcl: object,
        _ct: object,
    ) -> None:
        sid = f"s-handoff-{self._suffix}"
        cid = f"cf_cart_{self._suffix}"
        abandon = {
            "event": "cart_abandoned",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart_total": 120.0,
            "customer_phone": "966512345678",
        }
        arm_calls: list[dict] = []
        import main as main_mod

        real_arm = main_mod._arm_recovery_schedule_from_saved_reason_payload

        def arm_spy(synth_pl: dict) -> None:
            arm_calls.append(dict(synth_pl))
            return real_arm(synth_pl)

        with patch.object(
            main_mod,
            "_arm_recovery_schedule_from_saved_reason_payload",
            new=arm_spy,
        ):
            j_ab = self.client.post("/api/cart-event", json=abandon).json()
            self.assertEqual("waiting_for_reason", j_ab.get("recovery_state"))

            r_price = self.client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": "demo",
                    "session_id": sid,
                    "reason": "price",
                    "sub_category": "price_discount_request",
                    "customer_phone": "966512345678",
                },
            )
            self.assertEqual(200, r_price.status_code, r_price.text)

            n_sched_after_price = (
                db.session.query(RecoverySchedule)
                .filter(RecoverySchedule.session_id == sid)
                .count()
            )
            crr = (
                db.session.query(CartRecoveryReason)
                .filter(
                    CartRecoveryReason.store_slug == "demo",
                    CartRecoveryReason.session_id == sid,
                )
                .first()
            )
            self.assertIsNotNone(crr)
            self.assertEqual("price", (crr.reason or "").strip().lower())
            self.assertEqual(1, len(arm_calls))

            r_handoff = self.client.post(
                "/api/cartflow/assist-handoff",
                json={"store_slug": "demo", "session_id": sid},
            )
            self.assertEqual(200, r_handoff.status_code, r_handoff.text)
            self.assertTrue((r_handoff.json() or {}).get("ok"))

            r_legacy = self.client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": "demo",
                    "session_id": sid,
                    "reason": "human_support",
                },
            )
            self.assertEqual(200, r_legacy.status_code, r_legacy.text)

        self.assertEqual(1, len(arm_calls))
        n_sched_final = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.session_id == sid)
            .count()
        )
        self.assertEqual(n_sched_after_price, n_sched_final)
        db.session.refresh(crr)
        self.assertEqual("price", (crr.reason or "").strip().lower())

        n_ab = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid)
            .count()
        )
        self.assertLessEqual(n_ab, 2)


if __name__ == "__main__":
    unittest.main()
