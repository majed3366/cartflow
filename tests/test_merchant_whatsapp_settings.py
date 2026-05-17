# -*- coding: utf-8 -*-
"""Merchant WhatsApp settings persistence via /api/recovery-settings."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

import main
from extensions import db
from models import CartRecoveryLog, Store


class MerchantWhatsappSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        self.zid = f"wa_set_{uuid.uuid4().hex[:12]}"
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
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    def test_get_includes_whatsapp_settings_fields(self) -> None:
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200, r.text[:300])
        data = r.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("whatsapp_recovery_enabled", data)
        self.assertIn("whatsapp_provider_mode", data)
        self.assertIn("whatsapp_status_display", data)
        self.assertIn("last_send_status_ar", data)

    def test_post_persists_number_toggle_and_mode(self) -> None:
        phone = "+966501234567"
        post = self.client.post(
            "/api/recovery-settings",
            json={
                "store_whatsapp_number": phone,
                "whatsapp_recovery_enabled": False,
                "whatsapp_provider_mode": "sandbox",
            },
        )
        self.assertEqual(post.status_code, 200, post.text[:400])
        body = post.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("store_whatsapp_number"), phone)
        self.assertFalse(body.get("whatsapp_recovery_enabled"))
        self.assertEqual(body.get("whatsapp_provider_mode"), "sandbox")

        get2 = self.client.get("/api/recovery-settings")
        data = get2.json()
        self.assertEqual(data.get("store_whatsapp_number"), phone)
        self.assertFalse(data.get("whatsapp_recovery_enabled"))
        self.assertEqual(data.get("whatsapp_provider_mode"), "sandbox")

        saved = db.session.get(Store, self.row.id)
        assert saved is not None
        self.assertEqual((saved.store_whatsapp_number or "").strip(), phone)
        self.assertFalse(bool(saved.whatsapp_recovery_enabled))
        self.assertEqual(saved.whatsapp_provider_mode, "sandbox")

    def test_last_send_status_from_recovery_log(self) -> None:
        db.session.add(
            CartRecoveryLog(
                store_slug=self.zid,
                session_id="sess-wa-settings",
                message="test",
                status="mock_sent",
            )
        )
        db.session.commit()
        data = self.client.get("/api/recovery-settings").json()
        self.assertIn("تم الإرسال", data.get("last_send_status_ar") or "")

    def test_dashboard_whatsapp_page_has_form(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertIn('id="ma-wa-settings-form"', html)
        self.assertIn("merchant_whatsapp_settings.js", html)
        self.assertIn("رقم واتساب المتجر", html)
        self.assertIn("تفعيل إرسال رسائل الاسترجاع", html)


if __name__ == "__main__":
    unittest.main()
