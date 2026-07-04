# -*- coding: utf-8 -*-
"""Merchant Daily Brief Composer v2 — topic aggregation tests."""
from __future__ import annotations

import unittest

from services.merchant_daily_brief_composer_v2 import (
    COMPOSER_VERSION,
    aggregation_key_for_decision,
    compose_merchant_daily_brief_v2,
    group_decisions_into_topics,
    is_achievement_decision,
    validate_merchant_daily_brief_v2,
)
from services.merchant_daily_brief_v1 import (
    MAX_BRIEF_ITEMS,
    collect_published_decisions_from_bundles_v1,
)
from services.merchant_decision_layer_v1 import (
    CLASS_NEEDS_ATTENTION,
    CLASS_OBSERVATION,
    CLASS_SUGGESTED_ACTION,
    LIFECYCLE_PUBLISHED,
    VERIFY_PASSED,
)
from services.merchant_decision_registry_v1 import DECISION_ID_OBTAIN_CONTACT


def _published_decision(**overrides: object) -> dict:
    base = {
        "decision_id": DECISION_ID_OBTAIN_CONTACT,
        "decision_class": CLASS_NEEDS_ATTENTION,
        "evidence_ids": ["customer_journey"],
        "proof_sources": ["demo:cart:1"],
        "confidence": "medium",
        "commercial_goal": "obtain_contact",
        "merchant_action": "none",
        "priority": 200,
        "expiration": {"ttl_hours": 72},
        "suppression_state": "none",
        "verification_status": VERIFY_PASSED,
        "decision_explanation": {
            "rationale_ar": "سلة بانتظار رقم العميل",
            "why_now_ar": "لا يمكن متابعة الاسترجاع بدون رقم",
            "if_omitted_ar": "—",
        },
        "decision_timestamp": "2026-07-04T12:00:00+00:00",
        "lifecycle_state": LIFECYCLE_PUBLISHED,
        "owner": "merchant_decision_layer_v1",
        "verification_method": "test",
        "merge_key": "cart:demo:1",
        "action_key": "obtain_contact",
    }
    base.update(overrides)
    return base


def _bundle(*decisions: dict) -> dict:
    return {"version": "v1", "decisions": list(decisions), "suppressed": []}


