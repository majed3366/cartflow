# -*- coding: utf-8 -*-
"""Journey context remains visible after WhatsApp setup completion."""
from __future__ import annotations

import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from extensions import db
from models import Store
from services.merchant_whatsapp_connection_readiness_v1 import (
    connection_readiness_for_merchant_api,
)
from services.merchant_whatsapp_journey_execution_v1 import (
    CTA_CONTINUE_ACTIVATION_AR,
    JOURNEY_STATUS_COMPLETED,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
    journey_description_ar,
    journey_label_ar,
)
from services.merchant_whatsapp_readiness_presentation_v1 import (
    MERCHANT_JOURNEY_CURRENT_CONTEXT_AR,
    MERCHANT_JOURNEY_CURRENT_SECTION_TITLE_AR,
    MERCHANT_JOURNEY_STATUS_BADGE_COMPLETED_AR,
    MERCHANT_JOURNEY_STATUS_DESC_COMPLETED_AR,
    MERCHANT_JOURNEY_STATUS_SECTION_TITLE_AR,
    MERCHANT_NO_ACTION_AR,
    MERCHANT_PATH_MANAGEMENT_SECTION_TITLE_AR,
    MERCHANT_SENDING_STATUS_PREPARING_AR,
    MERCHANT_SENDING_TITLE_AR,
)


class MerchantWhatsappJourneyVisibilityAfterCompletionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_jvis_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            store_whatsapp_number="+966500000555",
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

    def _completed_ev(self) -> dict:
        with patch(
            "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
            return_value={
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
            },
        ):
            return connection_readiness_for_merchant_api(self.row)

    def test_current_journey_remains_visible_after_completion(self) -> None:
        ev = self._completed_ev()
        vis = ev.get("merchant_journey_visibility") or {}
        current = vis.get("current_journey") or {}
        self.assertTrue(vis.get("active"))
        self.assertEqual(current.get("title_ar"), MERCHANT_JOURNEY_CURRENT_SECTION_TITLE_AR)
        self.assertEqual(
            current.get("path_label_ar"),
            journey_label_ar(JOURNEY_EXISTING_WHATSAPP_BUSINESS),
        )
        self.assertEqual(
            current.get("path_description_ar"),
            journey_description_ar(JOURNEY_EXISTING_WHATSAPP_BUSINESS),
        )
        self.assertEqual(current.get("context_ar"), MERCHANT_JOURNEY_CURRENT_CONTEXT_AR)

    def test_journey_status_remains_visible_after_completion(self) -> None:
        ev = self._completed_ev()
        status = (ev.get("merchant_journey_visibility") or {}).get("journey_status") or {}
        self.assertEqual(status.get("title_ar"), MERCHANT_JOURNEY_STATUS_SECTION_TITLE_AR)
        self.assertEqual(status.get("badge_ar"), MERCHANT_JOURNEY_STATUS_BADGE_COMPLETED_AR)
        self.assertEqual(status.get("description_ar"), MERCHANT_JOURNEY_STATUS_DESC_COMPLETED_AR)

    def test_sending_status_remains_visible_after_completion(self) -> None:
        ev = self._completed_ev()
        prod = ev.get("production_sending_readiness") or {}
        self.assertEqual(prod.get("title_ar"), MERCHANT_SENDING_TITLE_AR)
        self.assertEqual(prod.get("status_ar"), MERCHANT_SENDING_STATUS_PREPARING_AR)
        self.assertIn("أكملت إعداداتك", prod.get("explanation_ar") or "")

    def test_merchant_can_still_access_settings(self) -> None:
        ev = self._completed_ev()
        mgmt = (ev.get("merchant_journey_visibility") or {}).get("path_management") or {}
        af = ev.get("action_first") or {}
        self.assertEqual(mgmt.get("title_ar"), MERCHANT_PATH_MANAGEMENT_SECTION_TITLE_AR)
        self.assertIn("تعديل إعدادات واتساب", mgmt.get("edit_settings_cta_ar") or "")
        self.assertIn("تغيير مسار واتساب", mgmt.get("change_journey_cta_ar") or "")
        cb = af.get("cta_behavior") or {}
        self.assertEqual(cb.get("cta_action"), "scroll_settings")

    def test_no_technical_diagnostics_for_merchants(self) -> None:
        ev = self._completed_ev()
        self.assertNotIn("readiness_diagnostic_temp", ev)
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertNotIn("تشخيص مؤقت", js)

    def test_no_continue_activation_copy_after_completion(self) -> None:
        ev = self._completed_ev()
        af = ev.get("action_first") or {}
        self.assertNotEqual(af.get("primary_cta_label_ar"), CTA_CONTINUE_ACTIVATION_AR)
        self.assertNotIn("متابعة التفعيل", af.get("primary_cta_label_ar") or "")

    def test_no_readiness_failure_language_when_setup_complete(self) -> None:
        ev = self._completed_ev()
        af = ev.get("action_first") or {}
        self.assertEqual(af.get("next_action_ar"), MERCHANT_NO_ACTION_AR)
        self.assertNotIn("أكمل خطوة التفعيل الحالية", af.get("next_action_ar") or "")
        self.assertNotIn("جاري إعداد الاتصال", af.get("title_ar") or "")
        checklist = (ev.get("setup_checklist") or {}).get("checklist_ar") or []
        labels = [i.get("label_ar") for i in checklist]
        self.assertNotIn("واتساب جاهز", labels)

    def test_api_keeps_journey_context_when_completed(self) -> None:
        ev = self._completed_ev()
        self.assertEqual(
            ev.get("whatsapp_onboarding_journey_status"), JOURNEY_STATUS_COMPLETED
        )
        journeys = ev.get("whatsapp_onboarding_journeys") or {}
        self.assertEqual(
            journeys.get("selected_key"), JOURNEY_EXISTING_WHATSAPP_BUSINESS
        )
        completion = (journeys.get("guidance") or {}).get("completion") or {}
        self.assertTrue(completion.get("is_completed"))

    def test_completed_layout_renders_four_sections(self) -> None:
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("renderCompletedJourneyVisibility", js)
        self.assertIn("ma-wa-completed-section-journey", js)
        self.assertIn("ma-wa-completed-section-status", js)
        self.assertIn("ma-wa-completed-section-sending", js)
        self.assertIn("ma-wa-completed-section-management", js)
        self.assertIn("مسار واتساب الحالي", js)
        self.assertIn("حالة المسار", js)
        self.assertIn("حالة الإرسال", js)
        self.assertIn("إدارة المسار", js)
        self.assertIn("data-ma-wa-change-journey", js)
        self.assertIn("data-cf-wa-primary-cta", js)


if __name__ == "__main__":
    unittest.main()
