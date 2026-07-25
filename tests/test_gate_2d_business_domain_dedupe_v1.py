# -*- coding: utf-8 -*-
"""Gate 2D — Business Domain Composition & Decision Deduplication."""
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


class BusinessDomainNormalizationTests(unittest.TestCase):
    def test_domains_normalize_ot_before_decisions(self) -> None:
        from services.decision_composition_engine_v1.business_domains_v1 import (
            ROOT_MISSING_CONTACT,
            normalize_business_domains_v1,
        )

        pkg = normalize_business_domains_v1(
            _counters(no_phone=3, waiting=3),
            [],
            store_slug="demo",
        )
        self.assertTrue(pkg["gate_2d_business_domains"])
        recovery = pkg["domains"]["recovery"]
        self.assertTrue(recovery["has_attention"])
        self.assertIn(ROOT_MISSING_CONTACT, recovery["root_causes"])
        # Waiting collapsed into missing contact — no separate ops fork.
        self.assertTrue(pkg["signals"]["waiting_collapsed_into_missing_contact"])
        self.assertFalse(pkg["domains"]["operations"]["has_attention"])
        # Store health does not restate no-phone decision language.
        health_ar = pkg["home_teasers"]["store_health_ar"]
        # Gate 2F — business condition via domains; Home later uses Store Executive.
        self.assertTrue("الاسترجاع" in health_ar or "فرص" in health_ar or "انخفض" in health_ar)
        self.assertNotIn("بلا رقم تواصل", health_ar)
        self.assertNotEqual(health_ar, "راجع تجربة إتمام الشراء ومتابعة العملاء.")

    def test_shipping_and_pricing_domain_mapping(self) -> None:
        from services.decision_composition_engine_v1.business_domains_v1 import (
            map_finding_to_domain_v1,
        )

        self.assertEqual(
            map_finding_to_domain_v1({"finding_type": "shipping_cost_hesitation_v1"}),
            "shipping",
        )
        self.assertEqual(
            map_finding_to_domain_v1({"finding_type": "pricing_too_high_v1"}),
            "pricing",
        )


