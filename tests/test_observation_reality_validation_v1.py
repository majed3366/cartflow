# -*- coding: utf-8 -*-
"""Observation Reality Validation V1 — merchant findings (polished surface)."""
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
    def test_projects_all_four_when_evidence_present(self) -> None:
        signals = [
            {
                "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                "stable_identity_key": "sku:a",
                "session_id": "1",
                "evidence_ref_id": "1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                "stable_identity_key": "sku:a",
                "session_id": "2",
                "evidence_ref_id": "2",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "sku:a",
                "reason_code": "shipping",
                "evidence_ref_id": "h1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "sku:a",
                "reason_code": "delivery",
                "evidence_ref_id": "h2",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "sku:a",
                "reason_code": "price",
                "evidence_ref_id": "h3",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
                "stable_identity_key": "sku:a",
                "customer_key": "c1",
                "session_id": "r1",
                "evidence_ref_id": "r1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
                "stable_identity_key": "sku:a",
                "customer_key": "c1",
                "session_id": "r2",
                "evidence_ref_id": "r2",
            },
        ]
        pkg = build_observation_reality_validation_v1("demo", signals=signals)
        self.assertTrue(pkg["ok"])
        self.assertTrue(pkg["acceptance_all_four"])
        for f in pkg["findings"]:
            self.assertTrue(f["statement_ar"])
            self.assertTrue(f["recommended_action_ar"])
            self.assertIn(f["confidence_ar"], {"مرتفع", "متوسط", "منخفض"})
            self.assertIn(f["confidence_level"], {"low", "medium", "high", "very_high"})
            # Technical fields must not be merchant-facing keys
            self.assertNotIn("evidence_summary", f)
            self.assertIn("evidence_details", f)
            self.assertIn("counts", f["evidence_details"])

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


if __name__ == "__main__":
    unittest.main()
