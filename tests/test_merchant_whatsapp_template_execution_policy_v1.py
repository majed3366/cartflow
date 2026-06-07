# -*- coding: utf-8 -*-
"""WhatsApp Production Strategy Phase 3 — template execution policy helpers."""
from __future__ import annotations

import unittest

from services.merchant_whatsapp_template_execution_policy_v1 import (
    MAX_EXECUTION_STAGES,
    STAGE_FINAL_FOLLOWUP,
    STAGE_GENERAL_FOLLOWUP,
    STAGE_REASON_RECOVERY,
    STOP_CUSTOMER_PURCHASED,
    STOP_CUSTOMER_RETURNED,
    STOP_SEQUENCE_COMPLETE,
    evaluate_follow_up_policy,
    evaluate_hard_stop_conditions,
    evaluate_template_disabled_policy,
    evaluate_vip_execution_policy,
    execution_policy_summary_for_api,
    managed_sender_policy_controls,
    resolve_template_key_for_execution_stage,
)


class MerchantWhatsappTemplateExecutionPolicyV1Tests(unittest.TestCase):
    def test_stage1_maps_reason_to_price_template(self) -> None:
        self.assertEqual(
            resolve_template_key_for_execution_stage(1, "price_high"),
            "PRICE_TEMPLATE",
        )

    def test_stage2_uses_followup_1(self) -> None:
        self.assertEqual(
            resolve_template_key_for_execution_stage(STAGE_GENERAL_FOLLOWUP, "price"),
            "FOLLOWUP_1_TEMPLATE",
        )

    def test_stage3_uses_followup_2(self) -> None:
        self.assertEqual(
            resolve_template_key_for_execution_stage(STAGE_FINAL_FOLLOWUP, "price"),
            "FOLLOWUP_2_TEMPLATE",
        )

    def test_max_three_stages(self) -> None:
        self.assertEqual(MAX_EXECUTION_STAGES, 3)

    def test_hard_stop_purchase_first(self) -> None:
        self.assertEqual(
            evaluate_hard_stop_conditions(
                customer_purchased=True,
                customer_returned=True,
            ),
            STOP_CUSTOMER_PURCHASED,
        )

    def test_hard_stop_return(self) -> None:
        self.assertEqual(
            evaluate_hard_stop_conditions(customer_returned=True),
            STOP_CUSTOMER_RETURNED,
        )

    def test_follow_up_advances_on_no_response(self) -> None:
        d = evaluate_follow_up_policy(current_stage=1, no_response=True)
        self.assertTrue(d.allowed)
        self.assertEqual(d.stage, 2)
        self.assertEqual(d.template_key, "FOLLOWUP_1_TEMPLATE")

    def test_follow_up_stops_after_stage_3(self) -> None:
        d = evaluate_follow_up_policy(current_stage=3, no_response=True)
        self.assertFalse(d.allowed)
        self.assertEqual(d.stop_reason, STOP_SEQUENCE_COMPLETE)

    def test_follow_up_stops_on_purchase(self) -> None:
        d = evaluate_follow_up_policy(current_stage=2, customer_purchased=True)
        self.assertFalse(d.allowed)
        self.assertEqual(d.stop_reason, STOP_CUSTOMER_PURCHASED)

    def test_template_disabled_fallback_unknown(self) -> None:
        class _Store:
            whatsapp_recovery_enabled = True
            whatsapp_template_overrides_json = (
                '{"PRICE_TEMPLATE": {"enabled": false}}'
            )

        d = evaluate_template_disabled_policy("price", _Store(), allow_unknown_fallback=True)
        self.assertTrue(d.allowed)
        self.assertEqual(d.template_key, "UNKNOWN_REASON_TEMPLATE")

    def test_template_disabled_no_fallback(self) -> None:
        class _Store:
            whatsapp_recovery_enabled = True
            whatsapp_template_overrides_json = (
                '{"PRICE_TEMPLATE": {"enabled": false}}'
            )

        d = evaluate_template_disabled_policy(
            "price", _Store(), allow_unknown_fallback=False
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.skip_reason, "unknown_fallback_not_allowed")

    def test_vip_lane_isolation_policy(self) -> None:
        vip = evaluate_vip_execution_policy(is_vip_cart=True, vip_notify_enabled=True)
        self.assertFalse(vip["vip_counts_as_customer_recovery"])
        self.assertTrue(vip["vip_lane_isolated_from_customer_sequence"])
        self.assertTrue(vip["vip_triggers_merchant_intervention"])

    def test_managed_sender_policy_not_public_quota(self) -> None:
        m = managed_sender_policy_controls()
        self.assertFalse(m["public_quota_exposed"])
        self.assertTrue(m["controls"]["daily_store_send_guard"]["enabled"])

    def test_execution_policy_api_summary(self) -> None:
        summary = execution_policy_summary_for_api()
        self.assertEqual(summary["policy_version"], "v1")
        self.assertTrue(summary["architecture_only"])
        self.assertEqual(summary["max_execution_stages"], 3)
        self.assertIn("hard_stop_reasons", summary)
        self.assertIn("admin_visibility_schema", summary)


if __name__ == "__main__":
    unittest.main()
