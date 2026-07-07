# -*- coding: utf-8 -*-
"""PDS Final Closure V1 — visual identity certification tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")

_CLOSURE_FILES = (
    "merchant_shell_identity_v1.css",
    "merchant_card_system_v1.css",
    "merchant_icon_language_v1.css",
    "merchant_spacing_certification_v1.css",
)


class VisualIdentityFinalClosureV1Tests(unittest.TestCase):
    def test_dashboard_loads_all_pds_closure_stylesheets(self) -> None:
        html = TestClient(app).get("/dashboard").text
        for name in _CLOSURE_FILES:
            self.assertIn(name, html, msg=f"missing {name}")

    def test_body_has_pds_closure_class(self) -> None:
        self.assertIn('class="cf-pds-closure"', _TEMPLATE)
        self.assertIn('data-cf-merchant-app="1"', _TEMPLATE)

    def test_shell_identity_tokens(self) -> None:
        css = (_ROOT / "static" / "merchant_shell_identity_v1.css").read_text(encoding="utf-8")
        for token in (
            "--cfpds-shell-bg",
            ".ma-global-topbar",
            ".ma-context-sidebar",
            ".nav-item.active",
            ".ma-scrim",
        ):
            self.assertIn(token, css)

    def test_card_system_tokens(self) -> None:
        css = (_ROOT / "static" / "merchant_card_system_v1.css").read_text(encoding="utf-8")
        for token in (
            "--cfpds-card-radius",
            ".setting-card",
            ".ma-fw-card",
            ".ma-plan-card",
            ".card",
        ):
            self.assertIn(token, css)

    def test_icon_language_tokens(self) -> None:
        css = (_ROOT / "static" / "merchant_icon_language_v1.css").read_text(encoding="utf-8")
        for token in (
            "--cfpds-icon-md",
            ".empty-icon",
            ".wa-pill",
            ".cf-status-dot",
        ):
            self.assertIn(token, css)

    def test_spacing_certification_tokens(self) -> None:
        css = (_ROOT / "static" / "merchant_spacing_certification_v1.css").read_text(
            encoding="utf-8"
        )
        for token in (
            "--cfpds-page-gutter",
            "--cfpds-section-gap",
            ".empty-state",
            "#page-carts",
        ):
            self.assertIn(token, css)

    def test_closure_styles_load_after_typography_lock(self) -> None:
        typo_idx = _TEMPLATE.index("merchant_typography_certification_v1.css")
        shell_idx = _TEMPLATE.index("merchant_shell_identity_v1.css")
        self.assertGreater(shell_idx, typo_idx)


if __name__ == "__main__":
    unittest.main()
