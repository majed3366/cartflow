# -*- coding: utf-8 -*-
"""Home Commercial Intelligence Transition V1."""
from __future__ import annotations

import unittest

from services.business_findings_engine_v1 import run_business_findings_engine_v1
from services.commercial_interpretation_v1 import (
    clear_commercial_interpretation_last_valid_cache_v1,
)
from services.commercial_question_registry_v1 import (
    COMMERCIAL_QUESTIONS_V1,
    registry_stats_v1,
    resolve_question_for_finding_v1,
)
from services.home_commercial_intelligence_v1 import (
    apply_home_commercial_intelligence_v1,
    insight_has_commercial_evidence_model_v1,
    select_diverse_insights_v1,
)
from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1


class TestCommercialQuestionRegistryV1(unittest.TestCase):
    def test_registry_spans_commercial_dimensions(self) -> None:
        stats = registry_stats_v1()
        self.assertGreaterEqual(stats["question_count"], 15)
        dims = stats["dimensions"]
        for need in (
            "products",
            "hesitation",
            "traffic",
            "recovery",
            "whatsapp",
            "knowledge",
            "missing_evidence",
        ):
            self.assertIn(need, dims, need)
        self.assertIn("commercial questions", stats["success_metric"].lower())

    def test_finding_maps_to_question(self) -> None:
        q = resolve_question_for_finding_v1(
            {"finding_type": "high_interest_low_purchase_product_v1"}
        )
        self.assertEqual(q["question_id"], "CQ-P01")
        self.assertEqual(q["dimension"], "products")


class TestHomeCommercialIntelligenceV1(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()

    def test_demo_home_answers_diverse_commercial_questions(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر",
            date_ar="اليوم",
            brief_date="2026-07-18",
            daily_brief={"version": "v1", "achievements": [], "attention_items": []},
            kl_insights=[],
            nav_metadata={
                "active_carts": 77,
                "canonical_no_phone_total": 43,
                "knowledge_cart_count": 77,
            },
            store_slug="demo",
            findings_package=pkg,
            commercial_intel_demo=False,
            admit_review_fixtures=True,
        )
        meta = home.get("home_commercial_intelligence_v1") or {}
        self.assertTrue(meta.get("ok"))
        self.assertTrue(meta.get("diversity_ok"))
        self.assertGreaterEqual(int(meta.get("questions_answered_count") or 0), 2)
        dims = set(meta.get("dimensions_answered") or [])
        # Must not be contact-only
        self.assertTrue(dims - {"contact"}, dims)

        und = (home.get("store_understanding") or {}).get("items") or []
        self.assertTrue(und)
        lead = und[0]
        self.assertTrue(lead.get("commercial_question_id"))
        self.assertTrue(lead.get("commercial_question_ar"))
        self.assertNotEqual(lead.get("commercial_dimension"), "contact")
        self.assertTrue(
            insight_has_commercial_evidence_model_v1(
                {
                    "commercial_question_id": lead["commercial_question_id"],
                    "commercial_question_ar": lead["commercial_question_ar"],
                    "commercial_answer_ar": lead.get("commercial_answer_ar")
                    or lead.get("observation_ar"),
                    "evidence_ar": lead.get("evidence_ar")
                    or lead.get("evidence_label_ar"),
                    "confidence": lead.get("confidence"),
                    "merchant_meaning_ar": lead.get("merchant_meaning_ar")
                    or lead.get("business_meaning_ar"),
                    "insufficient_evidence_ok": True,
                }
            )
        )

    def test_diversity_prefers_non_contact_dimensions(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        insights = select_diverse_insights_v1(list(pkg.get("findings") or []))
        dims = [i["commercial_dimension"] for i in insights]
        self.assertIn("products", dims)
        # Contact may appear but must not be the only dimension
        self.assertGreaterEqual(len(set(dims)), 3)

    def test_operational_opportunity_replaced_by_commercial(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        home = {
            "store_understanding": {"items": []},
            "attention_today": {"items": []},
            "biggest_opportunity": {
                "item": {
                    "headline_ar": "30 سلة نشطة",
                    "fact_key": "fact:opportunity:recoverable_with_contact",
                },
                "items": [],
            },
            "learning_progress": {"items": []},
            "business_health": {"summary_ar": "يعمل", "evidence_summary_ar": "77 سلة نشطة"},
            "observability": {},
        }
        apply_home_commercial_intelligence_v1(
            home,
            store_slug="demo",
            findings_package=pkg,
            admit_review_fixtures=True,
        )
        opp = home["biggest_opportunity"].get("item") or {}
        self.assertTrue(opp.get("commercial_question_id"))
        self.assertNotIn("recoverable_with_contact", str(opp.get("fact_key") or ""))

    def test_registry_ids_stable(self) -> None:
        self.assertIn("CQ-P01", COMMERCIAL_QUESTIONS_V1)
        self.assertIn("CQ-D01", COMMERCIAL_QUESTIONS_V1)


if __name__ == "__main__":
    unittest.main()
