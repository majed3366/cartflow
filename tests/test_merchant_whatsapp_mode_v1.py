# -*- coding: utf-8 -*-
"""WhatsApp Production Strategy Phase 1 — mode architecture & UX."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

import main
from extensions import db
from models import Store
from services.merchant_whatsapp_mode_v1 import (
    DEFAULT_WHATSAPP_MODE,
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
    merchant_whatsapp_mode_fields_for_api,
    normalize_whatsapp_mode,
)
from services.admin_whatsapp_visibility_v1 import build_admin_whatsapp_store_row


class MerchantWhatsappModeV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        main._ensure_store_widget_schema()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_mode_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
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
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    def test_default_mode_cartflow_managed(self) -> None:
        fields = merchant_whatsapp_mode_fields_for_api(self.row)
        self.assertEqual(fields["whatsapp_mode"], WHATSAPP_MODE_CARTFLOW_MANAGED)
        self.assertEqual(normalize_whatsapp_mode(None), DEFAULT_WHATSAPP_MODE)

    def test_api_includes_mode_and_connection_fields(self) -> None:
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))
        for key in (
            "whatsapp_mode",
            "whatsapp_mode_label_ar",
            "whatsapp_customer_connection_status_ar",
            "whatsapp_enable_recovery_cta_ar",
            "vip_destination_ar",
            "whatsapp_last_validation_ar",
        ):
            self.assertIn(key, data, msg=f"missing {key}")

    def test_post_returns_merchant_whatsapp_mode_in_api(self) -> None:
        post = self.client.post(
            "/api/recovery-settings",
            json={
                "whatsapp_mode": "merchant_whatsapp",
                "whatsapp_recovery_enabled": True,
            },
        )
        self.assertEqual(post.status_code, 200, post.text[:300])
        self.assertEqual(post.json().get("whatsapp_mode"), WHATSAPP_MODE_MERCHANT_WHATSAPP)

    def test_apply_whatsapp_mode_persists_on_store(self) -> None:
        from services.merchant_whatsapp_settings import apply_merchant_whatsapp_settings_from_body

        apply_merchant_whatsapp_settings_from_body(
            self.row,
            {"whatsapp_mode": WHATSAPP_MODE_MERCHANT_WHATSAPP},
        )
        db.session.commit()
        db.session.refresh(self.row)
        self.assertEqual(self.row.whatsapp_mode, WHATSAPP_MODE_MERCHANT_WHATSAPP)

    def test_admin_visibility_row(self) -> None:
        self.row.whatsapp_mode = WHATSAPP_MODE_MERCHANT_WHATSAPP
        self.row.store_whatsapp_number = "+966501112233"
        db.session.commit()
        admin_row = build_admin_whatsapp_store_row(self.row)
        data = admin_row.to_api_dict()
        self.assertEqual(data["whatsapp_mode"], WHATSAPP_MODE_MERCHANT_WHATSAPP)
        self.assertIn("connection_status_ar", data)
        self.assertIn("vip_destination_ar", data)

    def test_dashboard_whatsapp_page_mode_ux(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertIn("ma-wa-enable-recovery-btn", html)
        self.assertIn("CartFlow Managed", html)
        self.assertIn("Merchant WhatsApp", html)
        self.assertIn("رسائل العملاء عبر واتساب", html)


if __name__ == "__main__":
    unittest.main()
