# -*- coding: utf-8 -*-
"""POST /api/dashboard/vip-cart/{id}/merchant-alert — VIP تنبيه تاجر فقط."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from extensions import db
from fastapi.testclient import TestClient

from main import app
from models import AbandonedCart, CartRecoveryLog, Store


class VipDashboardMerchantAlertTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_manual_send_ok_returns_arabic_success(self, mock_send) -> None:
        mock_send.return_value = {"ok": True, "sid": "wx_1"}
        db.create_all()

        store = Store(
            zid_store_id=f"vip_manual_send_store_{uuid.uuid4().hex[:12]}",
            store_whatsapp_number="+966501112233",
            whatsapp_support_url=None,
        )
        db.session.add(store)
        db.session.commit()

        uid = uuid.uuid4().hex[:10]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"vip-dash-cart-1-{uid}",
            cart_value=999.0,
            status="detected",
            vip_mode=True,
        )
        db.session.add(ac)
        db.session.commit()
        rid = int(ac.id)

        r = self.client.post(f"/api/dashboard/vip-cart/{rid}/merchant-alert", json={})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"), body)
        self.assertEqual(body.get("message"), "تم إرسال تنبيه التاجر")
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        self.assertIn("تنبيه VIP", kwargs.get("message", ""))

    def test_non_vip_cart_rejected(self) -> None:
        db.create_all()
        store = Store(
            zid_store_id=f"vip_ns_1_{uuid.uuid4().hex[:12]}",
            store_whatsapp_number="+966501112233",
        )
        db.session.add(store)
        db.session.commit()
        uid = uuid.uuid4().hex[:10]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"vip-dash-cart-2-{uid}",
            cart_value=100.0,
            status="detected",
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.commit()
        r = self.client.post(f"/api/dashboard/vip-cart/{ac.id}/merchant-alert", json={})
        self.assertEqual(r.status_code, 400)
        self.assertIn("VIP", r.json().get("error", ""))

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_no_merchant_phone_arabic_error(self, mock_send) -> None:
        mock_send.return_value = {"ok": False, "error": "no_merchant_phone", "source": "no_merchant_contact"}
        db.create_all()
        store = Store(
            zid_store_id=f"vip_ns_2_{uuid.uuid4().hex[:12]}",
            store_whatsapp_number=None,
            whatsapp_support_url=None,
        )
        db.session.add(store)
        db.session.commit()
        uid = uuid.uuid4().hex[:10]
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"vip-dash-cart-3-{uid}",
            cart_value=300.0,
            status="detected",
            vip_mode=True,
        )
        db.session.add(ac)
        db.session.commit()
        r = self.client.post(f"/api/dashboard/vip-cart/{ac.id}/merchant-alert", json={})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json().get("error"), "لا يوجد رقم واتساب للمتجر")

    @patch("main._vip_priority_cart_alert_list", return_value=[])
    def test_vip_cart_settings_empty_priority_not_demo_but_demo_section_present(self, _prio_mock) -> None:
        db.create_all()
        r = self.client.get("/dashboard/vip-cart-settings")
        self.assertEqual(r.status_code, 200, r.text)
        html = r.text
        empty_msg = "لا توجد سلال مميزة حقيقية حالياً"
        self.assertIn(empty_msg, html)
        self.assertIn("demo_vip_cart_zid", html)
        self.assertGreater(html.find("demo_vip_cart_zid"), html.find(empty_msg))

    def test_vip_cart_settings_priority_from_vip_mode_and_recovery_log_union(self) -> None:
        db.create_all()
        slug = f"vip_pri_{uuid.uuid4().hex[:12]}"
        store = Store(zid_store_id=slug)
        db.session.add(store)
        db.session.commit()

        uid1 = uuid.uuid4().hex[:8]
        uid2 = uuid.uuid4().hex[:8]
        zid_mode = f"prio-mode-{uid1}"
        zid_log = f"prio-logonly-{uid2}"
        ac1 = AbandonedCart(
            store_id=store.id,
            zid_cart_id=zid_mode,
            cart_value=500.0,
            status="detected",
            vip_mode=True,
        )
        ac2 = AbandonedCart(
            store_id=store.id,
            zid_cart_id=zid_log,
            cart_value=600.0,
            status="detected",
            vip_mode=False,
        )
        db.session.add_all([ac1, ac2])
        db.session.commit()

        lg = CartRecoveryLog(
            store_slug=slug,
            session_id=f"sess-{uid2}",
            cart_id=zid_log,
            message="VIP log",
            status="vip_manual_handling",
        )
        db.session.add(lg)
        db.session.commit()

        r = self.client.get("/dashboard/vip-cart-settings")
        self.assertEqual(r.status_code, 200, r.text)
        html = r.text
        self.assertIn(zid_mode, html.replace("&#39;", "'"))
        self.assertIn(zid_log, html.replace("&#39;", "'"))
        demo_section = html.find('id="vip-demo-heading"')
        self.assertGreater(demo_section, 0)
        self.assertLess(html.find(zid_mode), demo_section)
        self.assertLess(html.find(zid_log), demo_section)


if __name__ == "__main__":
    unittest.main()
