# -*- coding: utf-8 -*-
"""VIP operational truth closure — lane isolation + alert log statuses."""
from __future__ import annotations

import uuid
from unittest.mock import patch

import unittest

from extensions import db
from main import (
    _cart_recovery_sent_real_count_for_abandoned,
    app,
)
from models import AbandonedCart, CartRecoveryLog, Store
from services.vip_merchant_alert import (
    VIP_MERCHANT_ALERT_REASON_TAG,
    resolve_vip_alert_destination,
)
from services.vip_operational_truth_v1 import (
    is_vip_merchant_only_recovery_log,
    resolve_vip_merchant_alert_log_status,
)


class VipOperationalTruthClosureTests(unittest.TestCase):
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

    def test_sent_count_excludes_vip_merchant_alert_logs(self) -> None:
        slug = f"vip-iso-{self._suffix}"
        sid = f"s_iso_{self._suffix}"
        cid = f"cf_cart_{self._suffix}"
        ac = AbandonedCart(
            zid_cart_id=cid,
            recovery_session_id=sid,
            cart_value=200.0,
            status="abandoned",
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=cid,
                status="sent_real",
                reason_tag=VIP_MERCHANT_ALERT_REASON_TAG,
                message="VIP merchant alert",
            )
        )
        db.session.commit()
        self.assertEqual(0, _cart_recovery_sent_real_count_for_abandoned(ac))

    def test_resolve_vip_merchant_alert_log_status_never_sent_real(self) -> None:
        st = resolve_vip_merchant_alert_log_status({"ok": True, "sid": "SMabc"})
        self.assertEqual("vip_merchant_alert_accepted", st)
        self.assertNotEqual("sent_real", st)

    def test_is_vip_merchant_only_recovery_log(self) -> None:
        lg = CartRecoveryLog(status="sent_real", reason_tag="vip_merchant_alert")
        self.assertTrue(is_vip_merchant_only_recovery_log(lg))
        lg2 = CartRecoveryLog(status="sent_real", reason_tag="recovery_first")
        self.assertFalse(is_vip_merchant_only_recovery_log(lg2))

    def test_resolve_vip_alert_destination_priority(self) -> None:
        store = Store(
            zid_store_id=f"dest-{self._suffix}",
            store_whatsapp_number="+966501112233",
            whatsapp_support_url="https://wa.me/966509998877",
        )
        phone, src, digits = resolve_vip_alert_destination(store)
        self.assertEqual("store_whatsapp_number", src)
        self.assertIn("966501112233", digits)
        self.assertIsNotNone(phone)

        store2 = Store(
            zid_store_id=f"dest2-{self._suffix}",
            whatsapp_support_url="https://wa.me/966509998877",
        )
        phone2, src2, _ = resolve_vip_alert_destination(store2)
        self.assertEqual("whatsapp_support_url_wa_me", src2)
        self.assertIsNotNone(phone2)

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_vip_cart_not_leaked_into_normal_carts_lifecycle(self, mock_send) -> None:
        mock_send.return_value = {
            "ok": True,
            "sid": "SM_test_lane",
            "delivery_truth": {"delivered_to_device": False, "truth_level": "accepted_by_provider"},
        }
        slug = f"vip-leak-{self._suffix}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            vip_notify_enabled=True,
            store_whatsapp_number="+966501112233",
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_leak_{self._suffix}"
        cid = f"cf_cart_leak_{self._suffix}"
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
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        nc = self.client.get(f"/api/dashboard/normal-carts?store={slug}")
        self.assertEqual(200, nc.status_code, nc.text)
        rows = nc.json().get("carts") or nc.json().get("rows") or []
        leaked = [
            row
            for row in rows
            if isinstance(row, dict)
            and str(row.get("cart_id") or "").strip() == cid
        ]
        self.assertEqual([], leaked, "VIP cart must not appear in normal-carts")

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_auto_alert_persists_vip_status_not_sent_real(self, mock_send: object) -> None:
        from services.whatsapp_delivery_truth_v1 import TRUTH_DELIVERED

        mock_send.return_value = {
            "ok": True,
            "sid": "SM_delivered_test",
            "delivery_truth_level": TRUTH_DELIVERED,
            "delivered_to_device": True,
        }
        slug = f"vip-st-{self._suffix}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            vip_notify_enabled=True,
            store_whatsapp_number="+966501112233",
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_st_{self._suffix}"
        cid = f"cf_cart_st_{self._suffix}"
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
        lg = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.cart_id == cid,
                CartRecoveryLog.reason_tag == VIP_MERCHANT_ALERT_REASON_TAG,
            )
            .first()
        )
        self.assertIsNotNone(lg)
        self.assertNotEqual("sent_real", lg.status)
        self.assertIn(
            lg.status,
            {
                "vip_merchant_alert_accepted",
                "vip_merchant_alert_delivered",
                "vip_merchant_alert_mock",
            },
        )
