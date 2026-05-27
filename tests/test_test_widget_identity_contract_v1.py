# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import RecoveryTruthTimelineEvent
from services.recovery_truth_timeline_v1 import STATUS_PROVIDER_SENT, record_recovery_truth_event


class TestWidgetIdentityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        try:
            db.session.query(RecoveryTruthTimelineEvent).filter(
                RecoveryTruthTimelineEvent.recovery_key.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_cart_event_resets_identity_when_old_lifecycle_progressed(self) -> None:
        store = "cartflow3-91bd2e"
        sid_old = f"s_old_{self._suffix}"
        cid_old = f"cf_old_{self._suffix}"
        rk_old = f"{store}:{sid_old}"
        record_recovery_truth_event(
            recovery_key=rk_old,
            status=STATUS_PROVIDER_SENT,
            source="test_identity_contract",
            store_slug=store,
            session_id=sid_old,
            cart_id=cid_old,
        )

        captured: dict[str, str] = {}

        async def fake_handle(_bg: object, payload: dict) -> dict:
            captured["session_id"] = str(payload.get("session_id") or "")
            captured["cart_id"] = str(payload.get("cart_id") or "")
            captured["store"] = str(payload.get("store") or payload.get("store_slug") or "")
            return {"recovery_scheduled": False, "recovery_state": "waiting_for_reason"}

        with patch(
            "services.merchant_test_widget_store_v1.merchant_authenticated_store_slug",
            return_value=store,
        ), patch("main.handle_cart_abandoned", side_effect=fake_handle):
            r = self.client.post(
                "/api/cart-event",
                json={
                    "event": "cart_abandoned",
                    "store": "demo",
                    "store_slug": "demo",
                    "session_id": sid_old,
                    "cart_id": cid_old,
                    "merchant_activation": True,
                    "test_widget_identity": "merchant_activation",
                },
            )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json() or {}
        self.assertTrue(j.get("test_identity_reset"))
        self.assertEqual(j.get("old_recovery_key"), rk_old)
        self.assertNotEqual(j.get("new_session_id"), sid_old)
        self.assertNotEqual(j.get("new_cart_id"), cid_old)
        self.assertEqual(captured.get("store"), store)
        self.assertEqual(captured.get("session_id"), j.get("new_session_id"))
        self.assertEqual(captured.get("cart_id"), j.get("new_cart_id"))

    def test_dev_identity_trace_marks_non_reusable_after_provider_sent(self) -> None:
        store = "cartflow3-91bd2e"
        sid = f"s_trace_{self._suffix}"
        cid = f"cf_trace_{self._suffix}"
        rk = f"{store}:{sid}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test_identity_trace",
            store_slug=store,
            session_id=sid,
            cart_id=cid,
        )
        r = self.client.get(
            "/dev/test-widget-identity-trace",
            params={"store_slug": store, "session_id": sid, "cart_id": cid},
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json() or {}
        self.assertTrue(j.get("ok"))
        self.assertFalse(j.get("identity_reusable"))
        flags = j.get("lifecycle_truth_flags") or {}
        self.assertTrue(flags.get("provider_sent"))
        self.assertEqual(j.get("recovery_key"), rk)


if __name__ == "__main__":
    unittest.main()
