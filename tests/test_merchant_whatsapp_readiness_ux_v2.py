# -*- coding: utf-8 -*-
"""WhatsApp Readiness UX V2 — action-first presentation (no engine changes)."""
from __future__ import annotations

import unittest

from services.merchant_whatsapp_connection_readiness_v1 import (
    CANONICAL_CONNECTION_STATES,
    CONNECTION_STATE_ACTION_FIRST,
    CONNECTION_STATE_ACTION_REQUIRED,
    CONNECTION_STATE_CONNECTED,
    CONNECTION_STATE_NOT_CONNECTED,
    CONNECTION_STATE_PAUSED,
    CONNECTION_STATE_PENDING_CONFIGURATION,
    CONNECTION_STATE_PROVIDER_ISSUE,
    CONNECTION_STATE_SETUP_REQUIRED,
    build_action_first_card,
)

_JARGON = ("provider", "api", "waba", "cloud api", "token", "webhook")


class WhatsappReadinessUxV2Tests(unittest.TestCase):
    def _assert_card_shape(self, card: dict) -> None:
        for key in (
            "title_ar",
            "next_action_ar",
            "primary_cta_label_ar",
            "primary_cta_href",
            "expected_outcome_ar",
            "single_cta",
        ):
            self.assertIn(key, card, msg=f"missing {key}")
        self.assertTrue(card["title_ar"].strip())
        self.assertTrue(card["primary_cta_label_ar"].strip())
        self.assertTrue(card["expected_outcome_ar"].strip())
        self.assertTrue(card["single_cta"])

    def test_all_states_have_action_first_mapping(self) -> None:
        self.assertEqual(
            set(CONNECTION_STATE_ACTION_FIRST.keys()), set(CANONICAL_CONNECTION_STATES)
        )

    def test_not_connected_rendering(self) -> None:
        card = build_action_first_card(CONNECTION_STATE_NOT_CONNECTED)
        self._assert_card_shape(card)
        self.assertIn("غير مرتبط", card["title_ar"])
        self.assertTrue(card["action_needed"])

    def test_setup_required_rendering(self) -> None:
        card = build_action_first_card(CONNECTION_STATE_SETUP_REQUIRED)
        self._assert_card_shape(card)
        self.assertIn("الإعداد", card["title_ar"])

    def test_pending_configuration_rendering(self) -> None:
        card = build_action_first_card(CONNECTION_STATE_PENDING_CONFIGURATION)
        self._assert_card_shape(card)
        self.assertIn("إعداد الاتصال", card["title_ar"])

    def test_connected_rendering(self) -> None:
        card = build_action_first_card(CONNECTION_STATE_CONNECTED)
        self._assert_card_shape(card)
        self.assertIn("جاهز", card["title_ar"])
        self.assertFalse(card["action_needed"])

    def test_action_required_rendering(self) -> None:
        card = build_action_first_card(CONNECTION_STATE_ACTION_REQUIRED)
        self._assert_card_shape(card)
        self.assertIn("إجراء", card["title_ar"])

    def test_paused_rendering(self) -> None:
        card = build_action_first_card(CONNECTION_STATE_PAUSED)
        self._assert_card_shape(card)
        self.assertIn("متوقف", card["title_ar"])
        self.assertIn("استئناف", card["primary_cta_label_ar"])

    def test_provider_issue_rendering(self) -> None:
        card = build_action_first_card(CONNECTION_STATE_PROVIDER_ISSUE)
        self._assert_card_shape(card)
        self.assertIn("مشكلة", card["title_ar"])

    def test_single_primary_cta_per_state(self) -> None:
        for state in CANONICAL_CONNECTION_STATES:
            card = build_action_first_card(state)
            self.assertTrue(card["single_cta"], msg=state)
            self.assertTrue(card["primary_cta_label_ar"].strip(), msg=state)

    def test_outcome_prefers_engine_expected_outcome(self) -> None:
        card = build_action_first_card(
            CONNECTION_STATE_SETUP_REQUIRED,
            expected_outcome_ar="سيبدأ CartFlow بإرسال رسائل الاسترجاع للعملاء.",
        )
        self.assertEqual(
            card["expected_outcome_ar"],
            "سيبدأ CartFlow بإرسال رسائل الاسترجاع للعملاء.",
        )

    def test_remaining_steps_from_checklist(self) -> None:
        checklist = {
            "checklist_ar": [
                {"label_ar": "ربط المتجر", "complete": True},
                {"label_ar": "ربط واتساب", "complete": False},
            ]
        }
        card = build_action_first_card(
            CONNECTION_STATE_SETUP_REQUIRED, setup_checklist=checklist
        )
        steps = card["remaining_steps_ar"]
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["mark_ar"], "✓")
        self.assertEqual(steps[1]["mark_ar"], "✗")

    def test_unknown_state_falls_back_to_setup(self) -> None:
        card = build_action_first_card("totally_unknown")
        self.assertEqual(card["connection_state"], CONNECTION_STATE_SETUP_REQUIRED)

    def test_merchant_facing_copy_has_no_english_jargon(self) -> None:
        for state, spec in CONNECTION_STATE_ACTION_FIRST.items():
            blob = " ".join(spec.values()).lower()
            for term in _JARGON:
                self.assertNotIn(term, blob, msg=f"{state} leaks '{term}'")


if __name__ == "__main__":
    unittest.main()
