# -*- coding: utf-8 -*-
"""Home Daily Business Brief V1 — Constitution V3 section ownership."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.commercial_interpretation_v1 import (
    clear_commercial_interpretation_last_valid_cache_v1,
)
from services.merchant_home_composition_v1 import (
    HOME_MAX_ATTENTION_DISPLAY,
    compose_merchant_home_experience_v1,
)

_REPO = Path(__file__).resolve().parents[1]


class TestHomeDailyBusinessBriefV1(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()

    def _home(self, *, no_phone: int = 50, active: int = 80, waiting: int = 12) -> dict:
        return compose_merchant_home_experience_v1(
            merchant_name_ar="متجر اختبار",
            date_ar="الجمعة",
            brief_date="2026-07-17",
            daily_brief={"version": "v1", "achievements": [], "attention_items": []},
            kl_insights=[],
            nav_metadata={
                "active_carts": active,
                "waiting_send": waiting,
                "canonical_no_phone_total": no_phone,
                "knowledge_cart_count": active,
            },
            store_slug="demo",
        )

    def test_brief_flag_and_seven_section_roles(self) -> None:
        home = self._home()
        self.assertTrue(home.get("daily_business_brief_v1"))
        self.assertTrue(home["observability"].get("home_daily_business_brief_v1"))
        self.assertEqual(home["business_health"].get("knowledge_role"), "business_health")
        self.assertEqual(
            home["biggest_revenue_risk"].get("knowledge_role"), "revenue_risk"
        )
        self.assertEqual(
            home["biggest_opportunity"].get("knowledge_role"), "opportunity"
        )
        self.assertEqual(home["attention_today"].get("knowledge_role"), "priority")
        self.assertEqual(home["store_understanding"].get("knowledge_role"), "explain")
        self.assertEqual(
            home["learning_progress"].get("knowledge_role"), "learning_progress"
        )
        self.assertEqual(home["while_away"].get("knowledge_role"), "business_timeline")

    def test_business_health_starts_with_status_not_events(self) -> None:
        home = self._home()
        health = home["business_health"]
        self.assertTrue(health.get("status_ar"))
        self.assertTrue(health.get("summary_ar"))
        self.assertTrue(health.get("direction_ar"))
        self.assertTrue(health.get("confidence"))
        self.assertTrue(health.get("attention_required"))
        self.assertNotIn("items", health)

    def test_e1_business_health_executive_contract(self) -> None:
        """Executive Home Sprint 1 — E1 answers EQ-01; proof in disclosure only."""
        home = self._home()
        health = home["business_health"]
        self.assertEqual(health.get("executive_band"), "E1")
        self.assertEqual(health.get("executive_question_id"), "EQ-01")
        self.assertEqual(
            health.get("section_question_ar"), "هل عملي بصحة جيدة اليوم؟"
        )
        self.assertEqual(health.get("evidence_summary_ar") or "", "")
        disc = health.get("disclosure") or {}
        self.assertTrue(disc.get("label_ar"))
        self.assertTrue(disc.get("trend_ar") or disc.get("evidence_ar"))
        blob = (
            f"{health.get('status_ar')} {health.get('summary_ar')} "
            f"{health.get('confidence_ar')} {disc.get('evidence_ar')} "
            f"{disc.get('trend_ar')}"
        )
        self.assertNotIn("hesitation_total", blob)
        self.assertNotIn("returns=", blob)
        self.assertNotRegex(blob, r"\d+\s*سلة")
        self.assertNotIn("hesitation_", blob)
        self.assertNotIn("loaded_from", blob)

    def test_revenue_risk_suppressed_when_same_problem_as_priority(self) -> None:
        """Semantic composition: risk must not paraphrase Priority's contact problem."""
        home = self._home()
        risk = home["biggest_revenue_risk"]
        self.assertFalse(risk.get("home_admission_v1", {}).get("admitted"))
        self.assertIsNone(risk.get("item"))
        self.assertEqual(risk.get("items") or [], [])

    def test_opportunity_not_inverse_contact_restatement(self) -> None:
        home = self._home(no_phone=50, active=80)
        opp = home["biggest_opportunity"].get("item")
        if opp:
            self.assertNotIn(
                "recoverable_with_contact", str(opp.get("fact_key") or "")
            )
        else:
            self.assertFalse(
                home["biggest_opportunity"].get("home_admission_v1", {}).get("admitted")
            )

    def test_priority_is_exactly_one(self) -> None:
        home = self._home()
        items = home["attention_today"]["items"]
        self.assertEqual(len(items), 1)
        self.assertLessEqual(len(items), HOME_MAX_ATTENTION_DISPLAY)
        self.assertEqual(home["attention_today"].get("title_ar"), "أولوية اليوم")
        self.assertEqual(
            items[0].get("operational_decision_key"), "decision:obtain_contact"
        )

    def test_understanding_explains_business_not_action(self) -> None:
        home = self._home()
        lead = home["store_understanding"]["items"][0]
        self.assertEqual(home["store_understanding"].get("title_ar"), "فهم العمل")
        self.assertTrue(lead.get("observation_ar"))
        self.assertTrue(lead.get("business_meaning_ar"))
        self.assertTrue(lead.get("commercial_impact_ar"))
        self.assertTrue(lead.get("recommended_direction_ar"))
        self.assertFalse(str(lead.get("action_ar") or "").strip())
        self.assertFalse(str(lead.get("cta_label_ar") or "").strip())

    def test_progressive_priority_and_understanding_not_paraphrase_twins(self) -> None:
        home = self._home()
        pri_h = str(
            (home["attention_today"]["items"][0] or {}).get("headline_ar") or ""
        ).strip()
        und_h = str(
            (home["store_understanding"]["items"][0] or {}).get("observation_ar") or ""
        ).strip()
        self.assertTrue(pri_h and und_h)
        self.assertNotEqual(pri_h, und_h)
        self.assertEqual(
            home["attention_today"]["items"][0].get("cognitive_role"), "action"
        )
        self.assertEqual(
            home["store_understanding"]["items"][0].get("cognitive_role"), "explain"
        )

    def test_learning_progress_not_contact_paraphrase(self) -> None:
        home = self._home()
        learning = home["learning_progress"]
        items = learning.get("items") or []
        for it in items:
            self.assertNotEqual(
                str(it.get("fact_key") or ""),
                "fact:learning:contact_blocker_pattern",
            )

    def test_timeline_has_why_it_matters_when_events_exist(self) -> None:
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر",
            date_ar="اليوم",
            brief_date="2026-07-17",
            daily_brief={
                "version": "v1",
                "achievements": [
                    {
                        "headline_ar": "تم استرجاع سلة",
                        "detail_ar": "عميل أكمل الشراء بعد المتابعة.",
                        "fact_key": "fact:recovery:demo1",
                        "insight_key": "recovery_completed",
                        "aggregation_key": "agg:recovery:demo1",
                    }
                ],
                "attention_items": [],
            },
            kl_insights=[],
            nav_metadata={"active_carts": 10, "waiting_send": 2},
            store_slug="demo",
        )
        items = home["while_away"]["items"]
        if items:
            self.assertTrue(items[0].get("why_it_matters_ar") or items[0].get("detail_ar"))

    def test_js_story_order_and_advisor_language(self) -> None:
        js = (_REPO / "static" / "merchant_dashboard_home_v1.js").read_text(
            encoding="utf-8", errors="replace"
        )
        self.assertIn("resolveSectionOrder", js)
        self.assertIn("sectionAdmitted", js)
        self.assertIn("renderSectionByKey", js)
        self.assertIn("daily-brief-v1", js)
        self.assertNotIn("طابور قرارات", js)
        self.assertNotIn("طبقة المعرفة", js)
        self.assertNotIn("renderMetrics", js)
        self.assertNotIn("مؤشرات سريعة", js)
        kn = js[
            js.find("function renderBusinessUnderstanding") : js.find(
                "function renderLearningProgress"
            )
        ]
        self.assertNotIn("عرض السلال المتأثرة", kn)
        self.assertIn("المعنى التجاري", kn)
        self.assertIn("الاتجاه الموصى به", kn)


if __name__ == "__main__":
    unittest.main()
