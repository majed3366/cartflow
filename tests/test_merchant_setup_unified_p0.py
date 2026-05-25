# -*- coding: utf-8 -*-
"""Merchant Setup Unified P0 — one guided path from existing evaluators."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from services.merchant_setup_unified_p0 import (
    PROD_OAUTH,
    SANDBOX_TEST_WIDGET,
    SANDBOX_VERIFIED,
    build_merchant_setup_unified_p0,
)
from services.merchant_setup_experience_v1 import build_merchant_setup_experience


class MerchantSetupUnifiedP0Tests(unittest.TestCase):
    def test_new_store_sandbox_path_locked_production(self) -> None:
        u = build_merchant_setup_unified_p0(None, emit_logs=False)
        self.assertTrue(u.unified_p0)
        self.assertTrue(u.setup_mode)
        self.assertFalse(u.sandbox_verified)
        self.assertIn("متجرك قريب من التشغيل الكامل", u.card_title_ar)
        locked = [s for s in u.steps if s.locked]
        self.assertGreaterEqual(len(locked), 4)

    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_sandbox_verified_unlocks_production_steps(self, mock_ms: object) -> None:
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": True,
            "first_whatsapp_sent": True,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.zid_store_id = "shop1"
        store.merchant_user_id = 1
        store.access_token = ""
        store.store_whatsapp_number = ""
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = ""
        store.cartflow_widget_enabled = True
        u = build_merchant_setup_unified_p0(store, merchant_user_id=1, emit_logs=False)
        self.assertTrue(u.sandbox_verified)
        self.assertTrue(u.production_unlocked)
        prod = [s for s in u.steps if s.phase == "production"]
        self.assertFalse(any(s.locked for s in prod))
        verified = next(s for s in u.steps if s.step_id == SANDBOX_VERIFIED)
        self.assertTrue(verified.is_complete)
        self.assertTrue(u.first_recovery_ready)
        self.assertTrue(u.setup_mode)

    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_setup_experience_api_shape_includes_unified(self, mock_ms: object) -> None:
        mock_ms.return_value = {
            "first_cart_detected": False,
            "first_recovery_scheduled": False,
            "first_whatsapp_sent": False,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.zid_store_id = "s2"
        store.merchant_user_id = 2
        exp = build_merchant_setup_experience(store, merchant_user_id=2, emit_logs=False)
        self.assertIn("تجربة الودجيت", exp.card_title_ar + " ".join(s.title_ar for s in exp.steps))

    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_production_oauth_step_separate(self, mock_ms: object) -> None:
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": True,
            "first_whatsapp_sent": True,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.zid_store_id = "s3"
        store.merchant_user_id = 3
        store.access_token = "tok"
        store.store_whatsapp_number = "+966500000001"
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = '{"price":{"1":"x"}}'
        store.cartflow_widget_enabled = True
        with patch(
            "services.merchant_onboarding_v1._step_is_complete",
            side_effect=lambda sid, *_a, **_k: sid == "widget",
        ):
            u = build_merchant_setup_unified_p0(
                store, merchant_user_id=3, emit_logs=False
            )
        oauth = next(s for s in u.steps if s.step_id == PROD_OAUTH)
        self.assertTrue(oauth.is_complete)
        widget_step = next(s for s in u.steps if s.step_id == SANDBOX_TEST_WIDGET)
        self.assertTrue(widget_step.is_complete)


if __name__ == "__main__":
    unittest.main()
