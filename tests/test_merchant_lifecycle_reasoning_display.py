# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.merchant_lifecycle_reasoning_display import (
    merchant_message_preview_display,
    merchant_reason_goal_ar,
    merchant_reply_preview_display,
    merchant_sent_message_line_ar,
)


class MerchantLifecycleReasoningDisplayTests(unittest.TestCase):
    def test_shipping_goal(self) -> None:
        self.assertEqual(merchant_reason_goal_ar("shipping"), "طمأنة حول الشحن")

    def test_message_preview_truncates(self) -> None:
        long = "أ" * 120
        out = merchant_message_preview_display(message_preview=long, max_len=80)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertLessEqual(len(out), 80)
        self.assertTrue(out.endswith("…"))

    def test_sent_line_with_preview(self) -> None:
        line = merchant_sent_message_line_ar(message_preview="نعرف أن الشحن مهم")
        self.assertIn("نعرف", line)

    def test_sent_line_without_preview(self) -> None:
        line = merchant_sent_message_line_ar()
        self.assertIn("مناسبة", line)

    def test_reply_preview(self) -> None:
        self.assertEqual(
            merchant_reply_preview_display(inbound_message="نعم"),
            '"نعم"',
        )


if __name__ == "__main__":
    unittest.main()
