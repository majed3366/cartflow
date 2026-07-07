# -*- coding: utf-8 -*-
"""Product Design System Compliance V1 — presentation contract tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_PDS_CSS = (_ROOT / "static" / "merchant_pds_compliance_v1.css").read_text(encoding="utf-8")
_FORMAT_JS = (_ROOT / "static" / "merchant_pds_format_v1.js").read_text(encoding="utf-8")
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_MI_CARTS_JS = (_ROOT / "static" / "merchant_intelligence_carts_v1.js").read_text(encoding="utf-8")


class MerchantPdsComplianceV1Tests(unittest.TestCase):
    def test_dashboard_shell_loads_pds_assets(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_pds_compliance_v1.css", html)
        self.assertIn("merchant_pds_format_v1.js", html)

    def test_pds_css_typography_tokens(self) -> None:
        for token in (
            "--pds-font",
            "--pds-type-story",
            "--pds-space-md",
            ".ma-mi-group-card__title",
            "body[data-cf-merchant-app",
        ):
            self.assertIn(token, _PDS_CSS, msg=f"missing {token}")

    def test_format_js_exports(self) -> None:
        self.assertIn("window.formatMerchantSar", _FORMAT_JS)
        self.assertIn("window.formatMerchantSarHtml", _FORMAT_JS)
        self.assertIn("window.sanitizeMerchantLanguage", _FORMAT_JS)
        self.assertIn("\\u00a0ر.س", _FORMAT_JS)

    def test_currency_compliance_in_lazy_dashboard(self) -> None:
        self.assertIn("formatMerchantSar", _LAZY_JS)
        self.assertNotIn('+ " ر"', _LAZY_JS)
        self.assertNotIn('+ " ريال"', _LAZY_JS)
        self.assertNotIn(" ر</div>", _LAZY_JS)

    def test_language_sanitizer_in_mi_carts(self) -> None:
        self.assertIn("sanitizeMerchantLanguage", _MI_CARTS_JS)

    def test_template_currency_suffix(self) -> None:
        self.assertIn('class="cf-currency-atom"', _TEMPLATE)
        self.assertIn("&#160;ر.س", _TEMPLATE)
        self.assertNotIn("↑ ريال — اليوم", _TEMPLATE)


if __name__ == "__main__":
    unittest.main()
