# -*- coding: utf-8 -*-
"""Business Facts Extraction V1."""
from __future__ import annotations

import unittest

from services.business_facts_v1.contract_v1 import (
    FACT_TYPE_CONVERSION,
    validate_business_fact_v1,
)
from services.business_facts_v1.extract_v1 import extract_business_facts_v1
from services.business_facts_v1.route_v1 import (
    route_business_facts_v1,
    workspace_cards_from_business_facts_v1,
)


def _orv_finding(
    *,
    cap: str,
    product: str,
    key: str,
    statement: str,
) -> dict:
    return {
        "finding_id": f"observation_reality:{cap}",
        "observation_id": f"obs:{cap}",
        "capability_id": cap,
        "product_name_ar": product,
        "statement_ar": statement,
        "home_teaser_ar": f"{product}: {statement}",
        "confidence_level": "high",
        "confidence_ar": "مرتفع",
        "confidence_score": 80,
        "confidence_source": "test",
        "evidence_details": {
            "product_key": key,
            "correlation_kind": "product_interest_conversion_v1",
            "evidence_refs": [{"evidence_ref_id": "e1"}],
            "evidence_ref_count": 1,
        },
    }


class ContractTests(unittest.TestCase):
    def test_fact_requires_meaning_and_evidence(self) -> None:
        bad = {
            "fact_id": "x",
            "fact_type": FACT_TYPE_CONVERSION,
            "subject": {"kind": "product", "id": "a", "name_ar": "A"},
            "business_meaning_ar": "",
            "evidence": {},
            "confidence": {},
            "freshness": {},
            "impact_category": "conversion",
        }
        errs = validate_business_fact_v1(bad)
        self.assertTrue(errs)


class ExtractionTests(unittest.TestCase):
    def test_extracts_from_validated_orv_not_counters(self) -> None:
        orv = {
            "ok": True,
            "findings": [
                _orv_finding(
                    cap="high_interest_low_conversion",
                    product="Raven — حزام جلد للساعة",
                    key="b|raven|band",
                    statement="اهتمام مرتفع",
                ),
                _orv_finding(
                    cap="shipping_stronger_than_price",
                    product="TrueSound — سماعة لاسلكية",
                    key="b|ts|air",
                    statement="شحن أقوى",
                ),
                _orv_finding(
                    cap="repeated_return_without_purchase",
                    product="Raven — حزام جلد للساعة",
                    key="b|raven|band",
                    statement="عودة",
                ),
            ],
        }
        pkg = extract_business_facts_v1(
            store_slug="demo",
            orv_package=orv,
            domains_pkg={
                "domains": {
                    "recovery": {"has_attention": True},
                    "operations": {"has_attention": False},
                    "communication": {"has_attention": False},
                }
            },
            store_executive_pkg={
                "home_teasers": {
                    "store_health_ar": "فرص استعادة المبيعات محدودة اليوم.",
                    "communication_ar": "تواصل العملاء يسير بشكل طبيعي.",
                },
                "briefing": {
                    "recovery_healthy_ar": "فرص الاستعادة محدودة اليوم.",
                },
            },
        )
        self.assertTrue(pkg["ok"])
        meanings = " ".join(
            str(f.get("business_meaning_ar") or "") for f in pkg["facts"]
        )
        types = {str(f.get("fact_type") or "") for f in pkg["facts"]}
        self.assertIn("Raven", meanings)
        self.assertIn("TrueSound", meanings)
        self.assertIn("customer_behaviour", types)
        self.assertIn("conversion", types)
        self.assertIn("recovery", types)
        self.assertTrue(
            any("يعودون" in str(f.get("business_meaning_ar") or "") for f in pkg["facts"])
        )
        self.assertTrue(
            any("استعادة" in str(f.get("business_meaning_ar") or "") for f in pkg["facts"])
        )
        # Never expose raw counter keys as facts.
        self.assertNotIn("waiting_total", meanings)
        self.assertNotIn("no_phone_total", meanings)
        for f in pkg["facts"]:
            self.assertIsNone(f.get("recommendation"))
            self.assertEqual(validate_business_fact_v1(f), [])

    def test_routing_home_and_workspace(self) -> None:
        orv = {
            "findings": [
                _orv_finding(
                    cap="high_interest_low_conversion",
                    product="Product A",
                    key="a",
                    statement="x",
                )
            ]
        }
        pkg = extract_business_facts_v1(store_slug="demo", orv_package=orv)
        routed = route_business_facts_v1(pkg)
        self.assertGreaterEqual(routed["home"]["product_fact_count"], 1)
        self.assertIsNotNone(routed["home_teaser"]["top"])
        cards = workspace_cards_from_business_facts_v1(pkg)
        self.assertTrue(cards)
        self.assertTrue(cards[0].get("gate_business_facts"))
        self.assertEqual(cards[0].get("recommended_action"), "")


class HomeIntegrationTests(unittest.TestCase):
    def test_hes_uses_business_fact_title(self) -> None:
        from services.home_executive_summary_v1.compose_v1 import (
            build_home_executive_summary_v1,
        )

        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {"domain_summary_ar": "نشاط المتجر مستقر."},
                    "decisions": {"count": 0, "top_title_ar": ""},
                    "observations": {
                        "count": 1,
                        "top": {
                            "product_name_ar": "Raven — حزام جلد للساعة",
                            "statement_ar": (
                                "Raven — حزام جلد للساعة يحظى باهتمام واضح، "
                                "لكن التحويل إلى شراء لا يزال ضعيفاً."
                            ),
                            "source": "business_facts_v1",
                        },
                        "evidence": "business_facts",
                    },
                    "carts": {"waiting": 0, "domain_summary_ar": "تقدّم سلال العملاء مستقر."},
                    "communication": {
                        "domain_summary_ar": "تواصل العملاء يسير بشكل طبيعي."
                    },
                }
            }
        )
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertIn(obs["title_ar"], {"حقائق المنتجات", "مواضيع المتجر"})
        self.assertIn(obs.get("built_from"), {"business_facts_v1", "business_themes_v1"})
        self.assertIn("اهتمام", obs["summary_ar"])
        self.assertNotIn("waiting_total", obs["summary_ar"])


class AllowlistTests(unittest.TestCase):
    def test_dev_route_allowlisted(self) -> None:
        from main import _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT

        self.assertIn("/dev/business-facts", _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT)


if __name__ == "__main__":
    unittest.main()
