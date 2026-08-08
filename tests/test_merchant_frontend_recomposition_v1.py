# -*- coding: utf-8 -*-
"""Merchant Frontend Recomposition V1 — frame + DS contract (replaces PDS closure CSS stack)."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")

_FRAME_STACK = (
    "merchant_frame_v1.css",
    "merchant_ds_v1.css",
    "merchant_grammar_v1.css",
    "cf_signature_primitives_v1.css",
)

_OBSOLETE_OVERRIDE_STACK = (
    "platform_shell_visual_assimilation_v1.css",
    "merchant_shell_identity_v1.css",
    "merchant_responsive_layout_v1.css",
    "merchant_workspace_expansion_v1.css",
    "merchant_visual_identity_v1.css",
    "merchant_pds_compliance_v1.css",
    "merchant_typography_certification_v1.css",
    "merchant_card_system_v1.css",
    "merchant_icon_language_v1.css",
    "merchant_spacing_certification_v1.css",
)


class MerchantFrontendRecompositionV1Tests(unittest.TestCase):
    def test_dashboard_loads_frame_design_system_stack(self) -> None:
        html = TestClient(app).get("/dashboard").text
        for name in _FRAME_STACK:
            self.assertIn(name, html, msg=f"missing {name}")

    def test_obsolete_override_stack_not_linked(self) -> None:
        html = TestClient(app).get("/dashboard").text
        for name in _OBSOLETE_OVERRIDE_STACK:
            self.assertNotIn(name, html, msg=f"obsolete override still linked: {name}")

    def test_body_has_frame_v1_marker(self) -> None:
        self.assertIn('data-cf-frame="v1"', _TEMPLATE)
        self.assertIn('data-cf-merchant-app="1"', _TEMPLATE)
        self.assertIn("cf-pds-closure", _TEMPLATE)

    def test_shell_uses_cf_rail_and_stage(self) -> None:
        self.assertIn('class="cf-rail ma-context-sidebar sidebar"', _TEMPLATE)
        self.assertIn('class="cf-stage ma-dashboard-frame ma-app-shell"', _TEMPLATE)
        self.assertIn("cf-rail__primary", _TEMPLATE)
        self.assertIn("cf-topbar", _TEMPLATE)

    def test_primary_nav_lives_in_rail_not_mobile_squeezed_header(self) -> None:
        self.assertIn('class="cf-rail__primary"', _TEMPLATE)
        self.assertIn("ma-gtb-section", _TEMPLATE)
        self.assertIn("cf-rail__account", _TEMPLATE)

    def test_frame_css_tokens(self) -> None:
        css = (_ROOT / "static" / "merchant_frame_v1.css").read_text(encoding="utf-8")
        for token in (
            "--cf-rail-w",
            "--cf-navy",
            "--cf-teal",
            ".cf-rail",
            ".cf-stage",
            ".cf-topbar",
            "max-width: none",
        ):
            self.assertIn(token, css)

    def test_ds_css_components(self) -> None:
        css = (_ROOT / "static" / "merchant_ds_v1.css").read_text(encoding="utf-8")
        for token in (
            ".cf-btn",
            ".cf-btn--secondary",
            ".cf-tab",
            ".cf-badge",
            ".cf-card",
            ".cf-panel",
            ".cf-empty",
            ".cf-skeleton",
        ):
            self.assertIn(token, css)

    def test_frame_styles_load_after_legacy_page_css(self) -> None:
        app_idx = _TEMPLATE.index("merchant_app.css")
        frame_idx = _TEMPLATE.index("merchant_frame_v1.css")
        self.assertGreater(frame_idx, app_idx)


if __name__ == "__main__":
    unittest.main()
