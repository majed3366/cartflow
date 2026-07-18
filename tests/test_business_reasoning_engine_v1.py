# -*- coding: utf-8 -*-
"""Business Reasoning Engine V1 — deterministic, findings-only, quality gates."""
from __future__ import annotations

import unittest

from services.business_findings_engine_v1 import run_business_findings_engine_v1
from services.business_reasoning_contract_v1 import (
    TYPE_CONFLICT,
    TYPE_CONSTRAINT,
    TYPE_OPPORTUNITY,
    TYPE_PRIORITY,
    TYPE_RELATIONSHIP,
    evaluate_quality_gates_v1,
    is_reasoning_worthy,
    merchant_text_is_clean,
    select_approved_findings_v1,
)
from services.business_reasoning_engine_v1 import (
    run_business_reasoning_engine_v1,
)


class TestBusinessReasoningEngineV1(unittest.TestCase):
    def test_demo_produces_all_five_categories(self) -> None:
        pkg = run_business_reasoning_engine_v1(store_slug="demo", demo_fixture=True)
        self.assertTrue(pkg["ok"])
        self.assertFalse(pkg["ai_used"])
        self.assertFalse(pkg["probabilistic"])
        cards = pkg["reasoning_cards"]
        self.assertGreaterEqual(len(cards), 4)
        types = {c.get("reasoning_type") for c in cards}
        for required in (
            TYPE_RELATIONSHIP,
            TYPE_PRIORITY,
            TYPE_CONFLICT,
            TYPE_CONSTRAINT,
            TYPE_OPPORTUNITY,
        ):
            self.assertIn(required, types)

    def test_deterministic_output(self) -> None:
        a = run_business_reasoning_engine_v1(store_slug="demo", demo_fixture=True)
        b = run_business_reasoning_engine_v1(store_slug="demo", demo_fixture=True)
        self.assertEqual(
            [c["reasoning_id"] for c in a["reasoning_cards"]],
            [c["reasoning_id"] for c in b["reasoning_cards"]],
        )
        self.assertEqual(
            [c["headline"] for c in a["reasoning_cards"]],
            [c["headline"] for c in b["reasoning_cards"]],
        )

    def test_consumes_findings_package_not_evidence(self) -> None:
        findings_pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        pkg = run_business_reasoning_engine_v1(
            store_slug="demo", findings_package=findings_pkg
        )
        self.assertEqual(pkg["input"]["findings_source"], "findings_package")
        self.assertGreaterEqual(pkg["input"]["findings_approved"], 5)
        obs = pkg["observability"]
        self.assertFalse(obs["bypassed_truth"])
        self.assertFalse(obs["bypassed_evidence"])
        self.assertFalse(obs["bypassed_findings"])

    def test_each_card_has_multiple_supporting_findings(self) -> None:
        pkg = run_business_reasoning_engine_v1(store_slug="demo", demo_fixture=True)
        for c in pkg["reasoning_cards"]:
            self.assertGreaterEqual(len(c["supporting_finding_ids"]), 2)
            self.assertGreaterEqual(len(c["supporting_finding_labels"]), 2)
            self.assertTrue(c["quality_gates"]["passed"])
            self.assertTrue(is_reasoning_worthy(c))

    def test_merchant_language_has_no_engineering_terms(self) -> None:
        pkg = run_business_reasoning_engine_v1(store_slug="demo", demo_fixture=True)
        for c in pkg["reasoning_cards"]:
            for field in (
                "headline",
                "business_meaning",
                "recommended_priority",
                "expected_impact",
            ):
                self.assertTrue(merchant_text_is_clean(c.get(field)), msg=c.get(field))

    def test_quality_gates_require_two_findings(self) -> None:
        gates = evaluate_quality_gates_v1(
            supporting_finding_ids=["only-one"],
            creates_business_decision=True,
            merchant_can_act_today=True,
        )
        self.assertFalse(gates["passed"])
        gates_ok = evaluate_quality_gates_v1(
            supporting_finding_ids=["a", "b"],
            creates_business_decision=True,
            merchant_can_act_today=True,
        )
        self.assertTrue(gates_ok["passed"])

    def test_rejects_non_worthy_findings(self) -> None:
        approved = select_approved_findings_v1(
            [
                {"finding_id": "", "title": "x", "merchant_summary": "y"},
                {
                    "finding_id": "f1",
                    "title": "عدد السلال",
                    "merchant_summary": "42",
                    "commercial_meaning": "",
                },
            ]
        )
        self.assertEqual(approved, [])

    def test_guidance_candidates_populated(self) -> None:
        pkg = run_business_reasoning_engine_v1(store_slug="demo", demo_fixture=True)
        g = pkg["guidance_candidates_v1"]
        self.assertIsNotNone(g.get("weekly_priority"))
        self.assertIsNotNone(g.get("top_constraint"))
        self.assertIsNotNone(g.get("primary_relationship"))
        self.assertTrue(str(g["weekly_priority"]["headline"]))

    def test_card_output_shape(self) -> None:
        pkg = run_business_reasoning_engine_v1(store_slug="demo", demo_fixture=True)
        c = pkg["reasoning_cards"][0]
        for key in (
            "headline",
            "business_meaning",
            "recommended_priority",
            "expected_impact",
            "confidence_level",
            "supporting_finding_labels",
        ):
            self.assertIn(key, c)
            self.assertTrue(c[key])

    def test_empty_findings_yields_no_cards(self) -> None:
        pkg = run_business_reasoning_engine_v1(store_slug="demo", findings=[])
        self.assertEqual(pkg["reasoning_cards"], [])
        self.assertEqual(pkg["input"]["findings_approved"], 0)


if __name__ == "__main__":
    unittest.main()
