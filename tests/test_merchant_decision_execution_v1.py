# -*- coding: utf-8 -*-
"""Merchant decision execution v1 — governed decision layer tests."""
from __future__ import annotations

import unittest

from services.merchant_decision_layer_v1 import (
    CLASS_NEEDS_ATTENTION,
    CLASS_OBSERVATION,
    CLASS_SUGGESTED_ACTION,
    DECISION_CONTACT_CUSTOMER,
    DECISION_MONITOR,
    DECISION_OBTAIN_CONTACT,
    LIFECYCLE_PUBLISHED,
    SUPPRESSION_ALREADY_ADDRESSED,
    SUPPRESSION_SILENT,
    VERIFY_PASSED,
    attach_merchant_decisions_v1,
    build_cart_row_merchant_decisions_v1,
    build_kl_observation_decision_v1,
    enrich_knowledge_report_merchant_decisions_v1,
    get_merchant_decision_observability_v1,
    reset_merchant_decision_observability_v1,
    validate_merchant_decision_contract_v1,
)
from services.merchant_decision_registry_v1 import (
    DECISION_ID_CONTACT_CUSTOMER,
    decision_id_for_action_key,
)
from services.merchant_proof_surface_v1 import attach_merchant_proof_surface_v1


def _sample_proof(**overrides: object) -> dict:
    base = {
        "version": "v1",
        "confidence": "medium",
        "evidence_id": "customer_journey",
        "proof_source": "demo:cart:1",
        "what_happened_ar": "تحتاج تدخل",
        "why_we_know_ar": "حالة المسار: needs_intervention",
        "recovery_steps": [],
    }
    base.update(overrides)
    return base


class MerchantDecisionExecutionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        reset_merchant_decision_observability_v1()

    def test_registry_maps_action_keys(self) -> None:
        self.assertEqual(
            decision_id_for_action_key(DECISION_OBTAIN_CONTACT),
            "decision_obtain_contact",
        )
        self.assertEqual(
            decision_id_for_action_key(DECISION_CONTACT_CUSTOMER),
            DECISION_ID_CONTACT_CUSTOMER,
        )

    def test_obtain_contact_capped_without_eligible_action(self) -> None:
        bundle = build_cart_row_merchant_decisions_v1(
            proof=_sample_proof(),
            recovery_key="demo:cart:1",
            customer_lifecycle_state="needs_intervention",
            customer_lifecycle_merchant_needed_ar="نعم",
            merchant_decision_key=DECISION_OBTAIN_CONTACT,
            action_eligible=False,
        )
        self.assertEqual(len(bundle["decisions"]), 1)
        dec = bundle["decisions"][0]
        self.assertEqual(dec["decision_class"], CLASS_NEEDS_ATTENTION)
        self.assertEqual(validate_merchant_decision_contract_v1(dec), [])

    def test_contact_customer_suggested_when_executable(self) -> None:
        bundle = build_cart_row_merchant_decisions_v1(
            proof=_sample_proof(confidence="high"),
            recovery_key="demo:cart:2",
            customer_lifecycle_state="needs_intervention",
            customer_lifecycle_merchant_needed_ar="نعم",
            merchant_decision_key=DECISION_CONTACT_CUSTOMER,
            action_eligible=True,
        )
        dec = bundle["decisions"][0]
        self.assertEqual(dec["decision_class"], CLASS_SUGGESTED_ACTION)
        self.assertEqual(dec["merchant_action"], "execute")
        self.assertEqual(dec["commercial_goal"], "recover_revenue")

    def test_purchase_truth_suppresses_decision(self) -> None:
        bundle = build_cart_row_merchant_decisions_v1(
            proof=_sample_proof(confidence="confirmed"),
            recovery_key="demo:cart:3",
            customer_lifecycle_state="completed",
            customer_lifecycle_merchant_needed_ar="نعم",
            merchant_decision_key=DECISION_CONTACT_CUSTOMER,
            purchase_truth=True,
        )
        self.assertEqual(bundle["decisions"], [])
        self.assertEqual(len(bundle["suppressed"]), 1)
        self.assertEqual(
            bundle["suppressed"][0]["suppression_state"],
            SUPPRESSION_ALREADY_ADDRESSED,
        )

    def test_monitor_return_is_observation(self) -> None:
        bundle = build_cart_row_merchant_decisions_v1(
            proof=_sample_proof(),
            recovery_key="demo:cart:4",
            customer_lifecycle_state="return_to_site",
            customer_lifecycle_merchant_needed_ar="لا",
            merchant_decision_key=DECISION_MONITOR,
        )
        dec = bundle["decisions"][0]
        self.assertEqual(dec["decision_class"], CLASS_OBSERVATION)
        self.assertEqual(dec["merchant_action"], "monitor")

    def test_silent_suppression_when_merchant_not_needed(self) -> None:
        bundle = build_cart_row_merchant_decisions_v1(
            proof=_sample_proof(),
            recovery_key="demo:cart:5",
            customer_lifecycle_state="needs_intervention",
            customer_lifecycle_merchant_needed_ar="لا",
            merchant_decision_key=DECISION_OBTAIN_CONTACT,
        )
        self.assertEqual(bundle["decisions"], [])
        self.assertEqual(
            bundle["suppressed"][0]["suppression_state"],
            SUPPRESSION_SILENT,
        )

    def test_attach_after_proof_surface(self) -> None:
        row = {
            "recovery_key": "demo:attach:1",
            "customer_lifecycle_state": "needs_intervention",
            "customer_lifecycle_merchant_needed_ar": "نعم",
            "merchant_decision_key": DECISION_CONTACT_CUSTOMER,
            "merchant_intervention_executable": True,
        }
        attach_merchant_proof_surface_v1(
            row,
            recovery_key="demo:attach:1",
            log_statuses=["sent_real"],
            sent_count=1,
        )
        attach_merchant_decisions_v1(row)
        md = row["merchant_decisions_v1"]
        self.assertEqual(md["version"], "v1")
        self.assertEqual(len(md["decisions"]), 1)
        self.assertEqual(md["decisions"][0]["lifecycle_state"], LIFECYCLE_PUBLISHED)
        self.assertEqual(md["decisions"][0]["verification_status"], VERIFY_PASSED)
        self.assertNotIn("customer_lifecycle_state", md)

    def test_kl_observation_decision_contract(self) -> None:
        dec = build_kl_observation_decision_v1(
            {
                "insight_key": "hesitation_top_reason",
                "evidence_id": "hesitation_reason",
                "confidence": "medium",
                "title_ar": "سبب التردد الأبرز",
            }
        )
        assert dec is not None
        self.assertEqual(dec["decision_class"], CLASS_OBSERVATION)
        self.assertEqual(validate_merchant_decision_contract_v1(dec), [])

    def test_kl_report_enrichment(self) -> None:
        payload: dict = {
            "insights": [
                {
                    "insight_key": "conversion_cart_to_purchase",
                    "evidence_id": "purchase_record",
                    "confidence": "high",
                    "title_ar": "تحويل السلة",
                },
                {
                    "insight_key": "hesitation_top_reason",
                    "evidence_id": "hesitation_reason",
                    "confidence": "medium",
                    "title_ar": "سبب التردد",
                },
            ],
        }
        enrich_knowledge_report_merchant_decisions_v1(payload)
        md = payload["merchant_decisions_v1"]
        self.assertEqual(len(md["decisions"]), 2)
        self.assertIn("registry", md)
        self.assertIn("observability", md)

    def test_observability_metrics(self) -> None:
        build_cart_row_merchant_decisions_v1(
            proof=_sample_proof(),
            recovery_key="demo:obs:1",
            customer_lifecycle_state="return_to_site",
            customer_lifecycle_merchant_needed_ar="لا",
            merchant_decision_key=DECISION_MONITOR,
        )
        obs = get_merchant_decision_observability_v1()
        self.assertGreaterEqual(obs["generated_decisions"], 1)
        self.assertGreaterEqual(obs["published_decisions"], 1)
        self.assertIn(CLASS_OBSERVATION, obs["decision_classes"])


if __name__ == "__main__":
    unittest.main()
