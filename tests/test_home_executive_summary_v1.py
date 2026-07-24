# -*- coding: utf-8 -*-
"""Home Executive Summary V1 + entity-bound observation findings."""
from __future__ import annotations

import unittest

from services.home_executive_summary_v1.compose_v1 import (
    OBS_EMPTY_AR,
    attach_home_executive_summary_to_summary_v1,
    build_home_executive_summary_v1,
)
from services.observation_foundation_v1.merchant_findings_v1 import (
    build_observation_reality_validation_v1,
    project_merchant_observation_findings_v1,
)
from services.observation_foundation_v1.product_entity_resolve_v1 import (
    is_banned_product_key_v1,
)
from services.product_data.product_signal_types_v1 import (
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
)


class HomeExecutiveSummaryV1Tests(unittest.TestCase):
    def test_bans_demo_product_keys(self) -> None:
        self.assertTrue(is_banned_product_key_v1("DEMO-PERFUME"))
        self.assertTrue(is_banned_product_key_v1("orv-s1"))
        self.assertTrue(is_banned_product_key_v1("demo"))

    def test_skips_findings_without_real_product_name(self) -> None:
        findings = project_merchant_observation_findings_v1(
            {
                "store_slug": "store-a",
                "correlations": [
                    {
                        "statement_capability": "high_interest_low_conversion",
                        "product_key": "DEMO-PERFUME",
                        "correlation_kind": "product_interest_conversion_v1",
                        "counts": {"cart_add": 2, "purchase": 0},
                        "evidence_refs": [{"id": 1}, {"id": 2}],
                    }
                ],
            },
            store_slug="store-a",
            product_name_resolver=lambda slug, key: None,
        )
        self.assertEqual(findings, [])

    def test_entity_bound_finding_includes_product_name(self) -> None:
        findings = project_merchant_observation_findings_v1(
            {
                "store_slug": "store-a",
                "correlations": [
                    {
                        "statement_capability": "high_interest_low_conversion",
                        "product_key": "sku:rose-oil",
                        "correlation_kind": "product_interest_conversion_v1",
                        "counts": {"cart_add": 2, "purchase": 0},
                        "evidence_refs": [{"id": 1}, {"id": 2}, {"id": 3}],
                    }
                ],
            },
            store_slug="store-a",
            product_name_resolver=lambda slug, key: "زيت الورد",
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["product_name_ar"], "زيت الورد")
        self.assertTrue(findings[0]["statement_ar"])
        self.assertTrue(findings[0]["recommended_action_ar"])
        self.assertIn(findings[0]["confidence_ar"], {"مرتفع", "متوسط", "منخفض"})

    def test_approved_mass_off_by_default(self) -> None:
        pkg = build_observation_reality_validation_v1(
            "empty-store",
            environ={
                "CARTFLOW_OBSERVATION_FOUNDATION_V1": "1",
                "CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1": "1",
                "CARTFLOW_ORV_APPROVED_MASS_V1": "0",
            },
        )
        self.assertTrue(pkg["ok"])
        self.assertEqual(pkg["findings"], [])
        self.assertEqual(pkg["empty_state_ar"], OBS_EMPTY_AR)

    def test_executive_summary_sections_and_slim_orv(self) -> None:
        summary = {
            "observation_reality_validation_v1": {
                "ok": True,
                "enabled": True,
                "findings": [
                    {
                        "product_name_ar": "زيت الورد",
                        "statement_ar": "اهتمام مرتفع وتحويل منخفض.",
                        "recommended_action_ar": "راجع صفحة المنتج.",
                        "confidence_ar": "مرتفع",
                        "confidence_level": "high",
                        "capability_id": "high_interest_low_conversion",
                        "evidence_details": {"cart_add": 2},
                        "diagnostics": {"product_key": "x"},
                    }
                ],
            },
            "merchant_experience_integration_v1": {
                "ok": True,
                "pages": {
                    "home": {
                        "operational_truth": {
                            "has_durable_carts": True,
                            "abandoned_carts": 3,
                        },
                        "sections": {
                            "merchant_decisions": [
                                {"title_ar": "راجع سلة عالية القيمة"}
                            ]
                        },
                    }
                },
            },
        }
        out = attach_home_executive_summary_to_summary_v1(
            dict(summary),
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        hes = out["home_executive_summary_v1"]
        self.assertTrue(hes["ok"])
        self.assertEqual(out["home_surface_mode"], "executive_summary_v1")
        ids = [s["id"] for s in hes["sections"]]
        self.assertEqual(ids, ["health", "decisions", "observations"])
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertEqual(obs["count"], 1)
        self.assertIn("زيت الورد", obs["summary_ar"])
        slim = out["observation_reality_validation_v1"]
        self.assertNotIn("evidence_details", slim["findings"][0])
        self.assertNotIn("diagnostics", slim["findings"][0])

    def test_observation_empty_summary_copy(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "observation_reality_validation_v1": {
                    "ok": True,
                    "enabled": True,
                    "findings": [],
                }
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertTrue(obs["empty"])
        self.assertEqual(obs["summary_ar"], OBS_EMPTY_AR)


if __name__ == "__main__":
    unittest.main()
