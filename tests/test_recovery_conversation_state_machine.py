# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.recovery_conversation_state_machine import (
    STAGE_ALTERNATIVE_CONSIDERATION,
    STAGE_PRICE_OBJECTION,
    append_adaptive_fields_to_patch,
    asks_alternative_or_comparison,
    compute_adaptive_transition,
)
from services.recovery_transition_engine import inbound_patch_for_recovery_reply


class RecoveryConversationStateMachineTests(unittest.TestCase):
    def test_first_turn_price_stage(self) -> None:
        st, reason, path = compute_adaptive_transition(
            prev_stage="",
            prev_intent="",
            new_intent="price",
            customer_message="غالي شوي",
            turn_index=1,
        )
        self.assertEqual(st, STAGE_PRICE_OBJECTION)
        self.assertTrue(reason)
        self.assertTrue(path)

    def test_second_message_alternative_transition(self) -> None:
        st, reason, _path = compute_adaptive_transition(
            prev_stage=STAGE_PRICE_OBJECTION,
            prev_intent="price",
            new_intent="price",
            customer_message="فيه خيار أرخص؟",
            turn_index=2,
        )
        self.assertEqual(st, STAGE_ALTERNATIVE_CONSIDERATION)
        self.assertIn("بدائل", reason)

    def test_asks_alternative_phrase(self) -> None:
        self.assertTrue(asks_alternative_or_comparison("طيب فيه خيار أرخص؟"))

    def test_inbound_patch_two_turns(self) -> None:
        prior = {
            "recovery_reply_intent": "price",
            "recovery_adaptive_stage": STAGE_PRICE_OBJECTION,
            "recovery_adaptive_turn_count": 1,
            "last_customer_reply_preview": "غالي شوي",
        }
        p = inbound_patch_for_recovery_reply("فيه خيار أرخص؟", prior_behavioral=prior)
        self.assertEqual(p.get("recovery_adaptive_stage"), STAGE_ALTERNATIVE_CONSIDERATION)
        self.assertEqual(p.get("recovery_adaptive_turn_count"), 2)
        self.assertEqual(p.get("recovery_previous_intent"), "price")

    def test_append_patch_sets_memory(self) -> None:
        patch = {"recovery_reply_intent": "price"}
        prior = {
            "recovery_reply_intent": "price",
            "recovery_adaptive_stage": STAGE_PRICE_OBJECTION,
            "recovery_adaptive_turn_count": 1,
            "last_customer_reply_preview": "غالي",
            "recovery_last_offer_strategy_key": "reassurance_only",
        }
        append_adaptive_fields_to_patch(patch, "سعر عالي", prior)
        self.assertEqual(patch.get("recovery_previous_offer_strategy"), "reassurance_only")
        self.assertEqual(patch.get("recovery_previous_customer_reply_preview"), "غالي")


if __name__ == "__main__":
    unittest.main()
