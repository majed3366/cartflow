# -*- coding: utf-8 -*-
"""Gate 1-B — Executive Summary Composition."""
from __future__ import annotations

import unittest

from services.home_executive_summary_v1.compose_v1 import (
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
        # Diagnosis Language V1 — calm store is evidence-backed, not a queue report.
        self.assertTrue(
            "مستقر" in (health.get("status_ar") or "")
            or "دون مشكلة تشغيلية" in health["summary_ar"]
            or "بثقة كافية" in health["summary_ar"]
        )
        self.assertTrue(health.get("diagnosis_ar"))
        self.assertFalse(str(health["diagnosis_ar"]).startswith("راجع"))
        self.assertEqual(health["view_details_href"], "#workspace")
        self.assertNotIn("count", health)

    def test_quiet_store_omits_count(self) -> None:
        hes = build_home_executive_summary_v1(
            {},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        health = next(s for s in hes["sections"] if s["id"] == "health")
        self.assertNotIn("count", health)
        self.assertEqual(health["title_ar"], "حالة المتجر")

    def test_carts_and_communication_executive_summaries(self) -> None:
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
        health = next(s for s in hes["sections"] if s["id"] == "health")
        # Diagnosis Language V1 — cause + recommendation, not queue counts.
        self.assertTrue(carts.get("diagnosis_ar"))
        self.assertFalse(str(carts["diagnosis_ar"]).startswith("راجع"))
        self.assertFalse(str(carts["summary_ar"])[:1].isdigit())
        self.assertIn("رقم الهاتف", comm.get("diagnosis_ar") or "")
        self.assertNotIn("بلا رقم", carts["summary_ar"])
        self.assertNotIn("بلا رقم", comm["summary_ar"])
        self.assertNotEqual(health["summary_ar"], carts["summary_ar"])
        self.assertNotIn("عدّاد", health["summary_ar"])
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
        self.assertIn("بثقة كافية", dec["diagnosis_ar"])
        self.assertTrue(dec["empty"])
        self.assertEqual(dec["view_details_href"], "#workspace")
        self.assertFalse(str(dec["diagnosis_ar"]).startswith("راجع"))

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
        self.assertIn("شحن", dec["diagnosis_ar"])
        self.assertFalse(str(dec["diagnosis_ar"]).startswith("راجع"))
        self.assertFalse(dec["empty"])

    def test_observation_constitutional_empty_omitted(self) -> None:
        """Constitution §9 — omit empty product slot; keep Health + Decisions."""
        hes = build_home_executive_summary_v1(
            {},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        ids = [s["id"] for s in hes["sections"]]
        self.assertNotIn("observations", ids)
        self.assertIn("health", ids)
        self.assertIn("decisions", ids)
        self.assertEqual(hes["title_ar"], "ماذا يجب أن أعرف الآن عن متجري؟")
        self.assertEqual(hes.get("eyebrow_ar") or "", "")
        self.assertEqual(hes.get("lede_ar") or "", "")

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
        self.assertTrue(obs.get("diagnosis_ar"))
        self.assertIn("نية شراء", obs["diagnosis_ar"])
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
            {
                "health",
                "decisions",
                "observations",
                "situations",
                "carts",
                "communication",
            },
        )
        self.assertEqual(SECTION_OWNERSHIP_HREF_V1["health"], "#workspace")

    def test_health_contact_blocked_routes_to_communication(self) -> None:
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
        self.assertEqual(health["view_details_href"], "#communication")

    def test_health_disconnected_routes_to_settings(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "home_teaser_inputs_v1": {
                    "schema": "home_teaser_inputs_v1",
                    "health": {"store_connected": False},
                    "decisions": {"count": 0},
                    "observations": {"count": 0},
                    "carts": {},
                    "communication": {},
                }
            },
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        health = next(s for s in hes["sections"] if s["id"] == "health")
        self.assertEqual(health["view_details_href"], "#settings")

    def test_no_bare_count_badges_on_home(self) -> None:
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
        for sec in hes["sections"]:
            self.assertNotIn("count", sec)
            self.assertNotEqual(sec.get("status_ar"), "القرار الأهم")
            self.assertNotEqual(sec.get("status_ar"), "منتج")
            self.assertNotEqual(sec.get("status_ar"), "مكتمل اليوم")


if __name__ == "__main__":
    unittest.main()
