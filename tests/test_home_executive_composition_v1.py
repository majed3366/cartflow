# -*- coding: utf-8 -*-
"""Gate 1-B — Executive Summary Composition."""
from __future__ import annotations

import unittest

from services.home_executive_summary_v1.compose_v1 import (
    DECISIONS_EMPTY_AR,
    OBS_EMPTY_AR,
    SECTION_OWNERSHIP_HREF_V1,
    build_home_executive_summary_v1,
)
from services.home_executive_summary_v1.slim_transport_v1 import (
    extract_home_teaser_inputs_v1,
)


class HomeExecutiveCompositionV1Tests(unittest.TestCase):
    def test_store_status_title_and_stable_ops(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "merchant_store_cart_counts": {"active_total": 5, "waiting_total": 0},
                "merchant_kpi_recovered_fmt": "1",
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        health = next(s for s in hes["sections"] if s["id"] == "health")
        self.assertEqual(health["title_ar"], "حالة المتجر")
        self.assertNotEqual(health["title_ar"], "صحة العمل")
        self.assertIn("مستقرة", health["summary_ar"])
        self.assertEqual(health["view_details_href"], "#carts")
        self.assertEqual(health.get("count"), 5)

    def test_quiet_store_omits_count(self) -> None:
        hes = build_home_executive_summary_v1(
            {},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        health = next(s for s in hes["sections"] if s["id"] == "health")
        self.assertNotIn("count", health)
        self.assertEqual(health["title_ar"], "حالة المتجر")

    def test_carts_and_communication_operational_conditions(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "merchant_nav_badge_abandoned": 3,
                "merchant_store_cart_counts": {
                    "waiting_total": 3,
                    "no_phone_total": 2,
                    "active_total": 8,
                },
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        carts = next(s for s in hes["sections"] if s["id"] == "carts")
        comm = next(s for s in hes["sections"] if s["id"] == "communication")
        self.assertIn("بانتظار المتابعة", carts["summary_ar"])
        self.assertIn("بلا رقم تواصل", carts["summary_ar"])
        self.assertIn("بانتظار المتابعة", comm["summary_ar"])
        self.assertEqual(carts["view_details_href"], SECTION_OWNERSHIP_HREF_V1["carts"])
        self.assertEqual(
            comm["view_details_href"], SECTION_OWNERSHIP_HREF_V1["communication"]
        )

    def test_decisions_never_invented(self) -> None:
        hes = build_home_executive_summary_v1(
            {"merchant_nav_badge_abandoned": 9},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        dec = next(s for s in hes["sections"] if s["id"] == "decisions")
        self.assertEqual(dec["summary_ar"], DECISIONS_EMPTY_AR)
        self.assertTrue(dec["empty"])
        self.assertEqual(dec["view_details_href"], "#workspace")

    def test_decision_title_when_evidence_present(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "decisions": {
                        "count": 1,
                        "top_title_ar": "راجع تكلفة الشحن.",
                        "evidence": "decision_titles",
                    },
                    "observations": {"count": 0},
                    "health": {},
                    "carts": {},
                    "communication": {},
                }
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        dec = next(s for s in hes["sections"] if s["id"] == "decisions")
        self.assertEqual(dec["summary_ar"], "راجع تكلفة الشحن.")
        self.assertFalse(dec["empty"])

    def test_observation_constitutional_empty(self) -> None:
        hes = build_home_executive_summary_v1(
            {},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertEqual(obs["summary_ar"], OBS_EMPTY_AR)

    def test_observation_product_line(self) -> None:
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
        self.assertIn("زيت الورد", obs["summary_ar"])
        self.assertNotIn("recommended_action", str(obs))
        self.assertEqual(obs["view_details_href"], "#workspace")

    def test_teasers_from_light_counts(self) -> None:
        t = extract_home_teaser_inputs_v1(
            {
                "merchant_store_cart_counts": {
                    "active_total": 4,
                    "waiting_total": 2,
                    "no_phone_total": 1,
                },
                "merchant_kpi_wa_sent_fmt": "3",
            }
        )
        self.assertEqual(t["carts"]["waiting"], 2)
        self.assertEqual(t["carts"]["no_phone"], 1)
        self.assertEqual(t["communication"]["sent"], 3)
        self.assertTrue(t["health"]["needs_attention"])

    def test_ownership_map_complete(self) -> None:
        self.assertEqual(
            set(SECTION_OWNERSHIP_HREF_V1),
            {"health", "decisions", "observations", "carts", "communication"},
        )


if __name__ == "__main__":
    unittest.main()
