# -*- coding: utf-8 -*-
"""
Matrix (50): rule-first copy + decision engine — no LLM calls; CI-safe.
Assertions: no discount language in deterministic builder; product wording tied to cart context;
VIP decision layer returns neutral body (see VIP manual integration tests for recovery_scheduled).
"""
from __future__ import annotations

import unittest

from services.ai_message_builder import build_abandoned_cart_message
from services.decision_engine import (
    VIP_CUSTOMER_WHATSAPP_NEUTRAL_BODY,
    decide_recovery_action,
)


def _matrix_rows() -> list[tuple[int, str, str, float]]:
    reasons = [
        "price_high",
        "shipping",
        "warranty",
        "quality",
        "thinking",
        "human_support",
        "other",
    ]
    names = ["حقيقي أ", "SKU-241", "منتج تجريبي", "TrueSound", "عطر"]
    values = [49.0, 100.0, 500.0, 1500.0, 12000.0]
    rows: list[tuple[int, str, str, float]] = []
    for i in range(50):
        rows.append(
            (
                i,
                reasons[i % len(reasons)],
                names[i % len(names)],
                values[i % len(values)],
            )
        )
    return rows


_DISCOUNT_MARKERS = ("%", "٪", "خصم", "discount", "off")


class EnterpriseMessageDisciplineMatrixTests(unittest.TestCase):
    def test_fifty_scenarios_rule_first_copy(self) -> None:
        for idx, _reason, prod_name, cart_val in _matrix_rows():
            with self.subTest(i=idx, product=prod_name):
                ctx = {
                    "customer_name": "عميل",
                    "cart_url": "https://store.example/cart",
                    "cart_value": cart_val,
                    "items": [{"name": prod_name, "price": min(cart_val, 99.0)}],
                }
                msg = build_abandoned_cart_message(ctx)
                low = (msg or "").lower()
                for m in _DISCOUNT_MARKERS:
                    self.assertNotIn(
                        m,
                        low,
                        f"unexpected discount/marketing token in deterministic message: {m!r}",
                    )
                self.assertIn(prod_name, msg, "product label must come from cart context only")
                self.assertNotIn("منتج وهمي", msg)

    def test_vip_decision_neutral_template(self) -> None:
        for tag in ("price_high", "shipping", "", "unknown_x"):
            with self.subTest(reason_tag=tag):
                r = decide_recovery_action(tag, store=None, is_vip_cart_flag=True)
                self.assertEqual(r["message"].strip(), VIP_CUSTOMER_WHATSAPP_NEUTRAL_BODY.strip())
                self.assertTrue(r["send_merchant"])
                self.assertTrue(r["send_customer"])


if __name__ == "__main__":
    unittest.main()
