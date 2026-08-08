# -*- coding: utf-8 -*-
"""Merchant Experience Rebuild V1 — Home + Decision Workspace contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "home_executive_summary_v1.js").read_text(encoding="utf-8")
CARD_JS = (ROOT / "static" / "cart_workspace_decision_card_v1.js").read_text(
    encoding="utf-8"
)
GRID_JS = (ROOT / "static" / "cart_workspace_grid_v1.js").read_text(encoding="utf-8")


class ExperienceRebuildContracts(unittest.TestCase):
    def test_new_experience_css_linked(self) -> None:
        self.assertIn("merchant_experience_home_v1.css", TEMPLATE)
        self.assertIn("merchant_experience_workspace_v1.css", TEMPLATE)
        self.assertIn("merchant_frame_v1.css", TEMPLATE)
        self.assertIn("merchant_ds_v1.css", TEMPLATE)

    def test_dwa_override_stack_unlinked(self) -> None:
        self.assertNotIn("decision_workspace_visual_assimilation_v1.css", TEMPLATE)

    def test_home_composition_not_equal_cards(self) -> None:
        self.assertIn("cx-home", HOME_JS)
        self.assertIn("cx-insight--primary", HOME_JS)
        self.assertIn("cx-home__decision", HOME_JS)
        self.assertIn("cx-home__evidence", HOME_JS)
        self.assertIn("cx-home__secondary", HOME_JS)
        self.assertIn(">عرض التفاصيل ←</a>", HOME_JS)
        self.assertNotIn('class="hes-section', HOME_JS)

    def test_workspace_reasoning_object(self) -> None:
        self.assertIn("cx-decision", CARD_JS)
        self.assertIn("cx-beat--evidence", CARD_JS)
        self.assertIn("cx-beat--understanding", CARD_JS)
        self.assertIn("cx-beat--decision", CARD_JS)
        self.assertIn("cx-beat--action", CARD_JS)
        self.assertIn("data-cf-evidence", CARD_JS)
        self.assertIn("cx-ws", GRID_JS)
        self.assertIn("cx-ws__primary", GRID_JS)
        self.assertIn("living-route", GRID_JS)

    def test_assets_exist(self) -> None:
        for rel in (
            "static/merchant_experience_home_v1.css",
            "static/merchant_experience_workspace_v1.css",
            "static/home_executive_summary_v1.js",
            "static/cart_workspace_decision_card_v1.js",
            "static/cart_workspace_grid_v1.js",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
