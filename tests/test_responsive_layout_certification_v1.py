# -*- coding: utf-8 -*-
"""Responsive Layout Certification V1 — superseded by Frame V1 full-width stage."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_FRAME_CSS = (_ROOT / "static" / "merchant_frame_v1.css").read_text(encoding="utf-8")


class ResponsiveLayoutCertificationV1Tests(unittest.TestCase):
    def test_frame_owns_content_width(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_frame_v1.css", html)
        self.assertNotIn("merchant_responsive_layout_v1.css", html)

    def test_no_family_a_content_choke_in_live_template(self) -> None:
        self.assertNotIn("merchant_responsive_layout_v1.css", _TEMPLATE)

    def test_frame_uses_full_workspace_width(self) -> None:
        self.assertIn("--ma-content-max: none", _FRAME_CSS)
        self.assertIn("max-width: none !important", _FRAME_CSS)

    def test_settings_keep_reading_comfort(self) -> None:
        self.assertIn('data-ma-page="settings"] #page-settings', _FRAME_CSS)
        self.assertIn("max-width: 720px", _FRAME_CSS)

    def test_legacy_responsive_file_still_exists_offline(self) -> None:
        self.assertTrue((_ROOT / "static" / "merchant_responsive_layout_v1.css").is_file())


if __name__ == "__main__":
    unittest.main()
