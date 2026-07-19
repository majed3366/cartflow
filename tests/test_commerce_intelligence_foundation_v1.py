# -*- coding: utf-8 -*-
"""Commerce Intelligence Foundation V1 — contract, domains, projection, package."""
from __future__ import annotations

import unittest

from services.commerce_intelligence.contract_v1 import (
    REQUIRED_FIELDS,
    record_is_complete_v1,
)
from services.commerce_intelligence.domains_v1 import (
    DOMAIN_CUSTOMER,
    DOMAIN_GUIDANCE,
    DOMAIN_PRODUCT,
    DOMAIN_STORE,
    all_domains_v1,
    domain_for_dimension_v1,
    is_guidance_eligible_v1,
)
from services.commerce_intelligence.engine_v1 import (
    build_commerce_intelligence_package_v1,
    run_commerce_intelligence_foundation_v1,
)
from services.commerce_intelligence.project_from_finding_v1 import (
    project_finding_to_intelligence_record_v1,
    project_guidance_from_finding_v1,
)
from services.commercial_question_registry_v1 import DIM_HESITATION, DIM_PRODUCTS


def _sample_finding(**overrides):
    base = {
        "finding_id": "finding:demo:product:1",
        "store_slug": "demo",
        "finding_type": "high_interest_low_purchase_product_v1",
        "title": "منتج يجذب ولا يحوّل",
        "merchant_summary": "منتج يظهر اهتماماً عالياً مع شراء ضعيف.",
        "commercial_meaning": "صفحة المنتج أو مسار الشراء يحتاج مراجعة.",
        "evidence_summary": "عينة كافية من العربات في النافذة.",
        "evidence_refs": ["cart:c1", "cart:c2"],
        "sample_size": 40,
        "confidence_level": "high",
        "confidence_score": 0.9,
        "recommended_direction": "راجع صفحة المنتج قبل أي خصم.",
        "recommendation_type": "investigate",
        "status": "confirmed",
        "family_key": "product_interest",
    }
    base.update(overrides)
    return base


