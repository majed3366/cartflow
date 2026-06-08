# -*- coding: utf-8 -*-
"""Journey completion vs WhatsApp readiness separation."""
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
from services.merchant_whatsapp_journey_execution_v1 import (
    CTA_CONTINUE_ACTIVATION_AR,
    CTA_REVIEW_SETTINGS_AR,
    JOURNEY_COMPLETED_BADGE_AR,
    JOURNEY_STATUS_COMPLETED,
    compute_journey_status,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
    JOURNEY_META_READY,
)


class MerchantWhatsappJourneyCompletionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_jcomp_{uuid.uuid4().hex[:12]}"
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

    def test_existing_journey_completed_with_number_and_recovery(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        self.row.store_whatsapp_number = "+966500000111"
        self.row.whatsapp_recovery_enabled = True
        db.session.commit()
        self.assertEqual(
            compute_journey_status(self.row, JOURNEY_EXISTING_WHATSAPP_BUSINESS),
            JOURNEY_STATUS_COMPLETED,
        )

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value={
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": True,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        },
    )
    def test_completed_journey_uses_review_settings_cta(self, _m: object) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        self.row.store_whatsapp_number = "+966500000111"
        self.row.whatsapp_recovery_enabled = True
        db.session.commit()
        ev = connection_readiness_for_merchant_api(self.row)
        af = ev.get("action_first") or {}
        self.assertEqual(af.get("primary_cta_label_ar"), CTA_REVIEW_SETTINGS_AR)
        self.assertNotEqual(af.get("primary_cta_label_ar"), CTA_CONTINUE_ACTIVATION_AR)
        self.assertTrue(af.get("journey_completed"))

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value={
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": True,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        },
    )
    def test_completed_journey_shows_completion_ui_fields(self, _m: object) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        self.row.store_whatsapp_number = "+966500000111"
        self.row.whatsapp_recovery_enabled = True
        db.session.commit()
        ev = connection_readiness_for_merchant_api(self.row)
        guidance = (ev.get("whatsapp_onboarding_journeys") or {}).get("guidance") or {}
        completion = guidance.get("completion") or {}
        self.assertTrue(completion.get("is_completed"))
        self.assertEqual(completion.get("badge_ar"), JOURNEY_COMPLETED_BADGE_AR)
        self.assertIn("رقم واتساب محفوظ", completion.get("summary_items_ar") or [])

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value={
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": True,
                "provider_ready": False,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        },
    )
    def test_readiness_remains_independent_when_journey_completed(self, _m: object) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        self.row.store_whatsapp_number = "+966500000111"
        self.row.whatsapp_recovery_enabled = True
        db.session.commit()
        ev = connection_readiness_for_merchant_api(self.row)
        self.assertEqual(
            ev.get("whatsapp_onboarding_journey_status"), JOURNEY_STATUS_COMPLETED
        )
        self.assertNotEqual(ev.get("readiness_overall_ar"), "—")

    def test_meta_ready_journey_completed_on_selection(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_META_READY
        db.session.commit()
        self.assertEqual(
            compute_journey_status(self.row, JOURNEY_META_READY),
            JOURNEY_STATUS_COMPLETED,
        )

    def test_admin_shows_separate_journey_and_readiness_status(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        self.row.store_whatsapp_number = "+966500000111"
        self.row.whatsapp_recovery_enabled = True
        db.session.commit()
        admin = build_admin_whatsapp_store_row(self.row).to_api_dict()
        self.assertEqual(
            admin["whatsapp_onboarding_journey_status"], JOURNEY_STATUS_COMPLETED
        )
        self.assertTrue(admin.get("readiness_state_ar"))

    def test_js_wires_journey_completion_ui(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("ma-wa-readiness-card-completed", js)
        self.assertIn("renderMerchantCompletedUx", js)
        self.assertIn("تم إكمال إعداد واتساب", js)
        self.assertIn("scroll_settings", js)


if __name__ == "__main__":
    unittest.main()
