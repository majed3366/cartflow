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
from services.merchant_whatsapp_journey_execution_v1 import CTA_CONTINUE_ACTIVATION_AR
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
)
from services.merchant_whatsapp_readiness_presentation_v1 import (
    MERCHANT_COMPLETED_HEADLINE_AR,
    MERCHANT_CTA_EDIT_SETTINGS_AR,
    MERCHANT_NO_ACTION_AR,
    MERCHANT_PRODUCTION_TITLE_AR,
    MERCHANT_SENDING_STATUS_PREPARING_AR,
    MERCHANT_SENDING_TITLE_AR,
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

    def _sandbox_flags(self) -> dict:
        return {
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

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_completed_journey_shows_merchant_completed_ux(self, mock_ob: object) -> None:
        mock_ob.return_value = self._sandbox_flags()
        ev = connection_readiness_for_merchant_api(self.row)
        ux = ev.get("merchant_completed_ux") or {}
        self.assertTrue(ux.get("active"))
        self.assertEqual(ux.get("headline_ar"), MERCHANT_COMPLETED_HEADLINE_AR)
        labels = [i.get("label_ar") for i in ux.get("checklist_ar") or []]
        self.assertIn("رقم واتساب محفوظ", labels)
        self.assertIn("استرجاع واتساب مفعل", labels)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_completed_journey_no_continue_activation_cta(self, mock_ob: object) -> None:
        mock_ob.return_value = self._sandbox_flags()
        ev = connection_readiness_for_merchant_api(self.row)
        af = ev.get("action_first") or {}
        self.assertNotEqual(af.get("primary_cta_label_ar"), CTA_CONTINUE_ACTIVATION_AR)
        self.assertEqual(af.get("primary_cta_label_ar"), MERCHANT_CTA_EDIT_SETTINGS_AR)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_completed_journey_no_activation_step_copy(self, mock_ob: object) -> None:
        mock_ob.return_value = self._sandbox_flags()
        ev = connection_readiness_for_merchant_api(self.row)
        af = ev.get("action_first") or {}
        self.assertEqual(af.get("next_action_ar"), MERCHANT_NO_ACTION_AR)
        self.assertNotIn("أكمل خطوة التفعيل الحالية", af.get("next_action_ar") or "")
        self.assertEqual(af.get("title_ar"), MERCHANT_PRODUCTION_TITLE_AR)
        self.assertNotIn("جاري إعداد الاتصال", af.get("title_ar") or "")

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_merchant_checklist_no_confusing_whatsapp_ready_x(self, mock_ob: object) -> None:
        mock_ob.return_value = self._sandbox_flags()
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
        mock_ob.return_value = self._sandbox_flags()
        ev = connection_readiness_for_merchant_api(self.row)
        prod = ev.get("production_sending_readiness") or {}
        self.assertEqual(prod.get("title_ar"), MERCHANT_SENDING_TITLE_AR)
        self.assertEqual(prod.get("status_ar"), MERCHANT_SENDING_STATUS_PREPARING_AR)
        self.assertFalse(prod.get("engine_ready"))
        self.assertIn("أكملت إعداداتك", prod.get("explanation_ar") or "")

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_merchant_api_strips_diagnostic_temp(self, mock_ob: object) -> None:
        mock_ob.return_value = self._sandbox_flags()
        ev = connection_readiness_for_merchant_api(self.row)
        self.assertNotIn("readiness_diagnostic_temp", ev)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness"
    )
    def test_admin_dimensions_unchanged(self, mock_ob: object) -> None:
        mock_ob.return_value = self._sandbox_flags()
        admin = build_admin_whatsapp_store_row(self.row).to_api_dict()
        self.assertTrue(admin.get("readiness_state_ar"))

    def test_js_renders_completed_merchant_ux(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("renderMerchantCompletedUx", js)
        self.assertIn("merchant_completed_ux", js)
        self.assertIn("ma-wa-merchant-completed-ux", js)
        self.assertNotIn("تشخيص مؤقت", js)
        self.assertIn("renderProductionSendingReadiness", js)


if __name__ == "__main__":
    unittest.main()
