# -*- coding: utf-8 -*-
"""Responsive Layout Certification V1 — layout family tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_LAYOUT_CSS = (_ROOT / "static" / "merchant_responsive_layout_v1.css").read_text(encoding="utf-8")


class ResponsiveLayoutCertificationV1Tests(unittest.TestCase):
    def test_dashboard_loads_layout_certification_stylesheet(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_responsive_layout_v1.css", html)

    def test_layout_styles_load_after_pds_closure_stack(self) -> None:
        spacing_idx = _TEMPLATE.index("merchant_spacing_certification_v1.css")
        layout_idx = _TEMPLATE.index("merchant_responsive_layout_v1.css")
        self.assertGreater(layout_idx, spacing_idx)

    def test_family_a_tokens_and_selectors(self) -> None:
        for token in (
            "--cfrl-family-a-max",
            'data-ma-page="home"] #page-home',
            'data-ma-page="home-month"] #page-home-month',
            'data-ma-page="home-setup"] #page-home-setup',
        ):
            self.assertIn(token, _LAYOUT_CSS)

    def test_family_b_full_width_selectors(self) -> None:
        for token in (
            'data-ma-page="carts"] #page-carts',
            'data-ma-page="messages"] #page-messages',
            'data-ma-page="reasons"] #page-reasons',
            'data-ma-page="followup"] #page-followup',
            "max-width: none",
        ):
            self.assertIn(token, _LAYOUT_CSS)

    def test_family_c_comfort_width_selectors(self) -> None:
        for token in (
            "--cfrl-family-c-max",
            'data-ma-page="whatsapp"] #page-whatsapp',
            'data-ma-page="widget"] #page-widget',
            'data-ma-page="plans"] #page-plans',
        ):
            self.assertIn(token, _LAYOUT_CSS)

    def test_desktop_only_media_query(self) -> None:
        self.assertIn("@media (min-width: 1024px)", _LAYOUT_CSS)
        self.assertNotIn("@media (max-width:", _LAYOUT_CSS)


if __name__ == "__main__":
    unittest.main()
