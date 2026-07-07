# -*- coding: utf-8 -*-
"""Currency Rendering Certification V1 — atomic SAR display tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_CURRENCY_CSS = (
    _ROOT / "static" / "merchant_currency_certification_v1.css"
).read_text(encoding="utf-8")
_FORMAT_JS = (_ROOT / "static" / "merchant_pds_format_v1.js").read_text(encoding="utf-8")


class CurrencyCertificationV1Tests(unittest.TestCase):
    def test_dashboard_loads_currency_certification_stylesheet(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_currency_certification_v1.css", html)

    def test_currency_styles_load_after_layout_certification(self) -> None:
        layout_idx = _TEMPLATE.index("merchant_responsive_layout_v1.css")
        currency_idx = _TEMPLATE.index("merchant_currency_certification_v1.css")
        self.assertGreater(currency_idx, layout_idx)

    def test_currency_css_atomic_rules(self) -> None:
        for token in (
            ".cf-currency-atom",
            "white-space: nowrap",
            "unicode-bidi: isolate",
            ".camt",
            ".kpi-value",
        ):
            self.assertIn(token, _CURRENCY_CSS)

    def test_format_js_nbsp_and_html_helper(self) -> None:
        self.assertIn("SAR_SUFFIX", _FORMAT_JS)
        self.assertIn("\\u00a0ر.س", _FORMAT_JS)
        self.assertIn("formatMerchantSarHtml", _FORMAT_JS)
        self.assertIn('data-cf-currency="1"', _FORMAT_JS)

    def test_template_currency_atoms(self) -> None:
        self.assertIn('class="camt cf-currency-atom"', _TEMPLATE)
        self.assertIn("&#160;ر.س", _TEMPLATE)
        self.assertNotIn("}} ر</div>", _TEMPLATE)


if __name__ == "__main__":
    unittest.main()
