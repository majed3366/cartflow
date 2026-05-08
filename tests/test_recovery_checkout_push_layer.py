# -*- coding: utf-8 -*-
"""تغطية طبقة دفع إكمال الطلب — مرحلة checkout_ready وقرار checkout_push."""
from __future__ import annotations

import unittest

from services.recovery_conversation_state_machine import STAGE_CHECKOUT_READY
from services.recovery_offer_decision import decide_recovery_offer_strategy
from services.recovery_transition_engine import inbound_patch_for_recovery_reply


class RecoveryCheckoutPushLayerTests(unittest.TestCase):
    def test_how_to_order_sets_checkout_ready_and_intent(self) -> None:
        from services.recovery_conversation_state_machine import (
            STAGE_ALTERNATIVE_CONSIDERATION,
        )

        prior = {
            "recovery_reply_intent": "price",
            "recovery_adaptive_stage": STAGE_ALTERNATIVE_CONSIDERATION,
            "recovery_adaptive_turn_count": 3,
        }
        p = inbound_patch_for_recovery_reply("كيف أطلب؟", prior_behavioral=prior)
        self.assertEqual(p.get("recovery_reply_intent"), "ready_to_buy")
        self.assertEqual(p.get("recovery_adaptive_stage"), STAGE_CHECKOUT_READY)

    def test_send_link_first_turn_checkout(self) -> None:
        p = inbound_patch_for_recovery_reply("أرسل الرابط", prior_behavioral=None)
        self.assertEqual(p.get("recovery_reply_intent"), "ready_to_buy")
        self.assertEqual(p.get("recovery_adaptive_stage"), STAGE_CHECKOUT_READY)

    def test_decide_offer_checkout_by_adaptive_stage(self) -> None:
        d = decide_recovery_offer_strategy(
            "other",
            100.0,
            "",
            "تمام",
            adaptive_stage=STAGE_CHECKOUT_READY,
        )
        self.assertEqual(d["strategy_type"], "checkout_push")
        self.assertEqual(d["persuasion_mode"], "checkout_push")
        self.assertEqual(d["confidence_level"], "high")

    def test_price_to_checkout_progression(self) -> None:
        from services.recovery_conversation_state_machine import (
            STAGE_ALTERNATIVE_CONSIDERATION,
            STAGE_PRICE_OBJECTION,
            STAGE_VALUE_REASSURANCE,
            compute_adaptive_transition,
        )

        st1, _, _ = compute_adaptive_transition(
            prev_stage="",
            prev_intent="",
            new_intent="price",
            customer_message="غالي",
            turn_index=1,
        )
        self.assertEqual(st1, STAGE_PRICE_OBJECTION)
        st2, _, _ = compute_adaptive_transition(
            prev_stage=st1,
            prev_intent="price",
            new_intent="price",
            customer_message="ما زال غالي شوي",
            turn_index=2,
        )
        self.assertEqual(st2, STAGE_VALUE_REASSURANCE)
        st3, _, _ = compute_adaptive_transition(
            prev_stage=st2,
            prev_intent="price",
            new_intent="price",
            customer_message="فيه غير",
            turn_index=3,
        )
        self.assertEqual(st3, STAGE_ALTERNATIVE_CONSIDERATION)
        st4, _, _ = compute_adaptive_transition(
            prev_stage=st3,
            prev_intent="price",
            new_intent="ready_to_buy",
            customer_message="تمام كيف أطلب؟",
            turn_index=4,
        )
        self.assertEqual(st4, STAGE_CHECKOUT_READY)


if __name__ == "__main__":
    unittest.main()
