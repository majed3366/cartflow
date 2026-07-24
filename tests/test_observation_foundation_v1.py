# -*- coding: utf-8 -*-
"""Observation Foundation V1 — catalog, correlations, readiness (no UI)."""
from __future__ import annotations

import unittest

from services.observation_foundation_v1 import (
    assemble_observation_foundation_v1,
    assess_product_intelligence_readiness_v1,
    correlation_model_dict_v1,
    observation_catalog_dict_v1,
    observation_foundation_v1_enabled,
)
from services.observation_foundation_v1.catalog_v1 import OBSERVATION_TYPES_V1
from services.observation_foundation_v1.correlation_v1 import CHAIN_STAGES_V1
from services.product_data.product_signal_types_v1 import (
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
    SIGNAL_PRODUCT_PURCHASED,
)


class ObservationFoundationV1Tests(unittest.TestCase):
    def test_flag_default_on(self) -> None:
        self.assertTrue(observation_foundation_v1_enabled(environ={}))

    def test_observation_model_covers_required_types(self) -> None:
        cat = observation_catalog_dict_v1()
        self.assertEqual(cat["counts"]["total"], 13)
        self.assertFalse(cat["ui"])
        self.assertEqual(len(OBSERVATION_TYPES_V1), 13)
        statuses = {e["observation_type"]: e["evidence_status"] for e in cat["entries"]}
        self.assertEqual(statuses["cart_add_observed_v1"], "wired")
        self.assertEqual(statuses["purchase_observed_v1"], "wired")
        self.assertEqual(statuses["hesitation_reason_observed_v1"], "wired")
        self.assertEqual(statuses["product_view_observed_v1"], "unavailable")
        self.assertEqual(statuses["time_spent_observed_v1"], "unavailable")

    def test_correlation_model_chain(self) -> None:
        cm = correlation_model_dict_v1()
        self.assertEqual(
            cm["chain"],
            ["product", "customer_behavior", "reason", "return", "purchase"],
        )
        self.assertEqual(list(CHAIN_STAGES_V1), cm["chain"])
        self.assertFalse(cm["intelligence"])

    def test_assemble_correlations_enable_statement_capabilities(self) -> None:
        signals = [
            {
                "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                "stable_identity_key": "sku:shirt",
                "session_id": "s1",
                "evidence_ref_type": "cart_line_snapshot",
                "evidence_ref_id": "1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                "stable_identity_key": "sku:shirt",
                "session_id": "s2",
                "evidence_ref_type": "cart_line_snapshot",
                "evidence_ref_id": "2",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "sku:shirt",
                "session_id": "s1",
                "reason_code": "shipping_cost",
                "evidence_ref_type": "product_hesitation_mapping",
                "evidence_ref_id": "h1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "sku:shirt",
                "session_id": "s1b",
                "reason_code": "delivery",
                "evidence_ref_type": "product_hesitation_mapping",
                "evidence_ref_id": "h1b",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "sku:shirt",
                "session_id": "s2",
                "reason_code": "price",
                "evidence_ref_type": "product_hesitation_mapping",
                "evidence_ref_id": "h2",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
                "stable_identity_key": "sku:shirt",
                "session_id": "s3",
                "customer_key": "c1",
                "evidence_ref_type": "session",
                "evidence_ref_id": "s3",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
                "stable_identity_key": "sku:shirt",
                "session_id": "s4",
                "customer_key": "c1",
                "evidence_ref_type": "session",
                "evidence_ref_id": "s4",
            },
        ]
        pkg = assemble_observation_foundation_v1("demo", signals=signals)
        self.assertTrue(pkg["ok"])
        self.assertFalse(pkg["ui"])
        caps = set(pkg["statement_capabilities_ready"])
        self.assertIn("high_interest_low_conversion", caps)
        self.assertIn("shipping_stronger_than_price", caps)
        self.assertIn("repeated_return_without_purchase", caps)
        self.assertIn("no_quality_issue_evidence", caps)
        # No purchases in fixture
        self.assertNotIn(
            SIGNAL_PRODUCT_PURCHASED,
            [s["signal_type"] for s in signals],
        )

    def test_readiness_conditional_without_store_mass(self) -> None:
        ready = assess_product_intelligence_readiness_v1(
            "empty-store",
            package=assemble_observation_foundation_v1("empty-store", signals=[]),
        )
        self.assertEqual(ready["verdict"], "CONDITIONAL")
        self.assertFalse(ready["ready_for_product_intelligence_v1"])
        self.assertTrue(ready["structural"]["structural_ok"])

    def test_readiness_go_with_correlated_store(self) -> None:
        signals = [
            {
                "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                "stable_identity_key": "p1",
                "session_id": "a",
                "evidence_ref_id": "1",
            },
            {
                "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                "stable_identity_key": "p1",
                "session_id": "b",
                "evidence_ref_id": "2",
            },
            {
                "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                "stable_identity_key": "p1",
                "reason_code": "delivery",
                "evidence_ref_id": "h",
            },
        ]
        pkg = assemble_observation_foundation_v1("demo", signals=signals)
        ready = assess_product_intelligence_readiness_v1("demo", package=pkg)
        self.assertEqual(ready["verdict"], "GO")
        self.assertTrue(ready["ready_for_product_intelligence_v1"])
        self.assertIn("product_view_observed_v1", " ".join(ready["blockers_for_full_pi_v1"]))


if __name__ == "__main__":
    unittest.main()
