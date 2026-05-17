# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.merchant_lifecycle_reasoning_display import (
    merchant_message_preview_display,
    merchant_reason_goal_ar,
    merchant_recovery_attempts_display_ar,
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

    def test_attempts_replied_zero_send(self) -> None:
        self.assertEqual(
            merchant_recovery_attempts_display_ar(0, customer_replied=True),
            "تم إرسال أول رسالة استرداد",
        )

    def test_attempts_one_send(self) -> None:
        self.assertEqual(
            merchant_recovery_attempts_display_ar(1, customer_replied=True),
            "أُرسلت رسالة — لا توجد متابعات إضافية بعد",
        )

    def test_attempts_two_sends(self) -> None:
        self.assertEqual(
            merchant_recovery_attempts_display_ar(2, customer_replied=True),
            "تمت متابعة إضافية",
        )

    def test_attempts_none(self) -> None:
        self.assertEqual(
            merchant_recovery_attempts_display_ar(0, customer_replied=False),
            "لم تبدأ عملية الاسترداد بعد",
        )


if __name__ == "__main__":
    unittest.main()
