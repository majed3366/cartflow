# -*- coding: utf-8 -*-
"""VIP merchant WhatsApp auto-alert delivery truth."""
from __future__ import annotations

import uuid
from unittest.mock import patch

import unittest

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, Store
from services.vip_merchant_alert import VIP_MERCHANT_ALERT_REASON_TAG
from services.whatsapp_send import send_whatsapp


class VipMerchantAlertDeliveryTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        try:
            sfx = self._suffix
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_vip_cart_state_sync_add_triggers_sync_merchant_alert(self, mock_send) -> None:
        mock_send.return_value = {"ok": True, "sid": "SM_test_vip_alert"}
        slug = f"vip-alert-{self._suffix}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            vip_notify_enabled=True,
            store_whatsapp_number="+966501112233",
        )
        db.session.add(store)
        db.session.commit()

        sid = f"s_vip_alert_{self._suffix}"
        cid = f"cf_cart_{self._suffix}"
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 1299.0,
                "items_count": 1,
                "cart": [{"price": 1299.0, "quantity": 1}],
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue(r.json().get("is_vip"))
        mock_send.assert_called_once()

        lg = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.cart_id == cid,
                CartRecoveryLog.reason_tag == VIP_MERCHANT_ALERT_REASON_TAG,
            )
            .first()
        )
        self.assertIsNotNone(lg)
        self.assertIn("966501112233", (lg.phone or "").replace("+", ""))

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_notify_disabled_skips_send_and_persists_skip_log(self, mock_send) -> None:
        slug = f"vip-off-{self._suffix}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            vip_notify_enabled=False,
            store_whatsapp_number="+966501112233",
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_vip_off_{self._suffix}"
        cid = f"cf_cart_off_{self._suffix}"
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 900.0,
                "items_count": 1,
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        mock_send.assert_not_called()
        lg = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.cart_id == cid)
            .first()
        )
        self.assertIsNotNone(lg)
        self.assertEqual("vip_merchant_alert_skipped", lg.status)

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=True)
    @patch(
        "services.whatsapp_production_reality_v2.enforce_whatsapp_template_window_before_send",
        return_value={"ok": False, "error": "template_required_outside_24h"},
    )
    @patch("services.whatsapp_send.twilio_messages_create")
    @patch("services.whatsapp_send.build_twilio_client")
    def test_merchant_alert_bypasses_template_window_gate(
        self,
        mock_client: object,
        mock_create: object,
        _gate: object,
        _prod: object,
    ) -> None:
        import os

        os.environ["TWILIO_ACCOUNT_SID"] = "ACtest"
        os.environ["TWILIO_AUTH_TOKEN"] = "tok"
        os.environ["TWILIO_WHATSAPP_FROM"] = "whatsapp:+14155238886"
        mock_create.return_value = {"ok": True, "msg": type("M", (), {"sid": "SMx", "status": "queued"})()}
        out = send_whatsapp(
            "+966579706669",
            "تنبيه VIP test",
            reason_tag=VIP_MERCHANT_ALERT_REASON_TAG,
            wa_trace_store_slug="demo",
        )
        self.assertTrue(out.get("ok"), out)
        _gate.assert_not_called()

