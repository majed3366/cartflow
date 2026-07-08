# -*- coding: utf-8 -*-
"""Currency Rendering Standardization V2 — single SR prefix formatter tests."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.merchant_pds_format_v1 import format_merchant_sar, format_merchant_sar_html

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
_VIP_JS = (_ROOT / "static" / "merchant_vip_automation_ui.js").read_text(encoding="utf-8")
_PLANS_PY = (_ROOT / "services" / "merchant_plans_catalog_v1.py").read_text(
    encoding="utf-8"
)

_REJECTED = ("ر.س", "ريال سعودي", "&#160;ر.س", "\\u00a0ر.س", "&#160;SR", "\\u00a0SR")
_FORBIDDEN_SUFFIX = ('+ " SR"', '+ "ر.س"', "\\u00a0SR", "toLocaleString(\"en-US\") + \" ر\"")


class CurrencyCertificationV2Tests(unittest.TestCase):
    def test_format_merchant_sar_python_examples(self) -> None:
        self.assertEqual(format_merchant_sar(449), "SR 449")
        self.assertEqual(format_merchant_sar(1299), "SR 1,299")
        self.assertEqual(format_merchant_sar(10000), "SR 10,000")

    def test_format_merchant_sar_html_python_atom(self) -> None:
        html = str(format_merchant_sar_html(449))
        self.assertIn("cf-currency-atom", html)
        self.assertIn('dir="ltr"', html)
        self.assertIn("SR 449", html)

    def test_dashboard_loads_currency_certification_stylesheet(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_currency_certification_v1.css", html)

    def test_format_js_prefix_contract(self) -> None:
        self.assertIn("SAR_PREFIX", _FORMAT_JS)
        self.assertIn('"SR\\u00a0"', _FORMAT_JS)
        self.assertIn("formatMerchantSarHtml", _FORMAT_JS)
        self.assertIn('dir="ltr"', _FORMAT_JS)
        for bad in _REJECTED:
            self.assertNotIn(bad, _FORMAT_JS, msg=f"rejected token {bad!r} in format JS")

    def test_currency_css_ltr_nowrap(self) -> None:
        for token in (
            ".cf-currency-atom",
            "white-space: nowrap",
            "unicode-bidi: isolate",
            "direction: ltr",
        ):
            self.assertIn(token, _CURRENCY_CSS)

    def test_template_uses_certified_filter_not_manual_suffix(self) -> None:
        self.assertIn("format_merchant_sar", _TEMPLATE)
        self.assertIn('dir="ltr"', _TEMPLATE)
        for bad in ("ر.س", "&#160;SR", "ريال سعودي"):
            self.assertNotIn(bad, _TEMPLATE, msg=f"rejected token {bad!r} in template")

    def test_lazy_and_mi_use_formatter_not_manual_concat(self) -> None:
        for src in (_LAZY_JS, _MI_CARTS_JS, _VIP_JS):
            self.assertIn("formatMerchantSar", src)
            self.assertNotIn("\\u00a0SR", src)
            self.assertNotIn('" ر</div>"', src)
            self.assertNotIn('+ " SR"', src)
        self.assertIn("merchantCurrencyHtml", _MI_CARTS_JS)
        self.assertIn("window.formatMerchantSar", _LAZY_JS)
        self.assertNotIn('toLocaleString("en-US") +\n      " ر"', _MI_CARTS_JS)

    def test_plans_catalog_price_labels_use_prefix_sr(self) -> None:
        self.assertIn("SR {amount:,} / سنة", _PLANS_PY)
        self.assertIn('SR {amount} / شهر', _PLANS_PY)
        self.assertNotIn(" SR /", _PLANS_PY)

    def test_no_legacy_arabic_currency_in_merchant_sources(self) -> None:
        combined = _TEMPLATE + _FORMAT_JS + _LAZY_JS + _MI_CARTS_JS + _VIP_JS + _PLANS_PY
        self.assertNotIn("ر.س", combined)
        self.assertIsNone(re.search(r">\s*ر\s*<", combined))


if __name__ == "__main__":
    unittest.main()
