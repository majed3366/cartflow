# -*- coding: utf-8 -*-
"""Merchant Setup Experience v1 — merchant-safe setup card."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from services.merchant_setup_experience_v1 import (
    SETUP_STATE_FULL,
    SETUP_STATE_NOT_READY,
    build_merchant_setup_experience,
    merchant_copy_is_safe_for_display,
)


class MerchantSetupExperienceV1Tests(unittest.TestCase):
    def test_not_started_merchant_card(self) -> None:
        exp = build_merchant_setup_experience(None, emit_logs=False)
        self.assertTrue(exp.show_card)
        self.assertEqual(exp.setup_state_label_ar, SETUP_STATE_NOT_READY)
        self.assertEqual(exp.readiness_percent, 0)
        self.assertGreater(exp.remaining_setup_count, 0)
        self.assertTrue(exp.card_title_ar)
        self.assertTrue(merchant_copy_is_safe_for_display(exp))

    def test_no_forbidden_jargon_in_blob(self) -> None:
        exp = build_merchant_setup_experience(None, emit_logs=False)
        blob = json.dumps(exp.to_dict(), ensure_ascii=False).lower()
        for term in (
            "callback",
            "status_callback",
            "twilio",
            "risk",
            "effort",
            "owner",
            "cartflow_ops",
            "provider_not_connected",
            "delivery_truth",
        ):
            self.assertNotIn(term, blob, msg=term)

    @patch.dict(os.environ, {"PRODUCTION_MODE": ""}, clear=False)
    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(False, False))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_sandbox_shows_whatsapp_steps(self, mock_ms: object, *_mocks: object) -> None:
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
        exp = build_merchant_setup_experience(store, emit_logs=False)
        titles = [s.title_ar for s in exp.steps]
        self.assertIn("ربط واتساب", titles)
        self.assertIn("تفعيل الودجيت", titles)
        self.assertTrue(exp.merchant_understands_in_30s)

    @patch.dict(os.environ, {"PRODUCTION_MODE": ""}, clear=False)
    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    @patch("services.cartflow_onboarding_readiness._phone_coverage_readonly", return_value=(True, True))
    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_production_ready_full_state(self, mock_ms: object, *_mocks: object) -> None:
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": True,
            "first_whatsapp_sent": True,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.zid_store_id = "demo"
        store.access_token = "tok"
        store.is_active = True
        store.recovery_attempts = 2
        store.cartflow_widget_enabled = True
        store.store_whatsapp_number = "+966500000001"
        store.whatsapp_recovery_enabled = True
        exp = build_merchant_setup_experience(store, emit_logs=False)
        self.assertEqual(exp.setup_state_label_ar, SETUP_STATE_FULL)
        self.assertEqual(exp.readiness_percent, 100)
        self.assertEqual(exp.remaining_setup_count, 0)


if __name__ == "__main__":
    unittest.main()
