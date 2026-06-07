# -*- coding: utf-8 -*-
"""WhatsApp Production Strategy Phase 4 — template library & guardrails."""
from __future__ import annotations

import unittest

from services.merchant_whatsapp_meta_policy_awareness_v1 import (
    TIMING_AUTO_ADJUST_MESSAGE_AR,
    meta_policy_guidance_for_merchant_api,
)
from services.merchant_whatsapp_template_library_v1 import (
    APPROVAL_APPROVED,
    APPROVAL_DISABLED,
    APPROVAL_DRAFT,
    APPROVAL_PENDING_REVIEW,
    APPROVAL_REJECTED,
    can_transition_approval_state,
    resolve_active_version_key,
    resolve_fallback_chain,
    resolve_merchant_visible_template,
    resolve_sendable_template_key,
    transition_approval_state,
)
from services.merchant_whatsapp_timing_guardrails_v1 import (
    EXECUTION_STAGE_2,
    EXECUTION_STAGE_3,
    apply_timing_guardrails_to_reason_templates_incoming,
    clamp_stage_delay,
    delay_to_hours,
    recommended_timing_for_stage,
    timing_guardrails_for_api,
)
from services.trigger_templates_dashboard import enrich_trigger_templates_payload


class MerchantWhatsappTemplateLibraryPhase4Tests(unittest.TestCase):
    def test_approval_state_transitions(self) -> None:
        self.assertTrue(
            can_transition_approval_state(APPROVAL_DRAFT, APPROVAL_PENDING_REVIEW)
        )
        self.assertTrue(
            can_transition_approval_state(
                APPROVAL_PENDING_REVIEW, APPROVAL_APPROVED
            )
        )
        self.assertFalse(
            can_transition_approval_state(APPROVAL_REJECTED, APPROVAL_APPROVED)
        )
        tx = transition_approval_state(
            "PRICE_TEMPLATE_V1", APPROVAL_PENDING_REVIEW
        )
        self.assertTrue(tx["ok"])

    def test_active_version_selection(self) -> None:
        self.assertEqual(
            resolve_active_version_key("PRICE_TEMPLATE"), "PRICE_TEMPLATE_V1"
        )
        merchant = resolve_merchant_visible_template("PRICE_TEMPLATE")
        self.assertEqual(merchant["active_template_key"], "PRICE_TEMPLATE_V1")
        self.assertIn("display_name_ar", merchant)

    def test_fallback_chain_resolution(self) -> None:
        chain = resolve_fallback_chain("PRICE_TEMPLATE")
        self.assertEqual(chain[0], "PRICE_TEMPLATE_V1")
        self.assertIn("UNKNOWN_REASON_TEMPLATE", chain)
        sendable = resolve_sendable_template_key("PRICE_TEMPLATE")
        self.assertEqual(sendable, "PRICE_TEMPLATE_V1")

    def test_fallback_skips_rejected_version(self) -> None:
        from services.merchant_whatsapp_template_library_v1 import (
            TemplateLibraryVersion,
            _version_is_sendable,
        )

        rejected = TemplateLibraryVersion(
            template_key="PRICE_TEMPLATE_V1",
            logical_key="PRICE_TEMPLATE",
            template_version="v1",
            reason_tag="price",
            default_content="x",
            enabled=True,
            active_version=True,
            fallback_template_key="UNKNOWN_REASON_TEMPLATE",
            approval_state=APPROVAL_REJECTED,
            created_at="",
            updated_at="",
        )
        self.assertFalse(_version_is_sendable(rejected))
        self.assertTrue(
            can_transition_approval_state(
                APPROVAL_PENDING_REVIEW, APPROVAL_REJECTED
            )
        )

    def test_timing_guardrail_stage2_minimum_six_hours(self) -> None:
        r = clamp_stage_delay(EXECUTION_STAGE_2, 2, "hour")
        self.assertTrue(r.was_adjusted)
        self.assertEqual(r.clamped_delay, 6.0)
        self.assertEqual(r.clamped_unit, "hour")

    def test_timing_guardrail_stage3_minimum_twenty_four_hours(self) -> None:
        r = clamp_stage_delay(EXECUTION_STAGE_3, 12, "hour")
        self.assertTrue(r.was_adjusted)
        self.assertEqual(r.min_hours, 24.0)
        self.assertGreaterEqual(delay_to_hours(r.clamped_delay, r.clamped_unit), 24.0)

    def test_timing_guardrail_stage1_not_clamped(self) -> None:
        r = clamp_stage_delay(1, 30, "minute")
        self.assertFalse(r.was_adjusted)

    def test_recommended_timing_visibility(self) -> None:
        rec2 = recommended_timing_for_stage(2)
        self.assertIsNotNone(rec2)
        assert rec2 is not None
        self.assertEqual(rec2["recommended_hours"], 24.0)
        self.assertEqual(rec2["min_hours"], 6.0)
        api = timing_guardrails_for_api()
        self.assertEqual(len(api["stages"]), 3)

    def test_apply_guardrails_to_incoming_reason_templates(self) -> None:
        incoming = {
            "price": {
                "messages": [
                    {"delay": 60, "unit": "minute", "text": "a"},
                    {"delay": 2, "unit": "hour", "text": "b"},
                    {"delay": 12, "unit": "hour", "text": "c"},
                ]
            }
        }
        guarded, ack = apply_timing_guardrails_to_reason_templates_incoming(incoming)
        self.assertTrue(ack["adjusted"])
        self.assertEqual(
            ack["timing_guardrail_message_ar"], TIMING_AUTO_ADJUST_MESSAGE_AR
        )
        msgs = guarded["price"]["messages"]
        self.assertEqual(msgs[1]["delay"], 6.0)
        self.assertGreaterEqual(delay_to_hours(msgs[2]["delay"], msgs[2]["unit"]), 24.0)

    def test_meta_policy_guidance_present(self) -> None:
        g = meta_policy_guidance_for_merchant_api()
        self.assertGreaterEqual(len(g["guidance_lines_ar"]), 3)

    def test_trigger_templates_payload_includes_phase4_fields(self) -> None:
        payload = enrich_trigger_templates_payload({"ok": True, "reason_rows": []})
        self.assertIn("timing_guardrails", payload)
        self.assertIn("meta_policy_guidance", payload)
        self.assertIn("template_library_architecture", payload)


if __name__ == "__main__":
    unittest.main()
