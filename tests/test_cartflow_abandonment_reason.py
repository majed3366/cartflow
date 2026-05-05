# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
import unittest

from main import app
from extensions import db
from models import CartRecoveryLog, CartRecoveryReason, Store, AbandonedCart
from schema_widget import ensure_store_widget_schema


class TestCartflowAbandonmentReason(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.client = TestClient(app)

    def test_post_reason_price(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-test-1",
                "reason": "price",
                "sub_category": "price_discount_request",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))

    def test_post_reason_price_requires_sub(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={"store_slug": "demo", "session_id": "s-no-sub", "reason": "price"},
        )
        self.assertEqual(400, r.status_code, r.text)
        self.assertFalse((r.json() or {}).get("ok"))

    def test_post_reason_sub_rejected_for_non_price(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-extra",
                "reason": "warranty",
                "sub_category": "price_discount_request",
            },
        )
        self.assertEqual(400, r.status_code, r.text)
        self.assertFalse((r.json() or {}).get("ok"))

    def test_post_reason_other_requires_text(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-test-2",
                "reason": "other",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertFalse((r.json() or {}).get("ok"))

    def test_post_reason_other_accepts_phone_only(self) -> None:
        ensure_store_widget_schema(db)
        sid = "s-phone-only-" + uuid.uuid4().hex[:8]
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason": "other",
                "customer_phone": "966512345678",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        self.assertIsNotNone(crr)
        self.assertEqual("966512345678", (crr.customer_phone or "").strip())

    def test_post_reason_other_invalid_phone(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-inv-ph",
                "reason": "other",
                "customer_phone": "12345",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertFalse((r.json() or {}).get("ok"))

    def test_customer_phone_rejected_when_not_other(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-wa-phone",
                "reason": "warranty",
                "customer_phone": "966512345678",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertEqual(
            "customer_phone_not_applicable",
            (r.json() or {}).get("error"),
        )

    def test_post_reason_vip_phone_capture_persists(self) -> None:
        ensure_store_widget_schema(db)
        sid = "s-vip-cap-" + uuid.uuid4().hex[:8]
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason": "vip_phone_capture",
                "customer_phone": "0598765432",
                "custom_text": "vip_cart_phone_capture",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        self.assertIsNotNone(crr)
        self.assertEqual("966598765432", (crr.customer_phone or "").strip())
        self.assertEqual("vip_phone_capture", crr.reason)
        self.assertEqual("vip_cart_phone_capture", (crr.custom_text or "").strip())

    def test_post_reason_vip_phone_capture_updates_matching_abandoned_cart(self) -> None:
        """رقم ‎vip_phone_capture‎ يُنسخ إلى ‎AbandonedCart.customer_phone‎ لنفس المتجر والجلسة."""
        ensure_store_widget_schema(db)
        uid = uuid.uuid4().hex[:12]
        zid_store = f"zid_vip_link_{uid}"
        sid = f"s-vip-cart-{uid}"
        store = Store(zid_store_id=zid_store)
        db.session.add(store)
        db.session.commit()
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"cart_vip_{uid}",
            cart_value=900.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid,
        )
        db.session.add(ac)
        db.session.commit()
        ac_id = int(ac.id)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": zid_store,
                "session_id": sid,
                "reason": "vip_phone_capture",
                "customer_phone": "0598877665",
                "custom_text": "vip_cart_phone_capture",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        db.session.expire_all()
        row = db.session.get(AbandonedCart, ac_id)
        self.assertIsNotNone(row)
        self.assertEqual("966598877665", (row.customer_phone or "").strip())
        from main import (  # type: ignore  # نفس مسار لوحة VIP
            _dashboard_recovery_store_row,
            _vip_dashboard_customer_phone_raw,
        )

        db.session.expire_all()
        ac_row = db.session.get(AbandonedCart, ac_id)
        self.assertIsNotNone(ac_row)
        dash_store = _dashboard_recovery_store_row()
        resolved = _vip_dashboard_customer_phone_raw(ac_row, dash_store)
        self.assertEqual("966598877665", resolved.strip())

    def test_post_reason_vip_phone_capture_triggers_merchant_whatsapp(self) -> None:
        """بعد حفظ ‎vip_phone_capture‎: محاولة إرسال واتساب للتاجر عبر ‎send_whatsapp‎."""
        ensure_store_widget_schema(db)
        import os
        from unittest.mock import patch

        sid = "s-vip-merch-wa-" + uuid.uuid4().hex[:8]
        prev = os.environ.get("DEFAULT_MERCHANT_PHONE")
        os.environ["DEFAULT_MERCHANT_PHONE"] = "+966511122233"
        try:
            with patch(
                "services.whatsapp_send.send_whatsapp",
                return_value={"ok": True, "sid": "SM_vip_cap_test"},
            ) as mock_sw:
                r = self.client.post(
                    "/api/cartflow/reason",
                    json={
                        "store_slug": "demo",
                        "session_id": sid,
                        "reason": "vip_phone_capture",
                        "customer_phone": "0594433322",
                        "custom_text": "vip_cart_phone_capture",
                    },
                )
        finally:
            if prev is None:
                os.environ.pop("DEFAULT_MERCHANT_PHONE", None)
            else:
                os.environ["DEFAULT_MERCHANT_PHONE"] = prev
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))
        mock_sw.assert_called_once()
        _merchant_to, msg = mock_sw.call_args[0]
        self.assertIn("966594433322", msg)
        self.assertIn("https://wa.me/966594433322", msg)
        self.assertIn("🔥 سلة مميزة", msg)

    def test_post_reason_vip_phone_capture_requires_custom_marker(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-vip-bad-ct-" + uuid.uuid4().hex[:8],
                "reason": "vip_phone_capture",
                "customer_phone": "966512345678",
                "custom_text": "wrong",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertEqual(
            "custom_text_invalid_vip_capture",
            (r.json() or {}).get("error"),
        )

    def test_post_reason_vip_phone_capture_requires_phone(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": "s-vip-no-ph-" + uuid.uuid4().hex[:8],
                "reason": "vip_phone_capture",
                "custom_text": "vip_cart_phone_capture",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertEqual(
            "customer_phone_required",
            (r.json() or {}).get("error"),
        )

    def test_public_config_includes_vip_cart_threshold_key(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": "demo"}
        )
        self.assertEqual(200, r.status_code)
        j = r.json() or {}
        self.assertTrue(j.get("ok"))
        self.assertIn("vip_cart_threshold", j)
        self.assertFalse(j.get("vip_from_cart_total"))
        self.assertIsNone(j.get("cart_total"))

    def test_public_config_reports_is_vip_when_cart_total_provided(self) -> None:
        ensure_store_widget_schema(db)
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        if row is None:
            self.skipTest("needs default store row")
        row.vip_cart_threshold = 400
        db.session.commit()
        r = self.client.get(
            "/api/cartflow/public-config",
            params={"store_slug": "demo", "cart_total": 401},
        )
        self.assertEqual(200, r.status_code)
        j = r.json() or {}
        self.assertTrue(j.get("vip_from_cart_total"))
        self.assertTrue(j.get("is_vip"))
        self.assertAlmostEqual(float(j.get("cart_total") or 0), 401.0)

    def test_post_reason_other_emits_cf_phone_logs(self) -> None:
        import logging

        ensure_store_widget_schema(db)
        sid = "s-cf-log-" + uuid.uuid4().hex[:8]
        with self.assertLogs("cartflow", level=logging.INFO) as alc:
            r = self.client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": "demo",
                    "session_id": sid,
                    "reason": "other",
                    "customer_phone": "0598765432",
                },
            )
        self.assertEqual(200, r.status_code, r.text)
        blob = "\n".join(alc.output)
        self.assertIn("[CF PHONE RECEIVED]", blob)
        self.assertIn("session_id=%s" % sid, blob)
        self.assertIn("reason=other", blob)
        self.assertIn("customer_phone=966598765432", blob)
        self.assertIn("[CF PHONE SAVED]", blob)
        ensure_store_widget_schema(db)
        sid = "rs1-" + uuid.uuid4().hex
        r0 = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "rstore", "session_id": sid},
        )
        self.assertEqual(200, r0.status_code)
        self.assertFalse((r0.json() or {}).get("after_step1"))
        log = CartRecoveryLog(
            store_slug="rstore",
            session_id=sid,
            message="m",
            status="mock_sent",
            step=1,
        )
        db.session.add(log)
        db.session.commit()
        r1 = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "rstore", "session_id": sid},
        )
        self.assertEqual(200, r1.status_code)
        self.assertTrue((r1.json() or {}).get("after_step1"))

    def test_cart_recovery_reason_upsert(self) -> None:
        ensure_store_widget_schema(db)
        sid = "crr-upsert-1"
        r1 = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason": "price",
                "sub_category": "price_budget_issue",
            },
        )
        self.assertEqual(200, r1.status_code, r1.text)
        self.assertTrue((r1.json() or {}).get("ok"))
        r2 = self.client.post(
            "/api/cartflow/reason",
            json={"store_slug": "demo", "session_id": sid, "reason": "warranty"},
        )
        self.assertEqual(200, r2.status_code, r2.text)
        self.assertTrue((r2.json() or {}).get("ok"))
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        self.assertIsNotNone(crr)
        self.assertEqual("warranty", crr.reason)
        self.assertIsNone(crr.sub_category)

    def test_public_config_whatsapp(self) -> None:
        ensure_store_widget_schema(db)
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        if row is not None:
            row.whatsapp_support_url = "https://wa.me/966500000000"
            db.session.commit()
        r = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": "demo"}
        )
        self.assertEqual(200, r.status_code)
        j = r.json() or {}
        self.assertTrue(j.get("ok"))


if __name__ == "__main__":
    unittest.main()