class DecisionDeduplicationTests(unittest.TestCase):
    def test_one_root_cause_one_decision(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1

        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[
                {
                    "finding_id": "f-missing",
                    "finding_type": "missing_contact_block_v1",
                    "title": "بلا رقم",
                    "merchant_decision_v1": {
                        "has_decision": True,
                        "status": "DECISION",
                        "decision": "اجمع الأرقام",
                        "why": "سبب",
                        "evidence_summary": "دليل",
                        "required_merchant_action": "فعل",
                        "expected_business_impact": "أثر",
                        "decision_confidence": "high",
                    },
                }
            ],
        ):
            pkg = compose_decisions_v1(
                "demo",
                counters=_counters(no_phone=2, waiting=2),
                use_cache=False,
            )
        self.assertTrue(pkg["gate_2d_decision_dedupe"])
        portfolio = pkg["portfolio"]
        # Recoverability OT wins; finding + waiting collapsed.
        recovery = [d for d in portfolio if d.get("decision_category") == "recovery"]
        self.assertEqual(len(recovery), 1)
        self.assertEqual(recovery[0]["decision_type"], "recoverability_gap")
        reasons = {r.get("suppression_reason") for r in pkg["suppression_registry"]}
        self.assertTrue(
            reasons
            & {
                "covered_by_recoverability_gap_composer",
                "subsumed_by_canonical_decision",
                "duplicate_root_cause",
            }
        )

    def test_distinct_root_causes_can_coexist(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1

        finding = {
            "finding_id": "f-prod",
            "finding_type": "high_interest_low_purchase_product_v1",
            "title": "منتج",
            "product_id": "p1",
            "entity": {"product_id": "p1", "product_name_ar": "عطر الورد"},
            "merchant_decision_v1": {
                "has_decision": True,
                "status": "DECISION",
                "decision": "راجع عرض عطر الورد.",
                "why": "اهتمام مرتفع بدون شراء",
                "evidence_summary": "أدلة المنتج",
                "required_merchant_action": "راجع الصفحة",
                "expected_business_impact": "رفع التحويل",
                "decision_confidence": "medium",
            },
        }
        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[finding],
        ):
            pkg = compose_decisions_v1(
                "demo",
                counters=_counters(no_phone=2, waiting=2),
                findings=[finding],
                use_cache=False,
            )
        cats = {d.get("decision_category") for d in pkg["portfolio"]}
        self.assertIn("recovery", cats)
        self.assertIn("products", cats)

    def test_home_teaser_has_no_why_or_evidence(self) -> None:
        from services.decision_composition_engine_v1.teaser_v1 import (
            count_composed_decisions_for_teaser_v1,
        )
        from services.home_executive_summary_v1.compose_v1 import (
            build_home_executive_summary_v1,
        )

        with patch(
            "services.decision_composition_engine_v1.compose_v1.load_bound_finding_inputs_v1",
            return_value=[],
        ):
            teaser = count_composed_decisions_for_teaser_v1(
                "demo",
                summary={
                    "store_slug": "demo",
                    "merchant_store_cart_counts": {
                        "active_total": 1,
                        "waiting_total": 2,
                        "no_phone_total": 2,
                    },
                },
            )
        self.assertTrue(teaser.get("gate_2d"))
        self.assertNotIn("why", teaser)
        self.assertNotIn("why_now", teaser)
        self.assertNotIn("evidence_summary", teaser)
        self.assertTrue(teaser.get("top_title_ar"))

        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {
                        "domain_summary_ar": "المتجر يحتاج انتباهاً — التفاصيل في قرارات اليوم.",
                        "needs_attention": True,
                        "abandoned_carts": 2,
                        "no_phone": 2,
                        "active_carts": 1,
                    },
                    "decisions": {
                        "count": 1,
                        "top_title_ar": teaser["top_title_ar"],
                        "evidence": "decision_composition_engine",
                    },
                    "observations": {"count": 0},
                    "carts": {
                        "waiting": 2,
                        "no_phone": 2,
                        "domain_summary_ar": "توجد سلال بانتظار المتابعة، وحالات بلا رقم.",
                    },
                    "communication": {
                        "sent": 0,
                        "schedules": 0,
                        "waiting": 2,
                        "no_phone": 2,
                        "domain_summary_ar": "متابعة معلّقة، وتوجد حالات بلا رقم.",
                    },
                }
            }
        )
        sections = {s["id"]: s for s in hes["sections"]}
        # Health must not duplicate the decision title/explanation.
        self.assertNotEqual(
            sections["health"]["summary_ar"], sections["decisions"]["summary_ar"]
        )
        self.assertNotIn("لماذا", sections["decisions"]["summary_ar"])
        self.assertEqual(sections["decisions"]["view_details_href"], "#workspace")
        self.assertEqual(hes["governance"]["home_creates_decisions"], False)

    def test_workspace_cards_carry_domain_and_constitution(self) -> None:
        from services.decision_composition_engine_v1.compose_v1 import compose_decisions_v1
        from services.decision_composition_engine_v1.project_workspace_v1 import (
            decisions_to_workspace_cards_v1,
        )

        pkg = compose_decisions_v1(
            "demo",
            counters=_counters(no_phone=4, waiting=4),
            findings=[],
            use_cache=False,
        )
        cards = decisions_to_workspace_cards_v1(pkg["portfolio"])
        self.assertEqual(len(cards), 1)
        card = cards[0]
        for key in (
            "decision_ar",
            "why_ar",
            "why_now_ar",
            "evidence_summary",
            "ignore_consequence_ar",
            "required_merchant_action",
            "first_step_ar",
            "expected_outcome_ar",
            "decision_confidence_ar",
            "business_domain",
            "root_cause_key",
        ):
            self.assertTrue(card.get(key), msg=key)
        evidence = card.get("evidence_summary") or ""
        self.assertNotIn("عدّاد الانتظار", evidence)
        self.assertNotIn("db_", evidence.lower())
        self.assertEqual(len(pkg["category_landscape"]), 9)


if __name__ == "__main__":
    unittest.main()
