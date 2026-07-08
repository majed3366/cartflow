# -*- coding: utf-8 -*-
"""Currency Rendering Certification V1 — atomic SR display tests."""
from __future__ import annotations

import re
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
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_MI_CARTS_JS = (_ROOT / "static" / "merchant_intelligence_carts_v1.js").read_text(
    encoding="utf-8"
)
_PLANS_PY = (_ROOT / "services" / "merchant_plans_catalog_v1.py").read_text(
    encoding="utf-8"
)

_REJECTED = ("ر.س", "ريال سعودي", "&#160;ر.س", "\\u00a0ر.س")
_EXPECTED_SR = ("\\u00a0SR", "&#160;SR", " SR")


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

    def test_format_js_sr_suffix_and_html_helper(self) -> None:
        self.assertIn("SAR_SUFFIX", _FORMAT_JS)
        self.assertIn("\\u00a0SR", _FORMAT_JS)
        self.assertIn("formatMerchantSarHtml", _FORMAT_JS)
        self.assertIn('data-cf-currency="1"', _FORMAT_JS)
        for bad in _REJECTED:
            self.assertNotIn(bad, _FORMAT_JS, msg=f"rejected token {bad!r} in format JS")

    def test_certified_compact_format_contract(self) -> None:
        self.assertIn('toLocaleString("en-US")', _FORMAT_JS)
        self.assertIn("+ SAR_SUFFIX", _FORMAT_JS)
        self.assertIn("\\u00a0SR", _FORMAT_JS)

    def test_template_currency_atoms_use_sr(self) -> None:
        self.assertIn('class="camt cf-currency-atom"', _TEMPLATE)
        self.assertIn("&#160;SR", _TEMPLATE)
        self.assertNotIn("}} ر</div>", _TEMPLATE)
        for bad in ("ر.س", "&#160;ر.س", "ريال سعودي"):
            self.assertNotIn(bad, _TEMPLATE, msg=f"rejected token {bad!r} in template")

    def test_lazy_and_mi_fallbacks_use_sr(self) -> None:
        for src in (_LAZY_JS, _MI_CARTS_JS):
            self.assertIn("\\u00a0SR", src)
            self.assertNotIn("\\u00a0ر.س", src)
            self.assertNotIn('+ " ر.س"', src)

    def test_plans_catalog_price_labels_use_sr(self) -> None:
        self.assertIn("SR / شهر", _PLANS_PY)
        self.assertIn("SR / سنة", _PLANS_PY)
        self.assertNotIn("ر.س", _PLANS_PY)

    def test_no_split_arabic_currency_suffix_in_merchant_sources(self) -> None:
        combined = _TEMPLATE + _FORMAT_JS + _LAZY_JS + _MI_CARTS_JS + _PLANS_PY
        self.assertNotIn("ر.س", combined)
        self.assertIsNone(re.search(r">\s*ر\s*<", combined))


if __name__ == "__main__":
    unittest.main()
