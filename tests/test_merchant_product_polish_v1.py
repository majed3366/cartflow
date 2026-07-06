# -*- coding: utf-8 -*-
"""Product Polish V1 — unified merchant presentation contract."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_POLISH_CSS = (_ROOT / "static" / "merchant_product_polish_v1.css").read_text(encoding="utf-8")
_APP_JS = (_ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")
_HOME_JS = (_ROOT / "static" / "merchant_home_experience.js").read_text(encoding="utf-8")
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


class MerchantProductPolishV1Tests(unittest.TestCase):
    def test_dashboard_shell_loads_polish_css(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_product_polish_v1.css", html)

    def test_unified_hero_and_grouping_in_template(self) -> None:
        self.assertIn('id="pagePurpose"', _TEMPLATE)
        self.assertIn("ma-page-hero__purpose", _TEMPLATE)
        self.assertIn('id="ma-carts-groups-v2"', _TEMPLATE)
        self.assertIn('data-ma-group="all"', _TEMPLATE)
        self.assertIn('id="ma-carts-hero"', _TEMPLATE)

    def test_page_purpose_map_in_router(self) -> None:
        self.assertIn("PAGE_PURPOSE", _APP_JS)
        self.assertIn("data-ma-page", _APP_JS)
        self.assertIn("whatsapp:", _APP_JS)

    def test_home_knowledge_section_head(self) -> None:
        self.assertIn("ma-page-section--knowledge", _HOME_JS)
        self.assertIn("ma-section-head__purpose", _HOME_JS)
        self.assertIn("v2-hero-purpose", _HOME_JS)

    def test_polish_css_tokens_and_card_family(self) -> None:
        for token in (
            "--ma-type-xl",
            "--ma-card-radius",
            ".ma-page-hero__purpose",
            ".ma-cart-group",
            ".ma-cart-group__title",
        ):
            self.assertIn(token, _POLISH_CSS, msg=f"missing {token}")


if __name__ == "__main__":
    unittest.main()
