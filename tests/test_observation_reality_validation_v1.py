# -*- coding: utf-8 -*-
"""Observation Reality Validation — entity-bound merchant findings."""
from __future__ import annotations

import unittest

from services.observation_foundation_v1.merchant_findings_v1 import (
    build_observation_reality_validation_v1,
    project_merchant_observation_findings_v1,
)
from services.product_data.product_signal_types_v1 import (
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
)


class ObservationRealityValidationV1Tests(unittest.TestCase):
    def test_projects_all_four_when_named_product_present(self) -> None:
        signals = [
            {
                "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                "stable_identity_key": "sku:rose-oil",
                "product_key": "sku:rose-oil",
                "session_id": "1",
                "evidence_ref_id": "1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                "stable_identity_key": "sku:rose-oil",
                "product_key": "sku:rose-oil",
                "session_id": "2",
                "evidence_ref_id": "2",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "sku:rose-oil",
                "product_key": "sku:rose-oil",
                "reason_code": "shipping",
                "evidence_ref_id": "h1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "sku:rose-oil",
                "product_key": "sku:rose-oil",
                "reason_code": "thinking",
                "evidence_ref_id": "h2",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
                "stable_identity_key": "sku:rose-oil",
                "product_key": "sku:rose-oil",
                "customer_key": "c1",
                "session_id": "r1",
                "evidence_ref_id": "r1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
                "stable_identity_key": "sku:rose-oil",
                "product_key": "sku:rose-oil",
                "customer_key": "c1",
                "session_id": "r2",
                "evidence_ref_id": "r2",
            },
        ]
        # Bypass DB name resolve with injected correlations projection
        from services.observation_foundation_v1.assemble_v1 import (
            assemble_observation_foundation_v1,
        )

        pkg = assemble_observation_foundation_v1("demo", signals=signals)
        findings = project_merchant_observation_findings_v1(
            pkg,
            store_slug="demo",
            product_name_resolver=lambda slug, key: "عطر تجريبي",
        )
        self.assertEqual(len(findings), 4)
        for f in findings:
            self.assertEqual(f["product_name_ar"], "عطر تجريبي")
            self.assertTrue(f["statement_ar"])
            self.assertTrue(f["recommended_action_ar"])
            self.assertIn(f["confidence_ar"], {"مرتفع", "متوسط", "منخفض"})
            self.assertNotIn("evidence_summary", f)

    def test_no_finding_without_capability(self) -> None:
        findings = project_merchant_observation_findings_v1(
            {
                "correlations": [
                    {
                        "correlation_kind": "product_customer_behavior_v1",
                        "statement_capability": None,
                        "product_key": "x",
                    }
                ]
            }
        )
        self.assertEqual(findings, [])

    def test_build_without_named_products_is_honest_empty(self) -> None:
        pkg = build_observation_reality_validation_v1(
            "demo",
            signals=[
                {
                    "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                    "stable_identity_key": "DEMO-PERFUME",
                    "product_key": "DEMO-PERFUME",
                    "session_id": "1",
                    "evidence_ref_id": "1",
                },
                {
                    "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                    "stable_identity_key": "DEMO-PERFUME",
                    "product_key": "DEMO-PERFUME",
                    "session_id": "2",
                    "evidence_ref_id": "2",
                },
            ],
            environ={
                "CARTFLOW_OBSERVATION_FOUNDATION_V1": "1",
                "CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1": "1",
                "CARTFLOW_ORV_APPROVED_MASS_V1": "0",
            },
        )
        self.assertTrue(pkg["ok"])
        self.assertEqual(pkg["findings"], [])
        self.assertTrue(pkg["empty_state_ar"])


if __name__ == "__main__":
    unittest.main()
