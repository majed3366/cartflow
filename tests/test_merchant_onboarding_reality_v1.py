# -*- coding: utf-8 -*-
"""Merchant Onboarding Reality v1 — audit matrix (read-only foundation)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.merchant_onboarding_reality_v1 import (
    LEVEL_NOT_STARTED,
    LEVEL_PARTIAL,
    LEVEL_PRODUCTION_READY,
    LEVEL_SANDBOX_ONLY,
    audit_can_self_serve_to_production_ready,
    build_merchant_onboarding_admin_card,
    evaluate_merchant_onboarding_reality,
)


class MerchantOnboardingRealityV1Tests(unittest.TestCase):
    def test_empty_store_not_started(self) -> None:
        r = evaluate_merchant_onboarding_reality(None, emit_log=False)
        self.assertEqual(r.onboarding_state, LEVEL_NOT_STARTED)
        self.assertIn("dashboard_not_initialized", r.missing)

    @patch.dict(os.environ, {"PRODUCTION_MODE": ""}, clear=False)
    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(False, False))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_partial_setup_sandbox_only(
        self, mock_ms: object, _phone: object, _wa: object
    ) -> None:
        mock_ms.return_value = {
            "first_cart_detected": False,
            "first_recovery_scheduled": False,
            "first_whatsapp_sent": False,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.slug = "demo"
        store.zid_store_id = "z1"
        store.access_token = "tok"
        store.is_active = True
        store.recovery_attempts = 2
        store.cartflow_widget_enabled = True
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = ""
        store.trigger_templates_json = ""
        store.recovery_delay_minutes = 15
        store.store_whatsapp_number = ""
        r = evaluate_merchant_onboarding_reality(store, emit_log=False)
        self.assertEqual(r.onboarding_state, LEVEL_SANDBOX_ONLY)

    @patch.dict(
        os.environ,
        {
            "PRODUCTION_MODE": "true",
            "TWILIO_ACCOUNT_SID": "ACx",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
            "TWILIO_STATUS_CALLBACK_URL": "https://app.example/webhook/whatsapp/status",
        },
        clear=False,
    )
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly")
    @patch(
        "services.cartflow_provider_readiness.get_whatsapp_provider_readiness",
        return_value={"ready": True, "provider": "twilio"},
    )
    @patch(
        "services.cartflow_provider_readiness.get_twilio_readiness",
        return_value={"ready": True},
    )
    def test_fully_configured_production_ready(
        self,
        _twilio: object,
        _wa_prov: object,
        mock_phone: object,
        mock_ms: object,
    ) -> None:
        mock_phone.return_value = (True, True)
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": True,
            "first_whatsapp_sent": True,
            "first_reply_received": True,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.slug = "shop-prod"
        store.zid_store_id = "z-prod"
        store.access_token = "tok"
        store.is_active = True
        store.recovery_attempts = 2
        store.cartflow_widget_enabled = True
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = '{"price":{"1":"msg"}}'
        store.trigger_templates_json = "{}"
        store.recovery_delay_minutes = 10
        store.recovery_second_attempt_delay_minutes = 60
        store.store_whatsapp_number = "+966500000001"
        r = evaluate_merchant_onboarding_reality(store, emit_log=False)
        self.assertEqual(r.onboarding_state, LEVEL_PRODUCTION_READY)
        self.assertTrue(r.provider_connected)
        self.assertTrue(r.delivery_truth_ready)
        self.assertTrue(r.templates_present)

    def test_self_serve_audit_not_automatic(self) -> None:
        audit = audit_can_self_serve_to_production_ready()
        self.assertFalse(audit.get("self_serve_to_production_ready"))
        self.assertTrue(audit.get("automation_gaps"))

    def test_admin_card_shape(self) -> None:
        card = build_merchant_onboarding_admin_card(None)
        self.assertEqual(card.get("title_ar"), "جاهزية المتجر")
        self.assertIn("operational", card)
        self.assertIn("reality", card)

    @patch("builtins.print")
    def test_merchant_readiness_log(self, mock_print: object) -> None:
        evaluate_merchant_onboarding_reality(None, emit_log=True)
        printed = " ".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("[MERCHANT READINESS]", printed)


if __name__ == "__main__":
    unittest.main()
