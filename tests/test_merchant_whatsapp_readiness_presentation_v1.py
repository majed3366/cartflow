# -*- coding: utf-8 -*-
"""Merchant readiness presentation — completion vs production sending."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from extensions import db
from models import Store
from services.admin_whatsapp_visibility_v1 import build_admin_whatsapp_store_row
from services.merchant_whatsapp_connection_readiness_v1 import (
    connection_readiness_for_merchant_api,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
)
from services.merchant_whatsapp_readiness_presentation_v1 import (
    MERCHANT_SENDING_READINESS_LABEL_AR,
    MERCHANT_SETUP_COMPLETION_HEADLINE_AR,
)


class MerchantWhatsappReadinessPresentationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_pres_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            store_whatsapp_number="+966500000333",
            whatsapp_recovery_enabled=True,
            whatsapp_onboarding_journey=JOURNEY_EXISTING_WHATSAPP_BUSINESS,
        )
        db.session.add(self.row)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_completed_journey_shows_merchant_completion_block(self, mock_ob: object) -> None:
        mock_ob.return_value = {
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        }
        ev = connection_readiness_for_merchant_api(self.row)
        block = ev.get("merchant_setup_completion") or {}
        self.assertEqual(block.get("headline_ar"), MERCHANT_SETUP_COMPLETION_HEADLINE_AR)
        self.assertIn("✓ رقم واتساب محفوظ", block.get("items_ar") or [])

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_merchant_checklist_no_confusing_whatsapp_ready_x(self, mock_ob: object) -> None:
        mock_ob.return_value = {
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        }
        ev = connection_readiness_for_merchant_api(self.row)
        checklist = (ev.get("setup_checklist") or {}).get("checklist_ar") or []
        labels = [i.get("label_ar") for i in checklist]
        marks = [i.get("mark_ar") for i in checklist]
        self.assertNotIn("واتساب جاهز", labels)
        self.assertNotIn("✗", marks)
        keys = [i.get("key") for i in checklist]
        self.assertNotIn("whatsapp_ready", keys)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_production_sending_readiness_shown_separately(self, mock_ob: object) -> None:
        mock_ob.return_value = {
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        }
        ev = connection_readiness_for_merchant_api(self.row)
        prod = ev.get("production_sending_readiness") or {}
        self.assertEqual(prod.get("label_ar"), MERCHANT_SENDING_READINESS_LABEL_AR)
        self.assertFalse(prod.get("engine_ready"))
        self.assertIn("أكملت إعداداتك", prod.get("explanation_ar") or "")

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_diagnostic_still_exposes_engine_truth(self, mock_ob: object) -> None:
        mock_ob.return_value = {
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        }
        ev = connection_readiness_for_merchant_api(self.row)
        diag = ev.get("readiness_diagnostic_temp") or {}
        item = diag.get("checklist_item") or {}
        self.assertEqual(item.get("label_ar"), "واتساب جاهز")
        self.assertFalse(item.get("ready_value"))

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_admin_dimensions_unchanged(self, mock_ob: object) -> None:
        mock_ob.return_value = {
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        }
        admin = build_admin_whatsapp_store_row(self.row).to_api_dict()
        self.assertTrue(admin.get("readiness_state_ar"))

    def test_js_renders_presentation_sections(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("renderMerchantSetupCompletion", js)
        self.assertIn("renderProductionSendingReadiness", js)
        self.assertIn("production_sending_readiness", js)


if __name__ == "__main__":
    unittest.main()
