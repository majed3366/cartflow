# -*- coding: utf-8 -*-
"""Knowledge Routing v1 — platform routing layer tests."""
from __future__ import annotations

import unittest

from services.knowledge_producer_metadata_v1 import enrich_decision_knowledge_metadata_v1
from services.knowledge_routing_v1 import (
    ROUTING_VERSION,
    SURFACE_CART_DETAIL,
    SURFACE_DAILY_BRIEF,
    SURFACE_KNOWLEDGE_LAYER,
    SURFACE_MERCHANT_HOME,
    assign_routing_section_v1,
    compute_routing_priority_v1,
    route_cart_detail_knowledge_v1,
    route_daily_brief_knowledge_v1,
    route_knowledge_for_surface_v1,
    route_knowledge_layer_knowledge_v1,
    route_merchant_home_knowledge_v1,
    validate_routed_knowledge_item_v1,
)
from services.merchant_decision_layer_v1 import (
    CLASS_NEEDS_ATTENTION,
    CLASS_OBSERVATION,
    LIFECYCLE_PUBLISHED,
    VERIFY_PASSED,
)
from services.merchant_decision_registry_v1 import (
    DECISION_ID_CONTACT_CUSTOMER,
    DECISION_ID_OBTAIN_CONTACT,
)


def _norm(value: object) -> str:
    return str(value or "").strip()


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
    proof_source = _norm(
        (base.get("proof_sources") or ["demo:cart:1"])[0]
        if isinstance(base.get("proof_sources"), list)
        else "demo:cart:1"
    )
    enrich_decision_knowledge_metadata_v1(
        base,
        store_slug="demo-store",
        recovery_key=proof_source,
    )
    return base


