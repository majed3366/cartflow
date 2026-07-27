# -*- coding: utf-8 -*-
"""Home Executive Summary V1 + Home Stabilization Sprint V1."""
from __future__ import annotations

import unittest

from services.home_executive_summary_v1.compose_v1 import (
    OBS_EMPTY_AR,
    SECTION_IDS_V1,
    attach_home_executive_summary_to_summary_v1,
    build_home_executive_summary_v1,
)
from services.observation_foundation_v1.merchant_findings_v1 import (
    attach_observation_reality_validation_to_summary_v1,
    build_observation_reality_validation_v1,
    project_merchant_observation_findings_v1,
)
from services.observation_foundation_v1.product_entity_resolve_v1 import (
    is_banned_product_key_v1,
    is_real_product_display_name_v1,
)
class HomeExecutiveSummaryV1Tests(unittest.TestCase):
    def test_bans_demo_product_keys(self) -> None:
        self.assertTrue(is_banned_product_key_v1("DEMO-PERFUME"))
        self.assertTrue(is_banned_product_key_v1("orv-s1"))
        self.assertTrue(is_banned_product_key_v1("demo"))

    def test_bans_placeholder_product_display_name(self) -> None:
        self.assertFalse(is_real_product_display_name_v1("هذا المنتج"))
        self.assertFalse(is_real_product_display_name_v1("this product"))

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
        self.assertNotIn("هذا المنتج", findings[0]["statement_ar"])
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

    def test_empty_store_slug_never_falls_back_to_demo(self) -> None:
        out: dict = {}
        attach_observation_reality_validation_to_summary_v1(
            out,
            "",
            environ={
                "CARTFLOW_OBSERVATION_FOUNDATION_V1": "1",
                "CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1": "1",
                "CARTFLOW_ORV_APPROVED_MASS_V1": "0",
            },
        )
        pkg = out["observation_reality_validation_v1"]
        self.assertEqual(pkg["store_slug"], "")
        self.assertEqual(pkg["findings"], [])
        self.assertEqual(pkg["empty_state_ar"], OBS_EMPTY_AR)
        self.assertNotEqual(pkg.get("mass_source"), "demo")

    def test_executive_summary_five_sections_and_slim_orv(self) -> None:
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
                    },
                    "carts": {
                        "durable_cart_count": 3,
                        "operational_truth": {
                            "abandoned_carts": 3,
                            "has_durable_carts": True,
                        },
                    },
                    "communication": {
                        "operational_truth": {
                            "mock_whatsapp_sent": 2,
                            "recovery_schedules": 1,
                            "has_communication_activity": True,
                        },
                    },
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
        # Constitution V2: Health + Decisions always; product/carts/comms only with signal.
        self.assertEqual(ids[0], "health")
        self.assertEqual(ids[1], "decisions")
        self.assertIn("observations", ids)
        self.assertIn("carts", ids)
        for sid in ids:
            self.assertIn(sid, SECTION_IDS_V1)
        for sec in hes["sections"]:
            self.assertTrue(sec.get("summary_ar"))
            self.assertTrue(sec.get("view_details_href"))
            self.assertNotIn("count", sec)
        obs = next(s for s in hes["sections"] if s["id"] == "observations")
        self.assertIn("زيت الورد", obs["summary_ar"])
        self.assertEqual(obs["view_details_href"], "#workspace")
        self.assertEqual(obs.get("findings_preview"), [])
        carts = next(s for s in hes["sections"] if s["id"] == "carts")
        self.assertFalse(str(carts["summary_ar"])[:1].isdigit())
        self.assertEqual(hes["title_ar"], "ماذا يجب أن أعرف الآن عن متجري؟")
        teasers = out["home_teaser_inputs_v1"]
        self.assertEqual(teasers["schema"], "home_teaser_inputs_v1")
        self.assertEqual(teasers["observations"]["count"], 1)
        # Gate 1 — ORV detail must not ride Home transport (stub only).
        slim = out["observation_reality_validation_v1"]
        self.assertEqual(slim["findings"], [])
        self.assertTrue(slim.get("stripped_for_home_slim_transport"))
        self.assertEqual(hes["governance"]["sprint"], "home_stabilization_v1")

    def test_observation_empty_omitted_from_paint(self) -> None:
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
        self.assertNotIn(
            "observations", [s["id"] for s in hes["sections"]]
        )
        # Stub / empty-state copy still used by ORV home strip.
        self.assertEqual(OBS_EMPTY_AR, "لا يوجد منتج يستحق انتباهك الآن.")

    def test_surface_mode_set_even_when_attach_builds_empty_shell(self) -> None:
        out = attach_home_executive_summary_to_summary_v1(
            {},
            environ={"CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1": "1"},
        )
        self.assertEqual(out["home_surface_mode"], "executive_summary_v1")
        self.assertTrue(out["home_executive_summary_v1"]["enabled"])


if __name__ == "__main__":
    unittest.main()
