# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.recovery_reply_suggestions import (
    effective_suggestion_intent,
    get_recovery_reply_suggestion,
)


class RecoveryReplySuggestionsTests(unittest.TestCase):
    def test_price_reassurance(self) -> None:
        s = get_recovery_reply_suggestion("price", "غالي")
        self.assertIn("نفهمك", s["suggested_reply"])
        self.assertIn("السعر", s["suggested_reply"])
        self.assertIn("سعر", s["suggested_action"])

    def test_delivery_suggestion(self) -> None:
        s = get_recovery_reply_suggestion("delivery", "متى يوصل؟")
        self.assertIn("التوصيل", s["suggested_reply"])
        self.assertIn("شحن", s["suggested_action"])

    def test_shipping_maps_to_delivery(self) -> None:
        s = get_recovery_reply_suggestion("shipping", "تكلفة الشحن")
        self.assertIn("التوصيل", s["suggested_reply"])
        self.assertEqual(effective_suggestion_intent("shipping"), "delivery")

    def test_ready_to_buy_checkout(self) -> None:
        s = get_recovery_reply_suggestion("ready_to_buy", "وين الرابط")
        self.assertIn("رابط", s["suggested_reply"])
        self.assertIn("الطلب", s["suggested_action"])

    def test_fallback_other(self) -> None:
        s = get_recovery_reply_suggestion("other", "؟")
        self.assertIn("نساعدك", s["suggested_reply"])


if __name__ == "__main__":
    unittest.main()
