# -*- coding: utf-8 -*-
"""Merchant general settings persistence via /api/recovery-settings."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

import main
from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.cartflow_widget_trigger_settings import widget_trigger_config_from_store_row


class MerchantGeneralSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        self.zid = f"gen_set_{uuid.uuid4().hex[:12]}"
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

    def test_get_includes_merchant_general_fields(self) -> None:
        data = self.client.get("/api/recovery-settings").json()
        self.assertTrue(data.get("ok"))
        self.assertIn("settings_notify_vip", data)
        self.assertIn("settings_notify_recovery_success", data)
        self.assertIn("settings_notify_whatsapp_failure", data)
        self.assertIn("widget_enabled", data)
        self.assertIn("widget_display_name", data)
        self.assertIn("merchant_automation_mode", data)
        self.assertIn("merchant_automation_mode_ar", data)
        self.assertIn("settings_notifications_summary_ar", data)
        self.assertIn("settings_updated_at_ar", data)

    def test_post_persists_automation_notify_widget_name(self) -> None:
        r1 = self.client.post(
            "/api/recovery-settings",
            json={
                "merchant_automation_mode": "auto",
                "settings_notify_vip": False,
                "settings_notify_recovery_success": True,
                "settings_notify_whatsapp_failure": True,
                "widget_enabled": True,
                "widget_display_name": "CART",
                "merchant_settings_scope": "general",
            },
        )
        self.assertEqual(r1.status_code, 200, r1.text[:400])
        j1 = r1.json()
        self.assertTrue(j1.get("ok"))
        self.assertEqual(j1.get("merchant_automation_mode"), "auto")
        self.assertFalse(j1.get("settings_notify_vip"))
        self.assertEqual(j1.get("widget_display_name"), "CART")

        j_get = self.client.get("/api/recovery-settings").json()
        self.assertEqual(j_get.get("merchant_automation_mode"), "auto")
        self.assertFalse(j_get.get("settings_notify_vip"))
        self.assertEqual(j_get.get("widget_display_name"), "CART")

        saved = db.session.get(Store, self.row.id)
        assert saved is not None
        self.assertEqual(saved.merchant_automation_mode, "auto")
        self.assertFalse(bool(saved.settings_notify_vip))
        self.assertEqual((saved.widget_display_name or "").strip(), "CART")

    def test_general_only_post_does_not_rewrite_widget_trigger_json(self) -> None:
        before = widget_trigger_config_from_store_row(self.row)
        self.client.post(
            "/api/recovery-settings",
            json={
                "widget_display_name": "CartFlow",
                "merchant_settings_scope": "general",
            },
        )
        db.session.expire(self.row)
        refreshed = db.session.get(Store, self.row.id)
        assert refreshed is not None
        after = widget_trigger_config_from_store_row(refreshed)
        self.assertEqual(after, before)
        self.assertEqual((refreshed.widget_display_name or "").strip(), "CartFlow")

    def test_general_only_patch_response_is_minimal(self) -> None:
        post = self.client.post(
            "/api/recovery-settings",
            json={
                "merchant_automation_mode": "manual",
                "merchant_settings_scope": "general",
            },
        )
        self.assertEqual(post.status_code, 200)
        body = post.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("merchant_automation_mode", body)
        self.assertNotIn("recovery_delay", body)
        self.assertNotIn("widget_trigger_config", body)
        self.assertTrue(body.get("apply_handlers_skipped"))
        self.assertIn("total_duration_ms", body)
        self.assertLess(float(body["total_duration_ms"]), 3000.0)

    def test_test123_persists_after_save_and_get(self) -> None:
        post = self.client.post(
            "/api/recovery-settings",
            json={
                "widget_display_name": "TEST123",
                "merchant_settings_scope": "general",
            },
        )
        self.assertEqual(post.status_code, 200, post.text[:400])
        self.assertEqual(post.json().get("widget_display_name"), "TEST123")

        get_after = self.client.get("/api/recovery-settings").json()
        self.assertEqual(get_after.get("widget_display_name"), "TEST123")
        self.assertEqual(
            get_after.get("settings_widget_name_display_ar"), "TEST123"
        )

        saved = db.session.get(Store, self.row.id)
        assert saved is not None
        self.assertEqual((saved.widget_display_name or "").strip(), "TEST123")

    def test_general_save_does_not_rewrite_recovery_delay(self) -> None:
        self.row.recovery_delay = 17
        db.session.commit()
        self.client.post(
            "/api/recovery-settings",
            json={
                "widget_display_name": "CART",
                "merchant_settings_scope": "general",
            },
        )
        db.session.expire(self.row)
        refreshed = db.session.get(Store, self.row.id)
        assert refreshed is not None
        self.assertEqual(refreshed.recovery_delay, 17)

    def test_dashboard_settings_page_has_form(self) -> None:
        html = self.client.get("/dashboard").text or ""
        self.assertIn('id="ma-general-settings-form"', html)
        self.assertIn("merchant_general_settings.js", html)
        self.assertIn("تنبيه سلة VIP", html)
        self.assertIn("حفظ الإعدادات", html)


if __name__ == "__main__":
    unittest.main()
