# -*- coding: utf-8 -*-
"""Merchant onboarding v1 — guided flow derived from readiness."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from services.merchant_onboarding_v1 import (
    TOTAL_GUIDED_STEPS,
    build_merchant_onboarding_flow,
)


class MerchantOnboardingV1Tests(unittest.TestCase):
    @patch.dict(os.environ, {"PRODUCTION_MODE": ""}, clear=False)
    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(False, False))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_new_store_incomplete_onboarding(
        self, mock_ms: object, *_mocks: object
    ) -> None:
        mock_ms.return_value = {
            "first_cart_detected": False,
            "first_recovery_scheduled": False,
            "first_whatsapp_sent": False,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.zid_store_id = "shop-1"
        store.access_token = ""
        store.is_active = True
        store.recovery_attempts = 1
        store.cartflow_widget_enabled = False
        store.store_whatsapp_number = ""
        store.whatsapp_recovery_enabled = True
        store.merchant_user_id = 1
        flow = build_merchant_onboarding_flow(
            store, merchant_user_id=1, emit_logs=False
        )
        self.assertTrue(flow.show_simplified_home)
        self.assertFalse(flow.onboarding_complete)
        self.assertEqual(flow.total_steps, TOTAL_GUIDED_STEPS)
        self.assertGreaterEqual(flow.completed_steps, 1)
        self.assertEqual(flow.current_step_ar, "ربط المتجر")
        titles = [s.title_ar for s in flow.steps]
        self.assertIn("إنشاء الحساب", titles)
        self.assertIn("تفعيل الودجيت", titles)

    @patch.dict(os.environ, {"PRODUCTION_MODE": ""}, clear=False)
    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(True, True))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_existing_merchant_inferred_progress(
        self, mock_ms: object, *_mocks: object
    ) -> None:
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": True,
            "first_whatsapp_sent": True,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.zid_store_id = "merchant-shop-ready"
        store.access_token = "tok"
        store.is_active = True
        store.recovery_attempts = 2
        store.cartflow_widget_enabled = True
        store.store_whatsapp_number = "+966500000001"
        store.whatsapp_recovery_enabled = True
        store.merchant_user_id = 1
        flow = build_merchant_onboarding_flow(
            store, merchant_user_id=1, emit_logs=False
        )
        self.assertTrue(flow.first_recovery_ready)
        self.assertTrue(flow.onboarding_complete)
        self.assertFalse(flow.show_simplified_home)
        self.assertIn("جاهز", flow.card_title_ar)

    def test_no_store_account_step_only(self) -> None:
        flow = build_merchant_onboarding_flow(None, emit_logs=False)
        self.assertFalse(flow.onboarding_complete)
        self.assertEqual(flow.completed_steps, 0)


if __name__ == "__main__":
    unittest.main()
