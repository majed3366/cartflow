# -*- coding: utf-8 -*-
"""Gate 2E — Executive Business Composition."""
from __future__ import annotations

import unittest
from unittest.mock import patch


def _counters(*, no_phone=0, waiting=0, engaged=0, active=0):
    return {
        "available": True,
        "store_slug": "demo",
        "no_phone_total": no_phone,
        "waiting_total": waiting,
        "engaged_total": engaged,
        "active_total": active,
    }


class BusinessImpactPriorityTests(unittest.TestCase):
    def test_product_outranks_recovery_by_domain_order(self) -> None:
        from services.decision_composition_engine_v1.portfolio_v1 import (
            build_portfolio_v1,
        )
        from services.decision_composition_engine_v1.business_impact_v1 import (
            attach_business_impact_v1,
        )
        from services.decision_composition_engine_v1.priority_v1 import (
            calculate_priority_v1,
        )

        product = attach_business_impact_v1(
            {
                "decision_id": "p1",
                "decision_type": "verified_existing_finding",
                "finding_type": "high_interest_low_purchase_product_v1",
                "business_domain": "products",
                "merchant_decision": "راجع أداء المنتج عطر الورد.",
                "confidence": "medium",
                "first_step": "افتح صفحة المنتج",
                "why_now": "الآن",
                "affected_count": 2,
            }
        )
        score, band, _ = calculate_priority_v1(product, affected_count=2)
        product["priority"] = score
        product["priority_band"] = band

        recovery = attach_business_impact_v1(
            {
                "decision_id": "r1",
                "decision_type": "recoverability_gap",
                "business_domain": "recovery",
                "merchant_decision": "راجع مسار الاسترجاع.",
                "confidence": "high",
                "first_step": "افتح الحالات",
                "why_now": "الآن",
                "affected_count": 80,
            }
        )
        score, band, _ = calculate_priority_v1(recovery, affected_count=80)
        recovery["priority"] = score
        recovery["priority_band"] = band

        pkg = build_portfolio_v1([recovery, product], max_visible=6)
        # Products domain ranks above Recovery even with smaller counter.
        self.assertEqual(pkg["portfolio"][0]["decision_id"], "p1")
        self.assertEqual(pkg["portfolio"][0]["business_domain"], "products")

    def test_scale_does_not_dominate_automation_wait(self) -> None:
        from services.decision_composition_engine_v1.priority_v1 import (
            calculate_priority_v1,
        )

        low = calculate_priority_v1(
            {
                "decision_type": "waiting_recovery_work",
                "business_domain": "operations",
                "confidence": "low",
                "first_step": "x",
                "why_now": "",
            },
            affected_count=100,
            automation_can_resolve=True,
        )
        high = calculate_priority_v1(
            {
                "decision_type": "recoverability_gap",
                "business_domain": "recovery",
                "confidence": "high",
                "first_step": "x",
                "why_now": "الآن",
            },
            affected_count=3,
            automation_can_resolve=False,
        )
        self.assertGreater(high[0], low[0])
        self.assertLessEqual(low[2]["scale"], 15)


class ExecutiveLanguageTests(unittest.TestCase):
    def test_decision_title_not_counter_report(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1

        pkg = compose_decisions_v1(
            "demo",
            counters=_counters(no_phone=43, waiting=43),
            findings=[],
            use_cache=False,
        )
        self.assertTrue(pkg.get("gate_2e_executive_business"))
        top = pkg["portfolio"][0]
        # Gate 2F rewrites recovery into morning-briefing attention language.
        self.assertIn("إتمام الشراء", top["merchant_decision"])
        self.assertNotIn("43", top["merchant_decision"])
        self.assertIn("business_meaning_ar", top)
        self.assertIn("business_impact_ar", top)

    def test_home_ceo_questions_in_thirty_seconds(self) -> None:
        from services.home_executive_summary_v1.compose_v1 import (
            build_home_executive_summary_v1,
        )

        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {
                        "domain_summary_ar": "أداء الاسترجاع انخفض اليوم.",
                        "needs_attention": True,
                        "abandoned_carts": 3,
                        "no_phone": 3,
                        "active_carts": 5,
                    },
                    "decisions": {
                        "count": 1,
                        "top_title_ar": "راجع تجربة إتمام الشراء ومتابعة العملاء.",
                        "evidence": "store_executive_understanding",
                    },
                    "observations": {"count": 0},
                    "carts": {
                        "waiting": 3,
                        "no_phone": 3,
                        "domain_summary_ar": "3 سلة قيد المتابعة مع العملاء.",
                    },
                    "communication": {
                        "sent": 12,
                        "waiting": 3,
                        "no_phone": 8,
                        "domain_summary_ar": "تواصل العملاء يحتاج انتباهاً — المتابعة مقيدة لبعض الحالات.",
                    },
                }
            }
        )
        by_id = {s["id"]: s for s in hes["sections"]}
        # 1) Store healthy? → clear business condition
        self.assertTrue(
            "فرص" in by_id["health"]["summary_ar"]
            or "الاسترجاع" in by_id["health"]["summary_ar"]
        )
        self.assertNotEqual(
            by_id["health"]["summary_ar"], by_id["decisions"]["summary_ar"]
        )
        # 2) Highest-priority business decision
        self.assertIn("إتمام الشراء", by_id["decisions"]["summary_ar"])
        self.assertNotIn("43", by_id["decisions"]["summary_ar"])
        # 3) Product observation honesty
        self.assertIn("أدلة كافية", by_id["observations"]["summary_ar"])
        # 4) Recovery / carts operating?
        self.assertIn("متابعة", by_id["carts"]["summary_ar"])
        # 5) Communication operating?
        self.assertTrue(
            "تواصل" in by_id["communication"]["summary_ar"]
            or "متابعة" in by_id["communication"]["summary_ar"]
            or "رسالة" in by_id["communication"]["summary_ar"]
        )
        self.assertTrue(hes["governance"].get("executive_business_language"))


if __name__ == "__main__":
    unittest.main()