class TestCommerceIntelligenceFoundationV1(unittest.TestCase):
    def test_required_canonical_fields(self) -> None:
        self.assertEqual(
            set(REQUIRED_FIELDS),
            {
                "question",
                "finding",
                "evidence",
                "confidence",
                "recommendation",
                "status",
                "source_domains",
            },
        )
        self.assertEqual(
            set(all_domains_v1()),
            {DOMAIN_PRODUCT, DOMAIN_CUSTOMER, DOMAIN_STORE, DOMAIN_GUIDANCE},
        )

    def test_domain_overlay_on_cq_dimensions(self) -> None:
        self.assertEqual(domain_for_dimension_v1(DIM_PRODUCTS), DOMAIN_PRODUCT)
        self.assertEqual(domain_for_dimension_v1(DIM_HESITATION), DOMAIN_CUSTOMER)
        self.assertEqual(domain_for_dimension_v1("traffic"), DOMAIN_STORE)
        self.assertEqual(domain_for_dimension_v1("merchant_guidance"), DOMAIN_GUIDANCE)

    def test_project_finding_to_canonical_record(self) -> None:
        rec = project_finding_to_intelligence_record_v1(_sample_finding())
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertTrue(record_is_complete_v1(rec))
        for key in REQUIRED_FIELDS:
            self.assertIn(key, rec)
        self.assertEqual(rec["question"]["id"], "CQ-P01")
        self.assertTrue(rec["question"]["text_ar"])
        self.assertIn(DOMAIN_PRODUCT, rec["source_domains"])
        self.assertEqual(rec["finding"]["text_ar"], "منتج يظهر اهتماماً عالياً مع شراء ضعيف.")
        self.assertEqual(rec["evidence"]["sample_size"], 40)
        self.assertEqual(rec["confidence"]["level"], "high")
        self.assertTrue(rec["recommendation"]["text_ar"])
        self.assertIn(rec["status"], ("ready", "actionable", "monitor", "still_learning"))

    def test_guidance_gate_blocks_action_on_insufficient_evidence(self) -> None:
        f = _sample_finding(
            finding_id="finding:demo:insuff:1",
            finding_type="insufficient_or_conflicting_evidence_v1",
            status="insufficient_evidence",
            confidence_level="insufficient",
            sample_size=2,
            recommendation_type="act_now",
            recommended_direction="قدّم خصماً الآن",
        )
        # Insufficient status is still allowed to emit honest “collect evidence” guidance
        self.assertTrue(
            is_guidance_eligible_v1(
                confidence="insufficient",
                status="insufficient_evidence",
                recommendation_type="act_now",
            )
        )
        g = project_guidance_from_finding_v1(f)
        self.assertIsNotNone(g)
        assert g is not None
        self.assertEqual(g["domain"], DOMAIN_GUIDANCE)
        self.assertIn(DOMAIN_GUIDANCE, g["source_domains"])
        self.assertFalse(g["recommendation"]["eligible"])
        self.assertEqual(g["recommendation"]["type"], "insufficient_evidence")
        self.assertIn("أدلة", g["recommendation"]["text_ar"])

    def test_guidance_eligible_action_when_evidenced(self) -> None:
        f = _sample_finding(
            recommendation_type="act_now",
            recommended_direction="حسّن صفحة المنتج",
            confidence_level="high",
            status="confirmed",
        )
        self.assertTrue(
            is_guidance_eligible_v1(
                confidence="high",
                status="confirmed",
                recommendation_type="act_now",
            )
        )
        g = project_guidance_from_finding_v1(f)
        self.assertIsNotNone(g)
        assert g is not None
        self.assertTrue(g["recommendation"]["eligible"])
        self.assertEqual(g["recommendation"]["type"], "act_now")

    def test_package_by_domain_and_home_contract(self) -> None:
        findings_pkg = {
            "engine_version": "business_findings_engine_v1",
            "findings": [
                _sample_finding(),
                _sample_finding(
                    finding_id="finding:demo:hes:1",
                    finding_type="dominant_hesitation_reason_v1",
                    merchant_summary="الشحن هو سبب التردد الأبرز.",
                    title="تردّد بسبب الشحن",
                    status="emerging",
                    confidence_level="medium",
                    recommendation_type="monitor",
                    recommended_direction="راقب تكلفة الشحن — لا توصِ بخصم بعد.",
                    family_key="hesitation",
                ),
            ],
        }
        pkg = build_commerce_intelligence_package_v1(
            store_slug="demo",
            findings_package=findings_pkg,
        )
        self.assertTrue(pkg["ok"])
        self.assertEqual(pkg["foundation_version"], "commerce_intelligence_foundation_v1")
        self.assertGreaterEqual(pkg["counts"]["records"], 2)
        self.assertTrue(pkg["by_domain"][DOMAIN_PRODUCT])
        self.assertTrue(pkg["by_domain"][DOMAIN_CUSTOMER])
        self.assertTrue(pkg["by_domain"][DOMAIN_GUIDANCE])
        hc = pkg["home_consumption_contract"]
        self.assertIn("never calculates", hc["rule"])
        self.assertEqual(set(hc["required_fields"]), set(REQUIRED_FIELDS))
        for rec in pkg["records"]:
            self.assertTrue(record_is_complete_v1(rec))

    def test_run_demo_fixture_end_to_end(self) -> None:
        pkg = run_commerce_intelligence_foundation_v1(
            store_slug="demo",
            load_db=False,
            demo_fixture=True,
        )
        self.assertTrue(pkg["ok"])
        self.assertGreaterEqual(pkg["counts"]["records"], 1)
        self.assertFalse(pkg["ai_used"])
        # At least one of the four domains should be populated from demo findings
        populated = sum(1 for d in all_domains_v1() if pkg["by_domain"].get(d))
        self.assertGreaterEqual(populated, 2)

    def test_home_must_not_be_invoked(self) -> None:
        """Foundation package must not require Home composition modules."""
        import services.commerce_intelligence.engine_v1 as eng

        src = open(eng.__file__, encoding="utf-8").read()
        self.assertNotIn("merchant_home_composition", src)
        self.assertNotIn("home_commercial_intelligence", src)


if __name__ == "__main__":
    unittest.main()
