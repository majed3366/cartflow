# -*- coding: utf-8 -*-
"""
Home Knowledge Redistribution V1 — compatibility with Daily Business Brief V1.

Section roles evolved under Constitution V3; explain-vs-decide separation remains.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from services.commercial_interpretation_v1 import (
    clear_commercial_interpretation_last_valid_cache_v1,
)
from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1

_REPO = Path(__file__).resolve().parents[1]


class TestHomeKnowledgeRedistributionV1(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()

    def _home_with_cil(self, *, count: int = 50) -> dict:
        return compose_merchant_home_experience_v1(
            merchant_name_ar="متجر اختبار",
            date_ar="الجمعة",
            brief_date="2026-07-17",
            daily_brief={"version": "v1", "achievements": [], "attention_items": []},
            kl_insights=[],
            nav_metadata={
                "active_carts": 60,
                "waiting_send": 10,
                "canonical_no_phone_total": count,
                "knowledge_cart_count": 60,
            },
            store_slug="demo",
        )

    def test_section_roles_are_distinct(self) -> None:
        home = self._home_with_cil()
        self.assertEqual(home["while_away"].get("knowledge_role"), "business_timeline")
        self.assertEqual(home["store_understanding"].get("knowledge_role"), "explain")
        self.assertEqual(home["attention_today"].get("knowledge_role"), "priority")
        self.assertTrue(home["observability"].get("home_knowledge_redistribution_v1"))
        self.assertTrue(home["observability"].get("home_daily_business_brief_v1"))

    def test_knowledge_explains_without_action(self) -> None:
        home = self._home_with_cil()
        lead = home["store_understanding"]["items"][0]
        self.assertTrue(lead.get("observation_ar"))
        self.assertTrue(lead.get("evidence_label_ar"))
        self.assertTrue(lead.get("impact_ar") or lead.get("business_meaning_ar"))
        self.assertTrue(lead.get("confidence"))
        self.assertFalse(str(lead.get("action_ar") or "").strip())
        self.assertFalse(str(lead.get("cta_label_ar") or "").strip())
        self.assertFalse(str(lead.get("drilldown_href") or "").strip())

    def test_attention_owns_decision_with_different_wording(self) -> None:
        home = self._home_with_cil()
        knowledge = home["store_understanding"]["items"][0]
        attention = home["attention_today"]["items"][0]
        self.assertEqual(
            attention.get("operational_decision_key"),
            "decision:obtain_contact",
        )
        self.assertTrue(attention.get("action_ar"))
        self.assertTrue(attention.get("why_ar"))
        self.assertTrue(attention.get("if_ignored_ar"))
        self.assertTrue(attention.get("expected_outcome_ar"))
        self.assertNotEqual(
            str(knowledge.get("observation_ar") or "").strip(),
            str(attention.get("headline_ar") or "").strip(),
        )
        # Same commercial fact must not reuse identical conclusion as decision headline.
        self.assertNotIn(
            "أكبر عائق أمام الاسترجاع",
            str(attention.get("headline_ar") or ""),
        )

    def test_today_section_evolved_to_health_not_attention_language(self) -> None:
        home = self._home_with_cil()
        health = home["business_health"]
        blob = " ".join(
            [
                str(health.get("title_ar") or ""),
                str(health.get("lead_ar") or ""),
                str(health.get("summary_ar") or ""),
            ]
        )
        self.assertIn("عمل", blob)
        self.assertNotIn("طابور", blob)

    def test_no_engineering_queue_copy_in_composition(self) -> None:
        home = self._home_with_cil()
        att = home["attention_today"]
        self.assertNotIn("طابور", str(att.get("lead_ar") or ""))
        self.assertIn("أهم", str(att.get("lead_ar") or ""))

    def test_js_story_order_and_language(self) -> None:
        js = (_REPO / "static" / "merchant_dashboard_home_v1.js").read_text(
            encoding="utf-8", errors="replace"
        )
        self.assertIn("resolveSectionOrder", js)
        self.assertIn("sectionAdmitted", js)
        self.assertIn("renderSectionByKey", js)
        self.assertNotIn("طابور قرارات", js)
        self.assertNotIn("حالة المعرفة", js)
        self.assertNotIn("renderPerformance", js)
        self.assertIn("المعنى التجاري", js)
        kn = js[
            js.find("function renderBusinessUnderstanding") : js.find(
                "function renderLearningProgress"
            )
        ]
        self.assertNotIn("عرض السلال المتأثرة", kn)
        self.assertNotIn("ma-ecc-today-list", js)
        self.assertNotIn("CartFlow يتابع", js)


if __name__ == "__main__":
    unittest.main()
