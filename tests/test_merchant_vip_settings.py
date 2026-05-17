# -*- coding: utf-8 -*-
"""Merchant VIP settings persistence via /api/recovery-settings."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

import main
from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.vip_cart import is_vip_cart, merchant_vip_threshold_int


class MerchantVipSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        self.zid = f"vip_set_{uuid.uuid4().hex[:12]}"
        for row in db.session.query(Store).filter_by(zid_store_id=self.zid).all():
            db.session.delete(row)
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(self.row)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.store_slug == self.zid
        ).delete(synchronize_session=False)
        db.session.query(AbandonedCart).filter(
            AbandonedCart.store_id == self.row.id
        ).delete(synchronize_session=False)
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    def test_get_includes_merchant_vip_fields(self) -> None:
        data = self.client.get("/api/recovery-settings").json()
        self.assertTrue(data.get("ok"))
        self.assertIn("vip_enabled", data)
        self.assertIn("vip_notify_enabled", data)
        self.assertIn("vip_note", data)
        self.assertIn("vip_status_display_ar", data)
        self.assertIn("vip_threshold_display_ar", data)

    def test_post_persists_300_then_1000_after_refresh(self) -> None:
        note = "شحن مجاني للسلال المهمة"
        r1 = self.client.post(
            "/api/recovery-settings",
            json={
                "vip_enabled": True,
                "vip_cart_threshold": 300,
                "vip_notify_enabled": True,
                "vip_note": note,
                "merchant_settings_scope": "vip",
            },
        )
        self.assertEqual(r1.status_code, 200, r1.text[:400])
        j1 = r1.json()
        self.assertTrue(j1.get("ok"))
        self.assertEqual(j1.get("vip_cart_threshold"), 300)
        self.assertEqual(j1.get("vip_note"), note)

        j_get = self.client.get("/api/recovery-settings").json()
        self.assertEqual(j_get.get("vip_cart_threshold"), 300)
        self.assertEqual(j_get.get("vip_note"), note)

        r2 = self.client.post(
            "/api/recovery-settings",
            json={
                "vip_enabled": True,
                "vip_cart_threshold": 1000,
                "vip_notify_enabled": True,
                "vip_note": note,
                "merchant_settings_scope": "vip",
            },
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json().get("vip_cart_threshold"), 1000)
        j_get2 = self.client.get("/api/recovery-settings").json()
        self.assertEqual(j_get2.get("vip_cart_threshold"), 1000)

    def test_vip_only_post_does_not_rewrite_widget_trigger_json(self) -> None:
        from services.cartflow_widget_trigger_settings import (
            widget_trigger_config_from_store_row,
        )

        before = widget_trigger_config_from_store_row(self.row)
        self.client.post(
            "/api/recovery-settings",
            json={"vip_cart_threshold": 250, "merchant_settings_scope": "vip"},
        )
        db.session.expire(self.row)
        refreshed = db.session.get(Store, self.row.id)
        assert refreshed is not None
        after = widget_trigger_config_from_store_row(refreshed)
        self.assertEqual(after, before)
        self.assertEqual(refreshed.vip_cart_threshold, 250)

    def test_post_persists_toggle_threshold_note(self) -> None:
        post = self.client.post(
            "/api/recovery-settings",
            json={
                "vip_enabled": False,
                "vip_cart_threshold": 1000,
                "vip_notify_enabled": False,
                "vip_note": "شحن مجاني",
            },
        )
        self.assertEqual(post.status_code, 200, post.text[:400])
        body = post.json()
        self.assertTrue(body.get("ok"))
        self.assertFalse(body.get("vip_enabled"))
        self.assertEqual(body.get("vip_cart_threshold"), 1000)
        self.assertFalse(body.get("vip_notify_enabled"))
        self.assertEqual(body.get("vip_note"), "شحن مجاني")

        get2 = self.client.get("/api/recovery-settings").json()
        self.assertFalse(get2.get("vip_enabled"))
        self.assertEqual(get2.get("vip_cart_threshold"), 1000)

        saved = db.session.get(Store, self.row.id)
        assert saved is not None
        self.assertFalse(bool(saved.vip_enabled))
        self.assertEqual(saved.vip_cart_threshold, 1000)
        self.assertEqual((saved.vip_note or "").strip(), "شحن مجاني")

    def test_runtime_is_vip_cart_unchanged_by_vip_enabled_flag(self) -> None:
        """vip_enabled is merchant preference only in v1 — lane still uses threshold."""
        self.row.vip_enabled = False
        self.row.vip_cart_threshold = 500
        db.session.commit()
        self.assertTrue(is_vip_cart(600, self.row))
        self.assertIsNone(merchant_vip_threshold_int(
            Store(zid_store_id="x", recovery_delay=1, recovery_delay_unit="minutes", recovery_attempts=1, vip_enabled=False, vip_cart_threshold=None)
        ))

    def test_last_vip_displays_from_log_and_cart(self) -> None:
        dash = main._dashboard_recovery_store_row()
        self.assertIsNotNone(dash)
        assert dash is not None
        dash.vip_cart_threshold = 500
        slug = (dash.zid_store_id or self.zid).strip()
        ac = AbandonedCart(
            store_id=dash.id,
            zid_cart_id=f"cart_{uuid.uuid4().hex[:8]}",
            cart_value=1200.0,
            status="abandoned",
        )
        db.session.add(ac)
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id="sess-vip",
                message="vip",
                status="vip_manual_handling",
            )
        )
        db.session.commit()

        data = self.client.get("/api/recovery-settings").json()
        last_cart = data.get("last_vip_cart_ar") or ""
        self.assertTrue("1200" in last_cart.replace(",", ""), msg=last_cart)
        self.assertIn("تنبيه", data.get("last_vip_alert_ar") or "")

    def test_dashboard_vip_page_has_form(self) -> None:
        html = self.client.get("/dashboard").text or ""
        self.assertIn('id="ma-vip-settings-form"', html)
        self.assertIn("merchant_vip_settings.js", html)
        self.assertIn("تفعيل متابعة السلال المهمة", html)


if __name__ == "__main__":
    unittest.main()
