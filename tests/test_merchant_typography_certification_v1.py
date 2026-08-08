# -*- coding: utf-8 -*-
"""Typography Lock V1 — merchant typography certification."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TYPO_CSS = (_ROOT / "static" / "merchant_typography_certification_v1.css").read_text(
    encoding="utf-8"
)
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")


class MerchantTypographyCertificationV1Tests(unittest.TestCase):
    def test_dashboard_shell_loads_frame_typography(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_frame_v1.css", html)
        self.assertNotIn("merchant_typography_certification_v1.css", html)

    def test_no_google_fonts_link_in_shell_html(self) -> None:
        """External font import lives in frame CSS; template stays free of <link> font tags."""
        self.assertNotIn("fonts.googleapis.com", _TEMPLATE)
        self.assertNotIn("IBM Plex", _TEMPLATE)

    def test_arial_single_certified_font_token_offline(self) -> None:
        self.assertIn("--cftyp-font: Arial, sans-serif", _TYPO_CSS)
        self.assertNotIn("IBM Plex", _TYPO_CSS)
        self.assertNotIn("system-ui", _TYPO_CSS)
        self.assertTrue(
            (_ROOT / "static" / "merchant_typography_certification_v1.css").is_file()
        )

    def test_certified_typography_token_system(self) -> None:
        for token in (
            "--cftyp-hero-title-size",
            "--cftyp-hero-subtitle-size",
            "--cftyp-page-title-size",
            "--cftyp-section-title-size",
            "--cftyp-card-title-size",
            "--cftyp-card-subtitle-size",
            "--cftyp-body-size",
            "--cftyp-body-secondary-size",
            "--cftyp-caption-size",
            "--cftyp-button-size",
            "--cftyp-badge-size",
            "--cftyp-table-size",
            "--cftyp-numeric-size",
            "--cftyp-currency-size",
        ):
            self.assertIn(token, _TYPO_CSS, msg=f"missing {token}")

    def test_hero_subtitle_unified_selector(self) -> None:
        self.assertIn("--cftyp-hero-subtitle-size", _TYPO_CSS)
        self.assertIn("#pageSub", _TYPO_CSS)
        self.assertIn(".ma-page-hero__purpose", _TYPO_CSS)

    def test_legacy_font_aliases_point_to_cftyp(self) -> None:
        self.assertIn("--cfvi-font-certified: var(--cftyp-font)", _TYPO_CSS)
        self.assertIn("--pds-font: var(--cftyp-font)", _TYPO_CSS)
        self.assertIn("--v2-font: var(--cftyp-font)", _TYPO_CSS)

    def test_template_inline_font_declarations_removed(self) -> None:
        """Shell chrome must not invent inline type; MEIF surface <style> residual is tracked."""
        shell_chunk = _TEMPLATE.split("<style>", 1)[0]
        self.assertNotRegex(shell_chunk, r"font-size:\s*\d")
        self.assertNotRegex(shell_chunk, r"font-weight:\s*\d")
        self.assertIn("/* MSR V1 — hierarchy only", _TEMPLATE)

    def test_lazy_js_inline_font_declarations_removed(self) -> None:
        self.assertNotIn("font-size:", _LAZY_JS)
        self.assertNotIn("font-weight:", _LAZY_JS)

    def test_button_typography_unified(self) -> None:
        self.assertIn(".v2-btn", _TYPO_CSS)
        self.assertIn(".filter-btn", _TYPO_CSS)
        self.assertIn("--cftyp-button-size", _TYPO_CSS)

    def test_sidebar_typography_lock(self) -> None:
        self.assertIn("#ma-context-sidebar", _TYPO_CSS)
        self.assertIn(".ma-gtb-section", _TYPO_CSS)


if __name__ == "__main__":
    unittest.main()