class KnowledgeRoutingV1Tests(unittest.TestCase):
    def test_routing_priority_is_deterministic(self) -> None:
        item = _published_decision()
        a = compute_routing_priority_v1(item)
        b = compute_routing_priority_v1(item)
        self.assertEqual(a, b)
        self.assertGreater(a, 0)

    def test_identical_input_produces_identical_routing_output(self) -> None:
        decisions = [_published_decision(merge_key=f"cart:{i}", proof_sources=[f"p:{i}"]) for i in range(3)]
        feed_a = route_daily_brief_knowledge_v1(
            decision_bundles=[{"decisions": decisions}],
        )
        feed_b = route_daily_brief_knowledge_v1(
            decision_bundles=[{"decisions": decisions}],
        )
        self.assertEqual(
            [r.get("routing_priority") for r in feed_a["attention_items"]],
            [r.get("routing_priority") for r in feed_b["attention_items"]],
        )

    def test_surface_eligibility_filters_non_brief_items(self) -> None:
        item = _published_decision()
        item["eligible_surfaces"] = ["cart_detail"]
        feed = route_daily_brief_knowledge_v1(
            decision_bundles=[{"decisions": [item]}],
        )
        self.assertEqual(feed["attention_items"], [])
        self.assertEqual(feed["achievements"], [])

    def test_aggregation_by_producer_aggregation_key(self) -> None:
        decisions = [
            _published_decision(merge_key=f"cart:{i}", proof_sources=[f"p:{i}"])
            for i in range(5)
        ]
        keys = {d["aggregation_key"] for d in decisions}
        self.assertEqual(len(keys), 1)
        feed = route_daily_brief_knowledge_v1(
            decision_bundles=[{"decisions": decisions}],
        )
        self.assertEqual(len(feed["attention_items"]), 1)
        routed = feed["attention_items"][0]
        self.assertEqual(routed["member_count"], 5)
        self.assertEqual(validate_routed_knowledge_item_v1(routed), [])

    def test_achievement_section_from_narrative_role_metadata(self) -> None:
        obs = _published_decision(
            decision_id="decision_monitor_return",
            decision_class=CLASS_OBSERVATION,
            merchant_action="monitor",
            action_key="monitor",
            merge_key="cart:obs:1",
            proof_sources=["p:obs:1"],
        )
        self.assertEqual(assign_routing_section_v1(obs), "achievement")
        feed = route_daily_brief_knowledge_v1(
            decision_bundles=[{"decisions": [obs]}],
        )
        self.assertEqual(len(feed["achievements"]), 1)
        self.assertEqual(feed["achievements"][0]["narrative_role"], "achievement")

    def test_attention_capped_at_five(self) -> None:
        decisions = []
        for i in range(8):
            decisions.append(
                _published_decision(
                    merge_key=f"cart:{i}",
                    proof_sources=[f"p:{i}"],
                    commercial_goal=f"goal_{i}",
                    action_key=f"action_{i}",
                    decision_id=f"{DECISION_ID_CONTACT_CUSTOMER}:{i}",
                )
            )
        feed = route_daily_brief_knowledge_v1(decision_bundles=[{"decisions": decisions}])
        self.assertEqual(len(feed["attention_items"]), 5)

    def test_routing_neutrality_no_domain_branching_in_module(self) -> None:
        import inspect
        import services.knowledge_routing_v1 as mod

        source = inspect.getsource(mod)
        forbidden = ("if purchase", "if return", "if hesitation", "if delivered", "if reply")
        lowered = source.lower()
        for token in forbidden:
            self.assertNotIn(token, lowered)

    def test_routed_item_traceability(self) -> None:
        feed = route_daily_brief_knowledge_v1(
            decision_bundles=[{"decisions": [_published_decision()]}],
        )
        routed = feed["attention_items"][0]
        trace = routed["traceability"]
        self.assertEqual(trace["routing_version"], ROUTING_VERSION)
        self.assertEqual(trace["surface"], SURFACE_DAILY_BRIEF)
        self.assertTrue(trace.get("producer_traceability"))

    def test_higher_attention_metadata_ranks_first(self) -> None:
        low = _published_decision(
            merge_key="cart:low",
            proof_sources=["p:low"],
            decision_id=DECISION_ID_OBTAIN_CONTACT,
        )
        high = _published_decision(
            merge_key="cart:high",
            proof_sources=["p:high"],
            decision_id=DECISION_ID_CONTACT_CUSTOMER,
            decision_class=CLASS_NEEDS_ATTENTION,
            merchant_action="execute",
            action_key="contact_customer",
            commercial_goal="recover_revenue",
        )
        feed = route_knowledge_for_surface_v1(
            [low, high],
            surface=SURFACE_DAILY_BRIEF,
            max_attention_items=5,
        )
        priorities = [r["routing_priority"] for r in feed["attention_items"]]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_knowledge_layer_surface_routing(self) -> None:
        from services.knowledge_producer_metadata_v1 import (
            enrich_kl_insight_knowledge_metadata_v1,
        )

        insight = {
            "insight_key": "hesitation_top_reason",
            "category": "hesitation",
            "severity": "info",
            "confidence": "medium",
            "evidence_id": "hesitation_reason",
        }
        enrich_kl_insight_knowledge_metadata_v1(insight, store_slug="demo", window_days=7)
        feed = route_knowledge_layer_knowledge_v1(kl_insights=[insight])
        self.assertEqual(feed["surface"], SURFACE_KNOWLEDGE_LAYER)
        total = len(feed["achievements"]) + len(feed["attention_items"])
        self.assertGreaterEqual(total, 1)
        routed = (feed["achievements"] or feed["attention_items"])[0]
        self.assertEqual(validate_routed_knowledge_item_v1(routed), [])
        trace = routed["traceability"]
        self.assertEqual(trace["surface"], SURFACE_KNOWLEDGE_LAYER)

    def test_cart_detail_surface_routing(self) -> None:
        from services.knowledge_producer_metadata_v1 import (
            enrich_decision_knowledge_metadata_v1,
        )

        decision = {
            "decision_id": "decision_contact_customer",
            "decision_class": "needs_attention",
            "evidence_ids": ["customer_journey"],
            "proof_sources": ["rk:1"],
            "confidence": "medium",
            "commercial_goal": "recover_revenue",
            "merchant_action": "execute",
            "priority": 300,
            "expiration": {"ttl_hours": 72},
            "suppression_state": "none",
            "verification_status": "passed",
            "decision_explanation": {"rationale_ar": "test", "why_now_ar": "now", "if_omitted_ar": "—"},
            "decision_timestamp": "2026-07-05T12:00:00+00:00",
            "lifecycle_state": "published",
            "owner": "merchant_decision_layer_v1",
            "verification_method": "test",
            "merge_key": "cart:1",
            "action_key": "contact_customer",
        }
        enrich_decision_knowledge_metadata_v1(decision, store_slug="demo", recovery_key="rk:1")
        feed = route_cart_detail_knowledge_v1(decision_bundle={"decisions": [decision]})
        self.assertEqual(feed["surface"], SURFACE_CART_DETAIL)
        total = len(feed["achievements"]) + len(feed["attention_items"])
        self.assertGreaterEqual(total, 1)

    def test_merchant_home_surface_routing(self) -> None:
        from services.knowledge_producer_metadata_v1 import enrich_kl_insight_knowledge_metadata_v1

        insight = {
            "insight_key": "hesitation_top_reason",
            "category": "hesitation",
            "severity": "info",
            "title_ar": "test",
            "message_ar": "test",
            "evidence": {"top_reason": "price", "top_count": 1, "hesitation_total": 1},
            "confidence": "medium",
            "data_window": {"days": 7},
            "sample_size": 1,
            "source_tables": ["cart_recovery_reasons"],
            "recommended_action_ar": "test",
            "evidence_id": "hesitation_reason",
        }
        enrich_kl_insight_knowledge_metadata_v1(insight, store_slug="demo", window_days=7)
        feed = route_merchant_home_knowledge_v1(kl_insights=[insight])
        self.assertEqual(feed["surface"], SURFACE_MERCHANT_HOME)
        self.assertGreaterEqual(int(feed["observability"]["eligible_items"]), 1)


if __name__ == "__main__":
    unittest.main()
