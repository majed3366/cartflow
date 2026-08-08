# -*- coding: utf-8 -*-
"""Visual Identity Unification V1 — tokens folded into Frame V1; CSS file offline."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_FRAME_CSS = (_ROOT / "static" / "merchant_frame_v1.css").read_text(encoding="utf-8")
_APP_JS = (_ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


class MerchantVisualIdentityV1Tests(unittest.TestCase):
    def test_dashboard_shell_loads_frame_not_vi_override(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_frame_v1.css", html)
        self.assertNotIn("merchant_visual_identity_v1.css", html)

    def test_brand_tokens_live_in_frame(self) -> None:
        for token in ("--cf-navy: #082048", "--cf-teal: #18b0a8", "--cfvi-chrome-bg"):
            self.assertIn(token, _FRAME_CSS)

    def test_hero_sync_in_router(self) -> None:
        self.assertIn("syncVisualHero", _APP_JS)
        self.assertIn("ma-vi-hero", _APP_JS)
        self.assertIn("syncFrameChrome", _APP_JS)

    def test_canonical_mark_in_rail(self) -> None:
        self.assertIn("cartflow_cf_mark.png", _TEMPLATE)
        self.assertIn("cf-rail__brand", _TEMPLATE)

    def test_legacy_vi_file_still_exists_offline(self) -> None:
        self.assertTrue((_ROOT / "static" / "merchant_visual_identity_v1.css").is_file())


if __name__ == "__main__":
    unittest.main()
