# -*- coding: utf-8 -*-
"""Merchant Daily Brief v1 — governed decision consumer tests."""
from __future__ import annotations

import unittest

from services.merchant_daily_brief_v1 import (
    MAX_BRIEF_ITEMS,
    collect_published_decisions_from_bundles_v1,
    compose_merchant_daily_brief_v1,
    is_decision_brief_eligible_v1,
    project_brief_item_v1,
    validate_merchant_daily_brief_v1,
)
from services.merchant_decision_layer_v1 import (
    CLASS_CRITICAL_ACTION,
    CLASS_NEEDS_ATTENTION,
    CLASS_SUGGESTED_ACTION,
    LIFECYCLE_PUBLISHED,
    VERIFY_PASSED,
)


def _published_decision(**overrides: object) -> dict:
    base = {
        "decision_id": "decision_contact_customer",
        "decision_class": CLASS_SUGGESTED_ACTION,
        "evidence_ids": ["customer_journey"],
        "proof_sources": ["demo:cart:1"],
        "confidence": "high",
        "commercial_goal": "recover_revenue",
        "merchant_action": "execute",
        "priority": 300,
        "expiration": {"ttl_hours": 72},
        "suppression_state": "none",
        "verification_status": VERIFY_PASSED,
        "decision_explanation": {
            "rationale_ar": "سلة تحتاج تدخلاً",
            "why_now_ar": "بيانات التواصل متوفرة",
            "if_omitted_ar": "قد تفوت فرصة",
        },
        "decision_timestamp": "2026-07-04T12:00:00+00:00",
        "lifecycle_state": LIFECYCLE_PUBLISHED,
        "owner": "merchant_decision_layer_v1",
        "verification_method": "test",
        "merge_key": "cart:demo:1",
        "action_key": "contact_customer",
    }
    base.update(overrides)
    return base


def _bundle(*decisions: dict) -> dict:
    return {"version": "v1", "decisions": list(decisions), "suppressed": []}


class MerchantDailyBriefV1Tests(unittest.TestCase):
    def test_eligible_requires_published_passed_not_suppressed(self) -> None:
        self.assertTrue(is_decision_brief_eligible_v1(_published_decision()))
        self.assertFalse(
            is_decision_brief_eligible_v1(
                _published_decision(lifecycle_state="candidate")
            )
        )
        self.assertFalse(
            is_decision_brief_eligible_v1(
                _published_decision(verification_status="suppressed")
            )
        )
        self.assertFalse(
            is_decision_brief_eligible_v1(
                _published_decision(suppression_state="merged")
            )
        )

    def test_empty_brief_when_no_decisions(self) -> None:
        brief = compose_merchant_daily_brief_v1(decision_bundles=[])
        self.assertTrue(brief["empty"])
        self.assertEqual(brief["items"], [])
        self.assertEqual(brief["item_count"], 0)
        self.assertIn("title_ar", brief["empty_state_ar"])
        self.assertEqual(validate_merchant_daily_brief_v1(brief), [])

    def test_max_five_items_cap(self) -> None:
        decisions = [
            _published_decision(
                decision_id=f"d{i}",
                merge_key=f"cart:{i}",
                priority=400 - i,
            )
            for i in range(8)
        ]
        brief = compose_merchant_daily_brief_v1(
            decision_bundles=[_bundle(*decisions)]
        )
        self.assertEqual(len(brief["items"]), MAX_BRIEF_ITEMS)
        self.assertEqual(brief["item_count"], MAX_BRIEF_ITEMS)
        self.assertEqual(validate_merchant_daily_brief_v1(brief), [])

    def test_sorts_by_priority_desc(self) -> None:
        low = _published_decision(
            decision_id="low",
            merge_key="cart:low",
            priority=200,
            decision_class=CLASS_NEEDS_ATTENTION,
        )
        high = _published_decision(
            decision_id="high",
            merge_key="cart:high",
            priority=400,
            decision_class=CLASS_CRITICAL_ACTION,
        )
        brief = compose_merchant_daily_brief_v1(decision_bundles=[_bundle(low, high)])
        self.assertEqual(brief["items"][0]["decision_id"], "high")

    def test_dedupes_merge_key(self) -> None:
        a = _published_decision(decision_id="a", merge_key="cart:same", priority=300)
        b = _published_decision(decision_id="b", merge_key="cart:same", priority=200)
        brief = compose_merchant_daily_brief_v1(decision_bundles=[_bundle(a, b)])
        self.assertEqual(len(brief["items"]), 1)
        self.assertEqual(brief["items"][0]["decision_id"], "a")

    def test_brief_item_contract_fields(self) -> None:
        item = project_brief_item_v1(_published_decision(), brief_date="2026-07-04")
        self.assertEqual(item["what_ar"], "سلة تحتاج تدخلاً")
        self.assertEqual(item["why_ar"], "بيانات التواصل متوفرة")
        self.assertEqual(item["action_ar"], "التواصل مع العميل")
        self.assertTrue(item["action_present"])
        self.assertEqual(item["confidence_label_ar"], "عالية")
        self.assertEqual(item["commercial_goal_label_ar"], "استرجاع المبيعات")
        self.assertEqual(item["evidence_source_ar"], "مسار العميل")

    def test_no_action_for_needs_attention_execute(self) -> None:
        item = project_brief_item_v1(
            _published_decision(
                decision_class=CLASS_NEEDS_ATTENTION,
                merchant_action="execute",
                priority=200,
            )
        )
        self.assertEqual(item["action_ar"], "")
        self.assertFalse(item["action_present"])

    def test_collects_from_multiple_bundles(self) -> None:
        b1 = _bundle(_published_decision(merge_key="cart:1"))
        b2 = _bundle(
            _published_decision(
                decision_id="decision_kl_observation:x",
                merge_key="insight:x",
                priority=100,
            )
        )
        collected = collect_published_decisions_from_bundles_v1([b1, b2])
        self.assertEqual(len(collected), 2)

    def test_skips_suppressed_bundle_entries(self) -> None:
        bundle = {
            "decisions": [_published_decision()],
            "suppressed": [_published_decision(merge_key="cart:sup")],
        }
        collected = collect_published_decisions_from_bundles_v1([bundle])
        self.assertEqual(len(collected), 1)


if __name__ == "__main__":
    unittest.main()