class MerchantDailyBriefComposerV2Tests(unittest.TestCase):
    def test_five_obtain_contact_aggregate_to_one_topic(self) -> None:
        decisions = [
            _published_decision(merge_key=f"cart:{i}", proof_sources=[f"demo:cart:{i}"])
            for i in range(5)
        ]
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[_bundle(*decisions)],
            brief_date="2026-07-04",
        )
        self.assertEqual(brief["composer_version"], COMPOSER_VERSION)
        self.assertEqual(len(brief["attention_items"]), 1)
        topic = brief["attention_items"][0]
        self.assertEqual(topic["decision_count"], 5)
        self.assertEqual(len(topic["source_decision_ids"]), 5)
        self.assertIn("5 عملاء", topic["headline_ar"])
        self.assertEqual(validate_merchant_daily_brief_v2(brief), [])

    def test_achievements_before_attention_in_payload(self) -> None:
        obs = _published_decision(
            decision_id="decision_monitor_return",
            decision_class=CLASS_OBSERVATION,
            merchant_action="monitor",
            action_key="monitor",
            merge_key="cart:obs:1",
            priority=100,
        )
        attn = _published_decision(
            merge_key="cart:attn:1",
            priority=300,
            decision_class=CLASS_SUGGESTED_ACTION,
            merchant_action="execute",
            decision_id="decision_contact_customer",
            action_key="contact_customer",
        )
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[_bundle(attn, obs)],
            brief_date="2026-07-04",
        )
        self.assertEqual(len(brief["achievements"]), 1)
        self.assertEqual(len(brief["attention_items"]), 1)
        self.assertEqual(brief["achievements"][0]["section"], "achievement")
        self.assertEqual(brief["attention_items"][0]["section"], "attention")
        self.assertFalse(brief["empty"])

    def test_no_duplicate_attention_topics(self) -> None:
        decisions = [
            _published_decision(merge_key=f"cart:{i}", proof_sources=[f"x:{i}"])
            for i in range(4)
        ]
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[_bundle(*decisions)],
            brief_date="2026-07-04",
        )
        keys = [t["aggregation_key"] for t in brief["attention_items"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_no_decision_loss(self) -> None:
        decisions = [
            _published_decision(merge_key=f"cart:{i}", proof_sources=[f"p:{i}"])
            for i in range(7)
        ]
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[_bundle(*decisions)],
            brief_date="2026-07-04",
        )
        collected = collect_published_decisions_from_bundles_v1([_bundle(*decisions)])
        traced: set[str] = set()
        for topic in brief["achievements"] + brief["attention_items"]:
            traced.update(topic["source_decision_ids"])
        self.assertEqual(len(traced), len(collected))
        self.assertEqual(brief["observability"]["decisions_composed"], len(collected))

    def test_attention_capped_at_max_five_topics(self) -> None:
        decisions = []
        for i in range(8):
            decisions.append(
                _published_decision(
                    merge_key=f"cart:{i}",
                    proof_sources=[f"p:{i}"],
                    commercial_goal=f"goal_{i}",
                    action_key=f"action_{i}",
                )
            )
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[_bundle(*decisions)],
            brief_date="2026-07-04",
        )
        self.assertEqual(len(brief["attention_items"]), MAX_BRIEF_ITEMS)
        self.assertEqual(brief["item_count"], MAX_BRIEF_ITEMS)

    def test_unrelated_decisions_do_not_aggregate(self) -> None:
        a = _published_decision(
            merge_key="cart:a",
            decision_id="decision_contact_customer",
            action_key="contact_customer",
            commercial_goal="recover_revenue",
        )
        b = _published_decision(
            merge_key="cart:b",
            decision_id="decision_fix_channel",
            action_key="fix_channel",
            commercial_goal="fix_channel",
            decision_class=CLASS_SUGGESTED_ACTION,
            priority=350,
        )
        achievements, attention = group_decisions_into_topics(
            [a, b], brief_date="2026-07-04"
        )
        self.assertEqual(len(attention), 2)
        self.assertEqual(len(achievements), 0)

    def test_is_achievement_decision_observation_and_monitor(self) -> None:
        self.assertTrue(
            is_achievement_decision(
                _published_decision(
                    decision_class=CLASS_OBSERVATION,
                    merchant_action="monitor",
                )
            )
        )
        self.assertFalse(
            is_achievement_decision(
                _published_decision(decision_class=CLASS_NEEDS_ATTENTION)
            )
        )

    def test_aggregation_key_includes_family_action_goal(self) -> None:
        d = _published_decision()
        key = aggregation_key_for_decision(d)
        self.assertIn(DECISION_ID_OBTAIN_CONTACT, key)
        self.assertIn("obtain_contact", key)

    def test_confidence_unchanged_on_representative(self) -> None:
        decisions = [
            _published_decision(
                merge_key=f"cart:{i}",
                confidence="high" if i == 0 else "low",
                priority=200 + i,
            )
            for i in range(3)
        ]
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[_bundle(*decisions)],
            brief_date="2026-07-04",
        )
        topic = brief["attention_items"][0]
        self.assertEqual(topic["confidence"], "low")
        self.assertEqual(topic["representative_decision_id"], DECISION_ID_OBTAIN_CONTACT)

    def test_empty_brief_when_no_decisions(self) -> None:
        brief = compose_merchant_daily_brief_v2(decision_bundles=[])
        self.assertTrue(brief["empty"])
        self.assertEqual(brief["achievements"], [])
        self.assertEqual(brief["attention_items"], [])


if __name__ == "__main__":
    unittest.main()
