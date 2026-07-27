# -*- coding: utf-8 -*-
"""Diagnostic Reasoning Foundation V1 — evidence gate + Home read-only."""
from __future__ import annotations

import unittest

from services.diagnostic_reasoning_v1.compose_v1 import compose_diagnostic_contract_v1
from services.diagnostic_reasoning_v1.contract_v1 import (
    AR_INSUFFICIENT_SHIPPING_STAGE,
    AR_SHIPPING_COST,
    DIAGNOSIS_STATUS_CONFLICTING,
    DIAGNOSIS_STATUS_INSUFFICIENT,
    DIAGNOSIS_STATUS_SUPPORTED,
    FAMILY_CHECKOUT_AFTER_SHIPPING,
    FAMILY_INTEREST_WITHOUT_PURCHASE,
    FAMILY_PAYMENT_FRICTION,
    validate_contract_v1,
)
from services.diagnostic_reasoning_v1.evidence_bag_v1 import (
    build_evidence_bags_from_reason_counts_v1,
)
from services.diagnostic_reasoning_v1.recommendation_registry_v1 import (
    assert_recommendation_derives_from_diagnosis_v1,
)
from services.diagnostic_reasoning_v1.scoring_v1 import select_diagnosis_v1


class DiagnosticReasoningV1Tests(unittest.TestCase):
    def test_shipping_stage_without_subtype_is_insufficient(self) -> None:
        bag = {
            "signals": {"shipping": 5, "shipping_stage_observed": 1},
            "sample_n": 5,
            "minimum_sample": 3,
            "product_identity_ok": True,
            "product_name_ar": "Nano 20W",
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
            subject_id="nano",
        )
        self.assertEqual(c["diagnosis_status"], DIAGNOSIS_STATUS_INSUFFICIENT)
        self.assertEqual(c["diagnosis_ar"], AR_INSUFFICIENT_SHIPPING_STAGE)
        self.assertTrue(assert_recommendation_derives_from_diagnosis_v1(c))
        self.assertNotIn("تكلفة الشحن هي السبب", c["diagnosis_ar"])

    def test_shipping_cost_supported_when_distinguished(self) -> None:
        bag = {
            "signals": {"shipping_cost": 8, "delivery_time": 0, "payment": 0},
            "sample_n": 8,
            "minimum_sample": 3,
            "product_identity_ok": True,
            "recurrence_days": 3,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        self.assertEqual(c["diagnosis_status"], DIAGNOSIS_STATUS_SUPPORTED)
        self.assertEqual(c["selected_diagnosis"], "shipping_cost")
        self.assertEqual(c["diagnosis_ar"], AR_SHIPPING_COST)
        self.assertIn("الشحن", c["recommendation_ar"])
        self.assertTrue(c["supporting_evidence"])
        ok, errs = validate_contract_v1(c)
        self.assertTrue(ok, errs)

    def test_conflicting_shipping_and_price(self) -> None:
        bag = {
            "signals": {"shipping_cost": 5, "delivery_time": 5},
            "sample_n": 10,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        sel = select_diagnosis_v1(FAMILY_CHECKOUT_AFTER_SHIPPING, evidence_bag=bag)
        self.assertEqual(sel["diagnosis_status"], DIAGNOSIS_STATUS_CONFLICTING)

    def test_payment_friction_supported(self) -> None:
        bag = {
            "signals": {"payment": 6},
            "sample_n": 6,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_PAYMENT_FRICTION,
            evidence_bag=bag,
        )
        self.assertEqual(c["diagnosis_status"], DIAGNOSIS_STATUS_SUPPORTED)
        self.assertEqual(c["selected_diagnosis"], "payment_friction")

    def test_interest_insufficient_causal(self) -> None:
        bag = {
            "signals": {"interest_without_purchase": 4},
            "sample_n": 4,
            "minimum_sample": 3,
            "product_identity_ok": True,
            "product_name_ar": "زيت الورد",
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_INTEREST_WITHOUT_PURCHASE,
            evidence_bag=bag,
        )
        self.assertEqual(c["diagnosis_status"], DIAGNOSIS_STATUS_INSUFFICIENT)
        self.assertIn("غير كافية", c["diagnosis_ar"])

    def test_insufficient_sample(self) -> None:
        bag = {
            "signals": {"shipping_cost": 1},
            "sample_n": 1,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        sel = select_diagnosis_v1(FAMILY_CHECKOUT_AFTER_SHIPPING, evidence_bag=bag)
        # support_n=1 < minimum_evidence=3 → no causal meets_minimum
        self.assertEqual(sel["diagnosis_status"], DIAGNOSIS_STATUS_INSUFFICIENT)

    def test_no_recommendation_without_diagnosis(self) -> None:
        bag = {
            "signals": {"shipping": 4},
            "sample_n": 4,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        self.assertEqual(
            c["recommendation"]["cause_key"], "insufficient_evidence"
        )
        self.assertTrue(assert_recommendation_derives_from_diagnosis_v1(c))

    def test_deterministic_selection(self) -> None:
        bag = {
            "signals": {"shipping_cost": 9},
            "sample_n": 9,
            "minimum_sample": 3,
            "product_identity_ok": True,
            "recurrence_days": 4,
        }
        a = select_diagnosis_v1(FAMILY_CHECKOUT_AFTER_SHIPPING, evidence_bag=bag)
        b = select_diagnosis_v1(FAMILY_CHECKOUT_AFTER_SHIPPING, evidence_bag=bag)
        self.assertEqual(a, b)

    def test_evidence_bag_builder_shipping_stage(self) -> None:
        bags = build_evidence_bags_from_reason_counts_v1(
            store_slug="demo",
            reason_counts={"shipping": 4},
            product_name_ar="Nano 20W",
            product_id="nano",
            shipping_stage_observed=True,
        )
        families = {b["diagnostic_family"] for b in bags}
        self.assertIn(FAMILY_CHECKOUT_AFTER_SHIPPING, families)

    def test_hes_prefers_persisted_publication(self) -> None:
        from services.home_executive_summary_v1.compose_v1 import (
            build_home_executive_summary_v1,
        )

        hes = build_home_executive_summary_v1(
            {
                "diagnostic_publication_v1": {
                    "diagnosis_ar": AR_INSUFFICIENT_SHIPPING_STAGE,
                    "recommendation_ar": "لا يُوصى بتغيير تجاري بعد؛ واصل جمع الأدلة.",
                    "observation_ar": "يغادر العملاء بعد خطوة الشحن.",
                    "diagnostic_family": FAMILY_CHECKOUT_AFTER_SHIPPING,
                    "diagnosis_status": DIAGNOSIS_STATUS_INSUFFICIENT,
                },
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "decisions": {
                        "count": 1,
                        "top_title_ar": "راجع مسار التحويل.",
                    },
                    "observations": {"count": 0},
                    "health": {"no_phone": 0, "store_connected": True},
                    "carts": {},
                    "communication": {},
                },
                "merchant_publication_v1": {
                    "ok": True,
                    "primary_action": "راجع مسار التحويل.",
                    "primary_subject": "Nano 20W",
                    "highest_priority_decision_id": "d1",
                },
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        dec = next(s for s in hes["sections"] if s["id"] == "decisions")
        self.assertEqual(dec["diagnosis_ar"], AR_INSUFFICIENT_SHIPPING_STAGE)
        self.assertFalse(str(dec["diagnosis_ar"]).startswith("راجع"))
        self.assertEqual(hes.get("diagnostic_reasoning"), "diagnostic_reasoning_v1")


if __name__ == "__main__":
    unittest.main()
