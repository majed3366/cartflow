# -*- coding: utf-8 -*-
"""Production Integration V1.1 — composition fit gates."""
from __future__ import annotations

import os
import unittest


ROOT = os.path.join(os.path.dirname(__file__), "..")


class CompositionFitV11Tests(unittest.TestCase):
    def test_secondary_compression_markers(self) -> None:
        home = open(
            os.path.join(ROOT, "static/merchant_ui_v2_home.js"), encoding="utf-8"
        ).read()
        self.assertIn("cf2-col__secondary--signal", home)
        self.assertIn("data-cf2-col-compress", home)
        self.assertIn("cf2-col__sec-line", home)
        self.assertIn("CartFlowCommercialDecisionArcV1", home)

    def test_cda_css_fit_constraints(self) -> None:
        css = open(
            os.path.join(ROOT, "static/commercial_decision_arc_production_v1.css"),
            encoding="utf-8",
        ).read()
        self.assertIn("max-width: 40rem", css)
        self.assertIn("Composition Fit", css)
        self.assertNotIn("webgl", css.lower())

    def test_cachebust_fit1(self) -> None:
        html = open(
            os.path.join(ROOT, "templates/merchant_app_v2.html"), encoding="utf-8"
        ).read()
        self.assertIn("cda1-fit1", html)

    def test_intelligence_frozen(self) -> None:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        pkg = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": "fit11",
                "merchant_reason_counts_week": {
                    "shipping": 14,
                    "price": 7,
                    "thinking": 4,
                },
            }
        )
        self.assertEqual(pkg["primary"]["family"], "shipping_friction")


if __name__ == "__main__":
    unittest.main()
