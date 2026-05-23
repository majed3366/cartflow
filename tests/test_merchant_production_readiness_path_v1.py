# -*- coding: utf-8 -*-
"""Merchant Production Readiness Path v1 — progression matrix."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.merchant_onboarding_reality_v1 import (
    LEVEL_NOT_STARTED,
    LEVEL_PARTIAL,
    LEVEL_PRODUCTION_READY,
    LEVEL_SANDBOX_ONLY,
)
from services.merchant_production_readiness_path_v1 import (
    build_merchant_production_readiness_path,
    merchant_understands_next_step,
)


class MerchantProductionReadinessPathV1Tests(unittest.TestCase):
    def test_empty_store_pass(self) -> None:
        path = build_merchant_production_readiness_path(None, emit_logs=False)
        self.assertEqual(path.onboarding_state, LEVEL_NOT_STARTED)
        self.assertGreaterEqual(path.remaining_count, 1)
        self.assertTrue(path.next_action_ar)
        self.assertTrue(merchant_understands_next_step(path))

    @patch.dict(os.environ, {"PRODUCTION_MODE": ""}, clear=False)
    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(False, False))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_sandbox_pass(self, mock_ms: object, *_mocks: object) -> None:
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
        store.reason_templates_json = '{"price":{"1":"msg"}}'
        store.recovery_delay_minutes = 15
        store.store_whatsapp_number = "+966500000001"
        path = build_merchant_production_readiness_path(store, emit_logs=False)
        self.assertEqual(path.onboarding_state, LEVEL_SANDBOX_ONLY)
        labels = [m.label_ar for m in path.missing_items]
        self.assertTrue(
            any("مزود" in lb or "تسليم" in lb or "اعتماد" in lb for lb in labels)
        )
        self.assertTrue(
            "مزود" in path.next_action_ar or path.next_action_ar.startswith("ربط")
        )
        self.assertLessEqual(path.readiness_score, 55)

    @patch.dict(
        os.environ,
        {
            "PRODUCTION_MODE": "true",
            "TWILIO_ACCOUNT_SID": "ACx",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
            "CARTFLOW_PUBLIC_BASE_URL": "https://app.example",
        },
        clear=False,
    )
    @patch(
        "services.cartflow_provider_readiness.get_whatsapp_provider_readiness",
        return_value={"ready": True, "provider": "twilio"},
    )
    @patch(
        "services.cartflow_provider_readiness.get_twilio_readiness",
        return_value={"ready": True},
    )
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(True, True))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_partial_pass(self, mock_ms: object, *_mocks: object) -> None:
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": True,
            "first_whatsapp_sent": True,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.slug = "partial-shop"
        store.zid_store_id = "z-p"
        store.access_token = "tok"
        store.is_active = True
        store.recovery_attempts = 2
        store.cartflow_widget_enabled = True
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = ""
        store.trigger_templates_json = ""
        store.recovery_delay_minutes = 10
        store.store_whatsapp_number = ""
        path = build_merchant_production_readiness_path(store, emit_logs=False)
        self.assertEqual(path.onboarding_state, LEVEL_PARTIAL)
        self.assertGreater(path.readiness_score, 0)
        self.assertLess(path.readiness_score, 100)
        self.assertGreater(path.remaining_count, 0)
        self.assertTrue(path.next_action_ar)

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
    @patch(
        "services.cartflow_provider_readiness.get_whatsapp_provider_readiness",
        return_value={"ready": True, "provider": "twilio"},
    )
    @patch(
        "services.cartflow_provider_readiness.get_twilio_readiness",
        return_value={"ready": True},
    )
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(True, True))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_production_pass(self, mock_ms: object, *_mocks: object) -> None:
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": True,
            "first_whatsapp_sent": True,
            "first_reply_received": True,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.slug = "prod-shop"
        store.zid_store_id = "z-prod"
        store.access_token = "tok"
        store.is_active = True
        store.recovery_attempts = 2
        store.cartflow_widget_enabled = True
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = '{"price":{"1":"hi"}}'
        store.recovery_delay_minutes = 10
        store.recovery_second_attempt_delay_minutes = 60
        store.store_whatsapp_number = "+966500000001"
        path = build_merchant_production_readiness_path(store, emit_logs=False)
        self.assertEqual(path.onboarding_state, LEVEL_PRODUCTION_READY)
        self.assertEqual(path.readiness_score, 100)
        self.assertEqual(path.remaining_count, 0)

    @patch("builtins.print")
    def test_next_action_log(self, mock_print: object) -> None:
        build_merchant_production_readiness_path(None, emit_logs=True)
        printed = " ".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("[MERCHANT NEXT ACTION]", printed)


if __name__ == "__main__":
    unittest.main()
