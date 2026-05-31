# -*- coding: utf-8 -*-
"""Onboarding Experience V2 — activation journey payload."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from services.merchant_onboarding_journey_v2 import (
    build_activation_journey_v2,
    journey_copy_is_merchant_safe,
)
from services.merchant_setup_experience_v1 import (
    build_merchant_setup_experience_api_payload,
)


class TestActivationJourneyV2(unittest.TestCase):
    def test_new_merchant_journey_steps_and_progress(self) -> None:
        j = build_activation_journey_v2(None, merchant_user_id=None)
        self.assertEqual(j.version, 2)
        self.assertEqual(j.total_steps, 6)
        self.assertFalse(j.onboarding_complete)
        self.assertTrue(j.show_journey)
        self.assertGreaterEqual(j.completed_steps, 0)
        self.assertIn("خطوات مكتملة", j.progress_label_ar)
        ids = [s.step_id for s in j.steps]
        self.assertEqual(
            ids,
            [
                "account",
                "widget_test",
                "connect_store",
                "configure_whatsapp",
                "review_messages",
                "ready_for_launch",
            ],
        )
        current = [s for s in j.steps if s.status == "current"]
        self.assertEqual(len(current), 1)

    def test_merchant_copy_has_no_technical_jargon(self) -> None:
        j = build_activation_journey_v2(None)
        self.assertTrue(journey_copy_is_merchant_safe(j))
        blob = " ".join(s.title_ar + s.why_ar for s in j.steps)
        self.assertNotIn("OAuth", blob)
        self.assertNotIn("Webhook", blob)

    def test_nav_locks_before_widget_test(self) -> None:
        j = build_activation_journey_v2(None)
        self.assertIn("settings", j.nav_locks)
        self.assertFalse(j.nav_locks["settings"].unlocked)
        self.assertIn("whatsapp", j.nav_locks)
        self.assertFalse(j.nav_locks["whatsapp"].unlocked)

    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_sandbox_unlocks_store_step(self, mock_ms: object) -> None:
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": False,
            "first_whatsapp_sent": False,
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
        j = build_activation_journey_v2(store, merchant_user_id=1)
        widget = next(s for s in j.steps if s.step_id == "widget_test")
        self.assertTrue(widget.is_complete)
        self.assertTrue(j.nav_locks["settings"].unlocked)

    @patch("services.cartflow_onboarding_readiness._milestones_readonly")
    def test_complete_onboarding_shows_readiness_card(self, mock_ms: object) -> None:
        mock_ms.return_value = {
            "first_cart_detected": True,
            "first_recovery_scheduled": True,
            "first_whatsapp_sent": True,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        store = MagicMock()
        store.zid_store_id = "shop2"
        store.merchant_user_id = 2
        store.access_token = "tok"
        store.store_whatsapp_number = "+966500000000"
        store.whatsapp_recovery_enabled = True
        store.reason_templates_json = '{"price":{}}'
        store.cartflow_widget_enabled = True
        j = build_activation_journey_v2(store, merchant_user_id=2)
        self.assertTrue(j.onboarding_complete)
        self.assertFalse(j.show_journey)
        self.assertIsNotNone(j.readiness_card)
        assert j.readiness_card is not None
        self.assertIn("جاهز", j.readiness_card.title_ar)

    def test_api_payload_includes_journey_v2(self) -> None:
        payload = build_merchant_setup_experience_api_payload(None)
        self.assertTrue(payload.get("onboarding_journey_v2"))
        journey = payload.get("activation_journey_v2")
        self.assertIsInstance(journey, dict)
        self.assertEqual(journey.get("version"), 2)
        self.assertIn("steps", journey)


if __name__ == "__main__":
    unittest.main()
