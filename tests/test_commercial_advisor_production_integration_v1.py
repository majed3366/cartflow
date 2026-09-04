# -*- coding: utf-8 -*-
"""Commercial Advisor Production Integration V1 — CDA on Merchant UI gates."""
from __future__ import annotations

import os
import unittest


ROOT = os.path.join(os.path.dirname(__file__), "..")


class ProductionCdaIntegrationTests(unittest.TestCase):
    def test_production_cda_assets_exist(self) -> None:
        for rel in (
            "static/commercial_decision_arc_production_v1.js",
            "static/commercial_decision_arc_production_v1.css",
        ):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_home_wires_cda(self) -> None:
        home = open(
            os.path.join(ROOT, "static/merchant_ui_v2_home.js"), encoding="utf-8"
        ).read()
        self.assertIn("CartFlowCommercialDecisionArcV1", home)
        self.assertIn("data-cf2-cda", home)
        self.assertIn("insufficient_evidence", home)
        self.assertIn("commercial-opportunity-layer-v1", home)
        self.assertNotIn("SIMULATION_TRUTH", home)

    def test_workspace_wires_cda(self) -> None:
        ws = open(
            os.path.join(ROOT, "static/merchant_ui_v2_workspace.js"), encoding="utf-8"
        ).read()
        self.assertIn("CartFlowCommercialDecisionArcV1", ws)
        self.assertIn("data-cf2-cda", ws)
        self.assertIn("recheck_due", ws)
        self.assertIn("commercial-opportunity-workspace-v1", ws)

    def test_shell_loads_cda_assets(self) -> None:
        html = open(
            os.path.join(ROOT, "templates/merchant_app_v2.html"), encoding="utf-8"
        ).read()
        self.assertIn("commercial_decision_arc_production_v1.css", html)
        self.assertIn("commercial_decision_arc_production_v1.js", html)
        self.assertIn("cda1", html)

    def test_cda_js_has_no_lab_missions(self) -> None:
        js = open(
            os.path.join(ROOT, "static/commercial_decision_arc_production_v1.js"),
            encoding="utf-8",
        ).read()
        self.assertIn("commercial-decision-arc-v1", js)
        self.assertIn("cf-cda__organism", js)
        self.assertNotIn("SIMULATION_TRUTH", js)
        self.assertNotIn("rrv_sim", js)
        self.assertNotIn("progress-bar", js.lower())
        self.assertNotIn("webgl", js.lower())

    def test_col_compose_untouched_markers(self) -> None:
        """Intelligence freeze: compose still owns shipping_friction contract."""
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        pkg = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": "cda_prod_int",
                "merchant_reason_counts_week": {
                    "shipping": 14,
                    "price": 7,
                    "thinking": 4,
                },
            }
        )
        self.assertFalse(pkg.get("empty"))
        self.assertEqual(pkg["primary"]["family"], "shipping_friction")


if __name__ == "__main__":
    unittest.main()
