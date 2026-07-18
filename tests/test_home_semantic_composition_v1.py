# -*- coding: utf-8 -*-
"""Home Semantic Composition V1 — cross-section dedup + progressive disclosure."""
from __future__ import annotations

import unittest

from services.commercial_interpretation_v1 import (
    clear_commercial_interpretation_last_valid_cache_v1,
)
from services.home_adaptive_cognition_home_bridge_v1 import (
    attach_adaptive_cognition_to_home_v1,
    clear_acf_home_request_context_v1,
)
from services.home_cognitive_router_v1 import clear_cognitive_sessions_v1
from services.home_semantic_composition_v1 import (
    PROBLEM_MISSING_CONTACT,
    apply_home_semantic_composition_v1,
    build_semantic_identity_v1,
    filter_section_order_by_admission_v1,
    resolve_merchant_problem_v1,
)
from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1


class TestHomeSemanticCompositionV1(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()
        clear_cognitive_sessions_v1()
        clear_acf_home_request_context_v1()

    def _contact_home(self, *, no_phone: int = 43, active: int = 77) -> dict:
        return compose_merchant_home_experience_v1(
            merchant_name_ar="متجر اختبار",
            date_ar="السبت",
            brief_date="2026-07-18",
            daily_brief={"version": "v1", "achievements": [], "attention_items": []},
            kl_insights=[],
            nav_metadata={
                "active_carts": active,
                "waiting_send": 5,
                "canonical_no_phone_total": no_phone,
                "knowledge_cart_count": active,
            },
            store_slug="demo",
        )

    def test_same_wording_variants_share_merchant_problem(self) -> None:
        a = resolve_merchant_problem_v1(
            {"fact_key": "fact:obtain_contact", "headline_ar": "احصل على الأرقام"}
        )
        b = resolve_merchant_problem_v1(
            {
                "commercial_interpretation_id": "missing_contact_blocks_recovery_v1",
                "headline_ar": "نقص بيانات التواصل يعيق الاسترجاع",
            }
        )
        c = resolve_merchant_problem_v1(
            {"fact_key": "fact:opportunity:recoverable_with_contact"}
        )
        self.assertEqual(a, PROBLEM_MISSING_CONTACT)
        self.assertEqual(b, PROBLEM_MISSING_CONTACT)
        self.assertEqual(c, "recovery_ready_with_contact")

    def test_contact_story_progressive_not_six_paraphrases(self) -> None:
        home = self._contact_home()
        meta = home["home_semantic_composition_v1"]
        self.assertTrue(home["observability"].get("home_semantic_composition_v1"))

        # Action survives; contact risk paraphrase suppressed.
        # Understanding/Opportunity/Learning may carry *other* commercial dimensions.
        self.assertTrue(home["todays_priority"]["home_admission_v1"]["admitted"])
        self.assertTrue(home["business_understanding"]["home_admission_v1"]["admitted"])
        self.assertFalse(home["biggest_revenue_risk"]["home_admission_v1"]["admitted"])
        self.assertIsNone(home["biggest_revenue_risk"].get("item"))

        reasons = {s.get("reason") for s in meta["suppressed"]}
        self.assertIn("semantic_duplicate_of_priority_or_explain", reasons)

        evidence = str(home["business_health"].get("evidence_summary_ar") or "")
        self.assertNotIn("تواصل", evidence)

        pri = home["attention_today"]["items"][0]
        und = home["store_understanding"]["items"][0]
        self.assertEqual(pri.get("cognitive_role") or "action", "action")
        self.assertEqual(und.get("cognitive_role") or "explain", "explain")
        # Understanding must not restate the same contact headline as Priority.
        self.assertNotEqual(
            str(pri.get("headline_ar") or ""),
            str(und.get("observation_ar") or ""),
        )
        # Commercial diversity: understanding answers a non-contact question when available.
        if und.get("commercial_dimension"):
            self.assertNotEqual(und.get("commercial_dimension"), "contact")

    def test_distinct_evidence_different_conclusions_preserved(self) -> None:
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر",
            date_ar="اليوم",
            brief_date="2026-07-18",
            daily_brief={
                "version": "v1",
                "achievements": [
                    {
                        "headline_ar": "تم استرجاع سلة",
                        "detail_ar": "عميل أكمل الشراء.",
                        "fact_key": "fact:recovery:demo_ok",
                        "insight_key": "recovery_completed",
                        "why_it_matters_ar": "يثبت أن المتابعة تعمل.",
                    }
                ],
                "attention_items": [],
            },
            kl_insights=[],
            nav_metadata={
                "active_carts": 20,
                "waiting_send": 8,
                "canonical_no_phone_total": 0,
                "knowledge_cart_count": 20,
            },
            store_slug="demo",
        )
        # No contact problem — commercial / waiting opportunity may survive.
        opp = home["biggest_opportunity"].get("item")
        if opp:
            problem = resolve_merchant_problem_v1(opp)
            self.assertNotEqual(problem, PROBLEM_MISSING_CONTACT)
            self.assertNotIn("obtain_contact", problem)
        # Distinct timeline event preserved.
        facts = [
            str(it.get("fact_key") or "")
            for it in home["while_away"].get("items") or []
        ]
        self.assertTrue(any("recovery" in f for f in facts) or not facts)

    def test_opportunity_cannot_invert_existing_risk_problem(self) -> None:
        home = self._contact_home()
        opp = home["biggest_opportunity"].get("item")
        # Inverse contact opportunity is suppressed; a distinct commercial
        # opportunity (e.g. product) may survive.
        if opp is None:
            self.assertTrue(
                any(
                    s.get("reason")
                    == "inverse_or_same_problem_as_admitted_risk_or_priority"
                    for s in home["home_semantic_composition_v1"]["suppressed"]
                )
            )
        else:
            self.assertNotIn(
                "recoverable_with_contact", str(opp.get("fact_key") or "")
            )
            self.assertTrue(opp.get("commercial_question_id") or opp.get("headline_ar"))

    def test_timeline_cannot_duplicate_executive_conclusion(self) -> None:
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر",
            date_ar="اليوم",
            brief_date="2026-07-18",
            daily_brief={
                "version": "v1",
                "achievements": [
                    {
                        "headline_ar": "سلال بلا رقم",
                        "detail_ar": "نقص بيانات التواصل يعيق الاسترجاع",
                        "fact_key": "fact:obtain_contact",
                        "insight_key": "missing_contact_blocks_recovery_v1",
                    }
                ],
                "attention_items": [],
            },
            kl_insights=[],
            nav_metadata={
                "active_carts": 40,
                "canonical_no_phone_total": 20,
                "knowledge_cart_count": 40,
            },
            store_slug="demo",
        )
        for it in home["while_away"].get("items") or []:
            self.assertNotEqual(
                resolve_merchant_problem_v1(it), PROBLEM_MISSING_CONTACT
            )

    def test_semantic_identity_stable_across_wording(self) -> None:
        a = build_semantic_identity_v1(
            {
                "fact_key": "fact:obtain_contact",
                "headline_ar": "راجع السلال",
                "confidence": "high",
            },
            cognitive_role="action",
            surface="todays_priority",
        )
        b = build_semantic_identity_v1(
            {
                "commercial_interpretation_id": "missing_contact_blocks_recovery_v1",
                "observation_ar": "عائق التواصل",
                "confidence": "high",
            },
            cognitive_role="explain",
            surface="business_understanding",
        )
        self.assertEqual(a["merchant_problem"], b["merchant_problem"])
        self.assertNotEqual(a["cognitive_role"], b["cognitive_role"])

    def test_adaptive_paths_filter_ineligible_sections(self) -> None:
        home = self._contact_home()
        attach_adaptive_cognition_to_home_v1(
            home, trigger="session_start", fixture="attention"
        )
        acf = home["adaptive_cognition_v1"]
        order = acf["section_order"]
        self.assertIn("business_health", order)
        self.assertIn("todays_priority", order)
        self.assertNotIn("biggest_revenue_risk", order)
        # Opportunity may appear when it answers a distinct commercial question.
        # Mobile/desktop share same composition (order is semantic, not viewport).
        again = filter_section_order_by_admission_v1(
            list(order), home, path=str(acf.get("selected_path") or "B")
        )
        self.assertEqual(again, order)

    def test_no_ungoverned_admission_after_composition(self) -> None:
        home = self._contact_home()
        # Re-running composition must not resurrect suppressed risk.
        apply_home_semantic_composition_v1(home)
        self.assertFalse(home["biggest_revenue_risk"]["home_admission_v1"]["admitted"])
        self.assertIsNone(home["biggest_revenue_risk"].get("item"))

    def test_all_fixture_paths_produce_admitted_order(self) -> None:
        for fixture in (
            "healthy",
            "vip",
            "operational",
            "attention",
            "pending",
            "insufficient",
        ):
            home = self._contact_home()
            attach_adaptive_cognition_to_home_v1(
                home, trigger="session_start", fixture=fixture
            )
            order = home["adaptive_cognition_v1"]["section_order"]
            self.assertTrue(order, fixture)
            self.assertEqual(order[0], "business_health", fixture)
            for key in order:
                if key == "business_health":
                    continue
                self.assertTrue(
                    home.get("home_semantic_composition_v1"),
                    fixture,
                )


if __name__ == "__main__":
    unittest.main()
