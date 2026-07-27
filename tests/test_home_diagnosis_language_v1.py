# -*- coding: utf-8 -*-
"""Home Diagnosis Language V1 — Observation → Diagnosis → Recommendation."""
from __future__ import annotations

import unittest

from services.home_executive_summary_v1.compose_v1 import build_home_executive_summary_v1
from services.home_executive_summary_v1.diagnosis_language_v1 import (
    BELIEVES_AR,
    DIAG_INSUFFICIENT_AR,
    REC_COMMUNICATION_AR,
    REC_CONTINUE_EVIDENCE_AR,
    REC_PURCHASE_JOURNEY_AR,
    diagnosis_opens_correctly,
)


class HomeDiagnosisLanguageV1Tests(unittest.TestCase):
    def test_health_contact_blocked_is_diagnosis_not_event(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {
                        "needs_attention": True,
                        "no_phone": 8,
                        "store_connected": True,
                        "domain_summary_ar": (
                            "المتجر يحتاج تدخلاً عاجلاً — متابعة العملاء "
                            "مقيدة بسبب نقص معلومات التواصل."
                        ),
                        "status_ar": "يحتاج تدخلاً عاجلاً",
                    },
                    "decisions": {"count": 0},
                    "observations": {"count": 0},
                    "carts": {},
                    "communication": {"no_phone": 8, "constrained": True},
                }
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        health = next(s for s in hes["sections"] if s["id"] == "health")
        self.assertTrue(health["diagnosis_ar"].startswith(BELIEVES_AR))
        self.assertIn("معلومات تواصل", health["diagnosis_ar"])
        self.assertEqual(health["recommendation_ar"], REC_COMMUNICATION_AR)
        self.assertFalse(health["diagnosis_ar"].startswith("راجع"))
        self.assertEqual(health["view_details_href"], "#communication")
        self.assertTrue(diagnosis_opens_correctly(health["summary_ar"]))

    def test_decision_never_starts_with_review(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "decisions": {
                        "count": 1,
                        "top_title_ar": "راجع مسار التحويل لـ Nano 20W.",
                        "evidence": "decision_titles",
                    },
                    "observations": {"count": 0},
                    "health": {},
                    "carts": {},
                    "communication": {},
                },
                "merchant_publication_v1": {
                    "ok": True,
                    "primary_action": "راجع مسار التحويل لـ Nano 20W.",
                    "primary_subject": "Nano 20W — رأس شحن",
                    "highest_priority_decision_id": "d1",
                },
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        dec = next(s for s in hes["sections"] if s["id"] == "decisions")
        self.assertFalse(dec["diagnosis_ar"].startswith("راجع"))
        self.assertIn("Nano 20W", dec["diagnosis_ar"])
        self.assertEqual(dec["recommendation_ar"], REC_PURCHASE_JOURNEY_AR)
        self.assertTrue(diagnosis_opens_correctly(dec["summary_ar"]))

    def test_decision_empty_is_insufficient_evidence(self) -> None:
        hes = build_home_executive_summary_v1(
            {},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        dec = next(s for s in hes["sections"] if s["id"] == "decisions")
        self.assertEqual(dec["diagnosis_ar"], DIAG_INSUFFICIENT_AR)
        self.assertEqual(dec["recommendation_ar"], REC_CONTINUE_EVIDENCE_AR)

    def test_product_interest_without_confirmed_cause(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "observations": {
                        "count": 1,
                        "top": {
                            "product_name_ar": "زيت الورد",
                            "statement_ar": "اهتمام مرتفع وتحويل منخفض.",
                        },
                        "evidence": "product_findings",
                    },
                    "decisions": {"count": 0},
                    "health": {},
                    "carts": {},
                    "communication": {},
                }
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertIn("نية شراء", obs["diagnosis_ar"])
        self.assertIn("لم يؤكد بعد", obs["diagnosis_ar"])
        self.assertNotIn("اهتمام مرتفع وتحويل منخفض", obs["diagnosis_ar"])
        self.assertEqual(obs["recommendation_ar"], REC_CONTINUE_EVIDENCE_AR)

    def test_communication_phone_diagnosis(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "merchant_store_cart_counts": {
                    "waiting_total": 3,
                    "no_phone_total": 2,
                    "active_total": 8,
                },
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        comm = next(s for s in hes["sections"] if s["id"] == "communication")
        self.assertIn("رقم الهاتف", comm["diagnosis_ar"])
        self.assertEqual(comm["recommendation_ar"], REC_COMMUNICATION_AR)
        self.assertFalse(comm["diagnosis_ar"].startswith("بعض العملاء"))

    def test_governance_marker(self) -> None:
        hes = build_home_executive_summary_v1(
            {},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        self.assertEqual(
            hes.get("diagnosis_language"), "home_diagnosis_language_v1"
        )
        self.assertEqual(
            hes["governance"].get("diagnosis_language"),
            "home_diagnosis_language_v1",
        )


if __name__ == "__main__":
    unittest.main()
