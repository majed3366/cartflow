# -*- coding: utf-8 -*-
"""WhatsApp Onboarding Journeys V1.1 — merchant can change journey."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from extensions import db
from models import Store
from services.merchant_whatsapp_connection_readiness_v1 import (
    connection_readiness_for_merchant_api,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_CHANGE_CTA_AR,
    JOURNEY_CHANGE_SAFETY_AR,
    JOURNEY_CURRENT_PATH_LABEL_AR,
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
    JOURNEY_NEW_NUMBER,
    JOURNEY_NO_WHATSAPP_BUSINESS,
    apply_whatsapp_onboarding_journey_from_body,
    onboarding_journeys_ui_block,
)


class MerchantWhatsappOnboardingJourneysChangeV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_chg_{uuid.uuid4().hex[:12]}"
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()
        self.row = Store(
            zid_store_id=self.zid,
            recovery_delay=5,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            store_whatsapp_number="+966500000099",
            whatsapp_recovery_enabled=True,
        )
        db.session.add(self.row)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.query(Store).filter_by(zid_store_id=self.zid).delete(
            synchronize_session=False
        )
        db.session.commit()

    def test_selected_journey_api_includes_change_cta(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        db.session.commit()
        block = onboarding_journeys_ui_block(self.row)
        self.assertEqual(block["change_journey_cta_ar"], JOURNEY_CHANGE_CTA_AR)
        self.assertEqual(block["current_path_label_ar"], JOURNEY_CURRENT_PATH_LABEL_AR)
        self.assertIn("لا يحذف إعداداتك", block["change_journey_safety_ar"])

    def test_changing_journey_persists_new_value(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        db.session.commit()
        apply_whatsapp_onboarding_journey_from_body(
            self.row, {"whatsapp_onboarding_journey": JOURNEY_NEW_NUMBER}
        )
        db.session.commit()
        self.assertEqual(self.row.whatsapp_onboarding_journey, JOURNEY_NEW_NUMBER)

    def test_changing_journey_preserves_phone_and_recovery(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        db.session.commit()
        apply_whatsapp_onboarding_journey_from_body(
            self.row, {"whatsapp_onboarding_journey": JOURNEY_NO_WHATSAPP_BUSINESS}
        )
        db.session.commit()
        self.assertEqual(self.row.store_whatsapp_number, "+966500000099")
        self.assertTrue(self.row.whatsapp_recovery_enabled)

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value={
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": True,
                "provider_ready": True,
                "recovery_enabled": True,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        },
    )
    def test_readiness_updates_cta_after_journey_change(self, _m: object) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        db.session.commit()
        before = connection_readiness_for_merchant_api(self.row)
        apply_whatsapp_onboarding_journey_from_body(
            self.row, {"whatsapp_onboarding_journey": JOURNEY_NO_WHATSAPP_BUSINESS}
        )
        db.session.commit()
        after = connection_readiness_for_merchant_api(self.row)
        self.assertNotEqual(
            (before.get("action_first") or {}).get("primary_cta_label_ar"),
            (after.get("action_first") or {}).get("primary_cta_label_ar"),
        )
        self.assertEqual(
            (after.get("whatsapp_onboarding_journeys") or {}).get("selected_key"),
            JOURNEY_NO_WHATSAPP_BUSINESS,
        )

    def test_js_wires_change_journey_ux(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("data-ma-wa-change-journey", js)
        self.assertIn(JOURNEY_CHANGE_CTA_AR, js)
        self.assertIn("is-current", js)
        self.assertIn("ma-wa-journey-change-safety", js)
        self.assertIn("change_journey_safety_ar", js)

    def test_selector_marks_current_journey_option(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        db.session.commit()
        block = onboarding_journeys_ui_block(self.row)
        self.assertEqual(len(block["options"]), 4)
        self.assertEqual(block["option_current_badge_ar"], "المسار الحالي")


if __name__ == "__main__":
    unittest.main()
