# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest

from services.recovery_product_context import (
    infer_category_from_product_name,
    recovery_product_context_from_payload,
)


class RecoveryProductContextTests(unittest.TestCase):
    def test_infer_category_electronics(self) -> None:
        self.assertEqual(infer_category_from_product_name("سماعة بلوتوث"), "إلكترونيات")

    def test_cheaper_alternative_from_two_items(self) -> None:
        payload = {
            "cart": {
                "items": [
                    {"name": "سماعة فاخرة", "price": 300},
                    {"name": "سماعة اقتصادية", "price": 99},
                ]
            }
        }
        ctx = recovery_product_context_from_payload(payload)
        self.assertEqual(ctx.current_product_name, "سماعة فاخرة")
        self.assertEqual(ctx.cheaper_alternative_name, "سماعة اقتصادية")
        self.assertEqual(ctx.cheaper_alternative_price, 99.0)

    def test_empty_payload(self) -> None:
        ctx = recovery_product_context_from_payload(None)
        self.assertIsNone(ctx.current_product_name)
        self.assertEqual(ctx.line_item_count, 0)


if __name__ == "__main__":
    unittest.main()
