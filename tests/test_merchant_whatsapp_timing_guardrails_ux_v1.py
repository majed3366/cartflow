# -*- coding: utf-8 -*-
"""Timing guardrail merchant UX copy — display only."""
from __future__ import annotations

import unittest

from services.merchant_whatsapp_timing_guardrails_v1 import (
    EXECUTION_STAGE_2,
    EXECUTION_STAGE_3,
    apply_timing_guardrails_to_reason_templates_incoming,
    clamp_stage_delay,
)
from services.merchant_whatsapp_timing_guardrails_ux_v1 import (
    enrich_timing_adjustment_for_merchant,
    format_delay_display_ar,
    stage_timing_panel_fields,
    timing_guardrails_ux_for_api,
)


class TestTimingGuardrailsUxV1(unittest.TestCase):
    def test_format_delay_display_ar(self) -> None:
        self.assertEqual(format_delay_display_ar(60, "minute"), "60 دقيقة")
        self.assertEqual(format_delay_display_ar(6, "hour"), "6 ساعات")
        self.assertEqual(format_delay_display_ar(24, "hour"), "24 ساعة")
        self.assertEqual(format_delay_display_ar(1, "day"), "1 يوم")

    def test_stage2_panel_fields(self) -> None:
        panel = stage_timing_panel_fields(
            EXECUTION_STAGE_2, current_delay=6, current_unit="hour"
        )
        self.assertEqual(panel["recommended_timing_ar"], "24 ساعة")
        self.assertEqual(panel["minimum_allowed_timing_ar"], "6 ساعات")
        self.assertEqual(panel["current_saved_timing_ar"], "6 ساعات")

    def test_stage3_panel_fields(self) -> None:
        panel = stage_timing_panel_fields(
            EXECUTION_STAGE_3, current_delay=1, current_unit="day"
        )
        self.assertEqual(panel["recommended_timing_ar"], "72 ساعة")
        self.assertEqual(panel["minimum_allowed_timing_ar"], "24 ساعة")
        self.assertEqual(panel["current_saved_timing_ar"], "1 يوم")

    def test_stage2_sixty_minutes_explicit_messages(self) -> None:
        result = clamp_stage_delay(EXECUTION_STAGE_2, 60, "minute")
        enriched = enrich_timing_adjustment_for_merchant(result)
        self.assertTrue(enriched["was_adjusted"])
        self.assertEqual(
            enriched["denial_message_ar"],
            "لا يمكن ضبط المرحلة الثانية بأقل من 6 ساعات.",
        )
        self.assertEqual(
            enriched["saved_message_ar"],
            "تم حفظ التوقيت على 6 ساعات.",
        )
        self.assertEqual(
            enriched["feedback_lines_ar"],
            [
                "لا يمكن ضبط المرحلة الثانية بأقل من 6 ساعات.",
                "تم حفظ التوقيت على 6 ساعات.",
            ],
        )

    def test_stage3_two_hours_explicit_messages(self) -> None:
        result = clamp_stage_delay(EXECUTION_STAGE_3, 2, "hour")
        enriched = enrich_timing_adjustment_for_merchant(result)
        self.assertTrue(enriched["was_adjusted"])
        self.assertEqual(
            enriched["denial_message_ar"],
            "لا يمكن ضبط المرحلة الثالثة بأقل من 24 ساعة.",
        )
        self.assertEqual(
            enriched["saved_message_ar"],
            "تم حفظ التوقيت على 24 ساعة.",
        )

    def test_apply_guardrails_save_feedback_lines(self) -> None:
        incoming = {
            "price": {
                "messages": [
                    {"delay": 60, "unit": "minute", "text": "a"},
                    {"delay": 60, "unit": "minute", "text": "b"},
                    {"delay": 2, "unit": "hour", "text": "c"},
                ]
            }
        }
        _, ack = apply_timing_guardrails_to_reason_templates_incoming(incoming)
        self.assertTrue(ack["adjusted"])
        lines = ack["feedback_lines_ar"]
        self.assertIn(
            "لا يمكن ضبط المرحلة الثانية بأقل من 6 ساعات.", lines
        )
        self.assertIn("تم حفظ التوقيت على 6 ساعات.", lines)
        self.assertIn(
            "لا يمكن ضبط المرحلة الثالثة بأقل من 24 ساعة.", lines
        )
        self.assertIn("تم حفظ التوقيت على 24 ساعة.", lines)

    def test_timing_guardrails_ux_api_payload(self) -> None:
        ux = timing_guardrails_ux_for_api()
        self.assertIn("policy_explanation_ar", ux)
        self.assertIn("stage_panels", ux)
        self.assertEqual(
            ux["stage_panels"]["2"]["minimum_allowed_timing_ar"], "6 ساعات"
        )


if __name__ == "__main__":
    unittest.main()
