# -*- coding: utf-8 -*-
"""VIP manual handling: cart_abandoned skips scheduled customer WhatsApp recovery."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from extensions import db
from main import app
from models import AbandonedCart
from tests.test_recovery_isolation import _post_recovery_reason_for_session, _reset_recovery_memory


class VipManualHandlingTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    @patch("main._load_store_row_for_recovery")
    @patch("main.try_send_vip_merchant_whatsapp_alert", return_value={"ok": False})
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    def test_vip_cart_abandon_skips_customer_whatsapp(
        self, mock_send: object, _p: object, _m: object, mock_store: object
    ) -> None:
        mock_store.return_value = SimpleNamespace(
            zid_store_id="demo",
            vip_cart_threshold=400,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            recovery_delay_minutes=None,
            store_whatsapp_number=None,
            whatsapp_support_url=None,
        )
        db.create_all()
        main._ensure_store_widget_schema()

        cid = "vip-manual-cart-1"
        existing = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        sid = "vip-manual-session-1"
        _post_recovery_reason_for_session(self.client, "demo", sid, "price")

        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_abandoned",
                "store": "demo",
                "session_id": sid,
                "cart_id": cid,
                "cart_value": 500.0,
                "phone": "+966501112233",
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body.get("recovery_state"), "vip_manual_handling")
        self.assertTrue(body.get("recovery_vip_manual"))
        self.assertTrue(body.get("customer_recovery_skipped"))
        self.assertFalse(body.get("recovery_scheduled", True))
        mock_send.assert_not_called()

        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac)
        self.assertTrue(bool(getattr(ac, "vip_mode", False)))
        self.assertEqual((ac.status or "").strip(), "abandoned")


class VipMerchantResolveTests(unittest.TestCase):
    def test_resolve_store_number(self) -> None:
        from services.vip_merchant_alert import resolve_merchant_whatsapp_phone

        st = SimpleNamespace(
            store_whatsapp_number="+966501112233",
            whatsapp_support_url=None,
        )
        phone, src = resolve_merchant_whatsapp_phone(st)
        self.assertIsNotNone(phone)
        self.assertEqual(src, "store_whatsapp_number")

    def test_resolve_wa_me(self) -> None:
        from services.vip_merchant_alert import resolve_merchant_whatsapp_phone

        st = SimpleNamespace(
            store_whatsapp_number=None,
            whatsapp_support_url="https://wa.me/966501112233",
        )
        phone, src = resolve_merchant_whatsapp_phone(st)
        self.assertEqual(phone, "966501112233")
        self.assertEqual(src, "whatsapp_support_url_wa_me")

    def test_vip_merchant_alert_body_plain(self) -> None:
        from services.vip_merchant_alert import build_vip_merchant_alert_body

        link = "https://example.test/dashboard/vip-cart-settings"
        expected = (
            "تنبيه VIP 🚨\n\n"
            "سلة عالية القيمة: 1200 ريال\n\n"
            "السبب: —\n\n"
            "رابط المراجعة:\n"
            + link
        )
        self.assertEqual(
            build_vip_merchant_alert_body(1200.0, dashboard_link=link),
            expected,
        )

    def test_vip_merchant_alert_body_with_reason_tag(self) -> None:
        from services.vip_merchant_alert import build_vip_merchant_alert_body

        link = "https://example.test/dashboard/vip-cart-settings"
        expected = (
            "تنبيه VIP 🚨\n\n"
            "سلة عالية القيمة: 500 ريال\n\n"
            "السبب: السعر\n\n"
            "رابط المراجعة:\n"
            + link
        )
        self.assertEqual(
            build_vip_merchant_alert_body(500.0, reason_tag="price", dashboard_link=link),
            expected,
        )

    def test_vip_merchant_alert_not_old_colon_intro(self) -> None:
        from services.vip_merchant_alert import build_vip_merchant_alert_body

        body = build_vip_merchant_alert_body(999.0, dashboard_link="https://x.test/dash")
        self.assertNotIn("تنبيه VIP:", body)


if __name__ == "__main__":
    unittest.main()
