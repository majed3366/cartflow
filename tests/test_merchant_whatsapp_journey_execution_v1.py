# -*- coding: utf-8 -*-
"""WhatsApp Journey Execution Layer V1."""
from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from extensions import db
from models import Store
from services.admin_whatsapp_visibility_v1 import build_admin_whatsapp_store_row
from services.merchant_whatsapp_connection_readiness_v1 import (
    connection_readiness_for_merchant_api,
)
from services.merchant_whatsapp_journey_execution_v1 import (
    CTA_CREATE_WA_BUSINESS_AR,
    CTA_CONTINUE_ACTIVATION_AR,
    CTA_META_ADVANCED_AR,
    CTA_PREPARE_NEW_NUMBER_AR,
    JOURNEY_STATUS_COMPLETED,
    JOURNEY_STATUS_IN_PROGRESS,
    JOURNEY_STATUS_NOT_STARTED,
    compute_journey_status,
    journey_execution_block,
    WA_BUSINESS_OFFICIAL_URL,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
    JOURNEY_META_READY,
    JOURNEY_NEW_NUMBER,
    JOURNEY_NO_WHATSAPP_BUSINESS,
)


class MerchantWhatsappJourneyExecutionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main.app)
        db.create_all()
        from services.merchant_whatsapp_settings import ensure_store_whatsapp_merchant_settings_schema

        ensure_store_whatsapp_merchant_settings_schema()
        self.zid = f"wa_exec_{uuid.uuid4().hex[:12]}"
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

    def test_existing_journey_cta_continue_activation(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        db.session.commit()
        block = journey_execution_block(self.row)
        self.assertEqual(
            block["execution"]["primary_cta_ar"], CTA_CONTINUE_ACTIVATION_AR
        )

    def test_no_whatsapp_business_cta_create(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_NO_WHATSAPP_BUSINESS
        db.session.commit()
        block = journey_execution_block(self.row)
        self.assertEqual(block["execution"]["primary_cta_ar"], CTA_CREATE_WA_BUSINESS_AR)
        self.assertEqual(block["execution"]["external_url"], WA_BUSINESS_OFFICIAL_URL)

    def test_new_number_cta_prepare(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_NEW_NUMBER
        db.session.commit()
        block = journey_execution_block(self.row)
        self.assertEqual(block["execution"]["primary_cta_ar"], CTA_PREPARE_NEW_NUMBER_AR)
        self.assertEqual(block["execution"]["remaining_step_ar"], "تجهيز الرقم الجديد")

    def test_meta_ready_shows_placeholder_cta(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_META_READY
        db.session.commit()
        block = journey_execution_block(self.row)
        self.assertEqual(block["execution"]["primary_cta_ar"], CTA_META_ADVANCED_AR)
        self.assertIn("قيد التجهيز", block["execution"]["placeholder_ar"])
        self.assertIn("CartFlow Managed", block["execution"]["secondary_note_ar"])

    def test_journey_status_persists_on_store(self) -> None:
        from services.merchant_whatsapp_journey_execution_v1 import (
            apply_whatsapp_onboarding_journey_status_from_body,
            sync_journey_status_on_store,
        )

        self.row.whatsapp_onboarding_journey = JOURNEY_NO_WHATSAPP_BUSINESS
        db.session.commit()
        apply_whatsapp_onboarding_journey_status_from_body(
            self.row, {"whatsapp_onboarding_journey_status": JOURNEY_STATUS_IN_PROGRESS}
        )
        sync_journey_status_on_store(self.row)
        db.session.commit()
        self.assertEqual(
            self.row.whatsapp_onboarding_journey_status,
            JOURNEY_STATUS_IN_PROGRESS,
        )

    def test_api_includes_journey_execution_fields(self) -> None:
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("whatsapp_journey_execution", data)

    def test_existing_journey_completes_on_number_and_recovery(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        self.row.store_whatsapp_number = "+966500000001"
        self.row.whatsapp_recovery_enabled = True
        db.session.commit()
        self.assertEqual(
            compute_journey_status(self.row, JOURNEY_EXISTING_WHATSAPP_BUSINESS),
            JOURNEY_STATUS_COMPLETED,
        )

    def test_new_journey_starts_not_started(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_NEW_NUMBER
        db.session.commit()
        self.assertEqual(
            compute_journey_status(self.row, JOURNEY_NEW_NUMBER),
            JOURNEY_STATUS_NOT_STARTED,
        )

    @patch(
        "services.merchant_whatsapp_connection_readiness_v1.evaluate_onboarding_readiness",
        return_value={
            "flags": {
                "dashboard_ready": True,
                "store_connected": True,
                "whatsapp_configured": False,
                "provider_ready": True,
                "recovery_enabled": False,
                "widget_installed": True,
                "sandbox_mode_active": True,
            },
            "blocking_steps": [],
        },
    )
    def test_readiness_reflects_journey_remaining_step(self, _m: object) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_NO_WHATSAPP_BUSINESS
        db.session.commit()
        ev = connection_readiness_for_merchant_api(self.row)
        af = ev.get("action_first") or {}
        self.assertEqual(af.get("primary_cta_label_ar"), CTA_CREATE_WA_BUSINESS_AR)
        self.assertEqual(af.get("next_action_ar"), "إنشاء واتساب أعمال")

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
                "sandbox_mode_active": False,
            },
            "blocking_steps": [],
        },
    )
    def test_readiness_existing_journey_continue_cta(self, _m: object) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_EXISTING_WHATSAPP_BUSINESS
        db.session.commit()
        ev = connection_readiness_for_merchant_api(self.row)
        af = ev.get("action_first") or {}
        self.assertEqual(af.get("primary_cta_label_ar"), CTA_CONTINUE_ACTIVATION_AR)

    def test_admin_row_includes_journey_status(self) -> None:
        self.row.whatsapp_onboarding_journey = JOURNEY_NO_WHATSAPP_BUSINESS
        self.row.whatsapp_onboarding_journey_status = JOURNEY_STATUS_IN_PROGRESS
        db.session.commit()
        admin = build_admin_whatsapp_store_row(self.row)
        d = admin.to_api_dict()
        self.assertEqual(
            d["whatsapp_onboarding_journey_status"], JOURNEY_STATUS_IN_PROGRESS
        )
        self.assertEqual(d["whatsapp_onboarding_journey_status_ar"], "قيد التنفيذ")

    def test_js_wires_execution_cta_actions(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("open_whatsapp_business_guide", js)
        self.assertIn("prepare_new_number", js)
        self.assertIn("open_meta_advanced_placeholder", js)
        self.assertIn("ma-wa-journey-progress", js)


if __name__ == "__main__":
    unittest.main()
