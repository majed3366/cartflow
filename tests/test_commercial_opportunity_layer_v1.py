# -*- coding: utf-8 -*-
"""Commercial Opportunity Layer V1 — gates + failure tests."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from services.commercial_opportunity_layer_v1.attach_v1 import (
    attach_commercial_opportunity_layer_to_summary_v1,
)
from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    FORBIDDEN_SIM_MARKERS,
    TRUTH_PRODUCTION_PARTIAL,
    TRUTH_PRODUCTION_READY,
    package_has_simulation_leak,
)
from services.commercial_opportunity_layer_v1.flag_v1 import (
    ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1,
    commercial_opportunity_layer_v1_enabled,
)
from services.commercial_opportunity_layer_v1.truth_gate_v1 import (
    classify_hesitation_truth_v1,
)


def _ready_counts() -> dict:
    return {"shipping": 12, "price": 5, "thinking": 3}


class FlagTests(unittest.TestCase):
    def test_flag_default_off(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1}
        self.assertFalse(commercial_opportunity_layer_v1_enabled(environ=env))

    def test_flag_on(self) -> None:
        self.assertTrue(
            commercial_opportunity_layer_v1_enabled(
                environ={ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1: "1"}
            )
        )


class TruthGateTests(unittest.TestCase):
    def test_ready_vs_partial_vs_insufficient(self) -> None:
        self.assertEqual(
            classify_hesitation_truth_v1(total=20, top_count=12, share=0.6),
            TRUTH_PRODUCTION_READY,
        )
        self.assertEqual(
            classify_hesitation_truth_v1(total=5, top_count=3, share=0.6),
            TRUTH_PRODUCTION_PARTIAL,
        )
        self.assertEqual(
            classify_hesitation_truth_v1(total=2, top_count=2, share=1.0),
            "INSUFFICIENT",
        )

    def test_simulation_class(self) -> None:
        self.assertEqual(
            classify_hesitation_truth_v1(
                total=20, top_count=12, share=0.6, simulation=True
            ),
            "SIMULATION_ONLY",
        )


class ComposeTests(unittest.TestCase):
    def test_primary_shipping_from_production_counts(self) -> None:
        pkg = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": "demo",
                "merchant_reason_counts_week": _ready_counts(),
            }
        )
        self.assertTrue(pkg["ok"])
        self.assertFalse(pkg["empty"])
        self.assertIsNotNone(pkg["primary"])
        assert pkg["primary"] is not None
        self.assertEqual(pkg["primary"]["truth_class"], TRUTH_PRODUCTION_READY)
        self.assertEqual(pkg["primary"]["family"], "shipping_friction")
        self.assertTrue(pkg["primary"]["measure_ar"])
        self.assertTrue(pkg["primary"]["recheck_ar"])
        self.assertNotIn("إيراد مضمون", pkg["primary"]["why_ar"])
        self.assertTrue(pkg["primary"]["decision_contract_ar"]["dont_ar"])
        self.assertLessEqual(len(pkg["secondaries"]), 2)
        self.assertEqual(pkg["cost"]["ai_calls"], 0)
        self.assertEqual(pkg["cost"]["external_api_calls"], 0)
        self.assertEqual(pkg["truth_boundary"], "PRODUCTION_TRUTH")

    def test_empty_when_no_evidence(self) -> None:
        pkg = compose_commercial_opportunity_layer_v1({"store_slug": "demo"})
        self.assertTrue(pkg["empty"])
        self.assertIsNone(pkg["primary"])
        self.assertEqual(pkg["secondaries"], [])

    def test_weak_evidence_no_overconfident_primary(self) -> None:
        pkg = compose_commercial_opportunity_layer_v1(
            {"merchant_reason_counts_week": {"shipping": 1, "price": 1}}
        )
        self.assertTrue(pkg["empty"])

    def test_simulation_summary_suppresses(self) -> None:
        pkg = compose_commercial_opportunity_layer_v1(
            {
                "truth_boundary": "SIMULATION_TRUTH",
                "merchant_reason_counts_week": _ready_counts(),
            }
        )
        self.assertTrue(pkg["empty"])

    def test_no_simulation_marker_in_package(self) -> None:
        pkg = compose_commercial_opportunity_layer_v1(
            {"merchant_reason_counts_week": _ready_counts()}
        )
        blob = str(pkg)
        for m in FORBIDDEN_SIM_MARKERS:
            if m in ("production_truth_present",):
                continue
            self.assertNotIn("SIMULATION_TRUTH", blob)
            self.assertNotIn("rrv_sim_store", blob)
        self.assertFalse(package_has_simulation_leak(pkg))

    def test_communication_opportunity(self) -> None:
        pkg = compose_commercial_opportunity_layer_v1(
            {
                "home_teaser_inputs_v1": {"health": {"no_phone": 4}},
            }
        )
        self.assertFalse(pkg["empty"])
        assert pkg["primary"] is not None
        self.assertEqual(pkg["primary"]["family"], "communication_followup")

    def test_partial_constrained_wording(self) -> None:
        pkg = compose_commercial_opportunity_layer_v1(
            {"merchant_reason_counts_week": {"shipping": 3, "price": 2}}
        )
        # total=5, top=3 → PARTIAL may render
        if not pkg["empty"]:
            assert pkg["primary"] is not None
            self.assertEqual(pkg["primary"]["truth_class"], TRUTH_PRODUCTION_PARTIAL)
            self.assertIn("أدلة جزئية", pkg["primary"]["title_ar"])

    def test_malformed_fail_closed_via_attach(self) -> None:
        summary: dict = {"store_slug": "x"}
        with mock.patch(
            "services.commercial_opportunity_layer_v1.attach_v1.compose_commercial_opportunity_layer_v1",
            side_effect=RuntimeError("boom"),
        ):
            out = attach_commercial_opportunity_layer_to_summary_v1(
                summary,
                environ={ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1: "1"},
            )
        self.assertFalse(out["commercial_opportunity_layer_v1"]["ok"])
        self.assertTrue(out["commercial_opportunity_layer_v1"]["empty"])


class AttachFlagTests(unittest.TestCase):
    def test_flag_off_leaves_summary_without_col(self) -> None:
        summary = {
            "store_slug": "demo",
            "merchant_reason_counts_week": _ready_counts(),
            "commercial_opportunity_layer_v1": {"stale": True},
        }
        out = attach_commercial_opportunity_layer_to_summary_v1(
            summary, environ={ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1: "0"}
        )
        self.assertNotIn("commercial_opportunity_layer_v1", out)

    def test_flag_on_attaches(self) -> None:
        summary = {
            "store_slug": "demo",
            "merchant_reason_counts_week": _ready_counts(),
        }
        out = attach_commercial_opportunity_layer_to_summary_v1(
            summary, environ={ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1: "1"}
        )
        self.assertIn("commercial_opportunity_layer_v1", out)
        self.assertFalse(out["commercial_opportunity_layer_v1"]["empty"])

    def test_col_survives_when_hes_path_imports(self) -> None:
        """COL attach is wired after OGL inside HES attach (smoke import only)."""
        from services.home_executive_summary_v1 import compose_v1 as hes_mod

        src = open(hes_mod.__file__, encoding="utf-8").read()
        self.assertIn("attach_commercial_opportunity_layer_to_summary_v1", src)


class StaticAssetTests(unittest.TestCase):
    def test_home_js_has_col_markers(self) -> None:
        path = os.path.join(
            os.path.dirname(__file__), "..", "static", "merchant_ui_v2_home.js"
        )
        text = open(path, encoding="utf-8").read()
        self.assertIn("commercial-opportunity-layer-v1", text)
        self.assertIn("أهم فرصة تجارية الآن", text)
        self.assertIn("لماذا الآن؟", text)
        self.assertIn("الحركة الآن", text)
        self.assertIn("عرض الدليل", text)
        self.assertIn("data-cf2-col-refine", text)

    def test_workspace_js_has_compressed_decision(self) -> None:
        path = os.path.join(
            os.path.dirname(__file__), "..", "static", "merchant_ui_v2_workspace.js"
        )
        text = open(path, encoding="utf-8").read()
        self.assertIn("commercial-opportunity-workspace-v1", text)
        self.assertIn("لماذا الآن؟", text)
        self.assertIn("لا تفعل هذا", text)
        self.assertIn("cf2-col-ws__unit", text)

    def test_no_preview_import_in_home(self) -> None:
        path = os.path.join(
            os.path.dirname(__file__), "..", "static", "merchant_ui_v2_home.js"
        )
        text = open(path, encoding="utf-8").read()
        self.assertNotIn("SIMULATION_TRUTH", text)
        self.assertNotIn("commercial-intelligence-preview", text)


if __name__ == "__main__":
    unittest.main()
