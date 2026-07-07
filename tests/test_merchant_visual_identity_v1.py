# -*- coding: utf-8 -*-
"""Visual Identity Unification V1 — presentation contract."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_VI_CSS = (_ROOT / "static" / "merchant_visual_identity_v1.css").read_text(encoding="utf-8")
_APP_JS = (_ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


class MerchantVisualIdentityV1Tests(unittest.TestCase):
    def test_dashboard_shell_loads_visual_identity_css(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_visual_identity_v1.css", html)

    def test_certified_font_token_arial(self) -> None:
        self.assertIn("--cfvi-font-certified: Arial", _VI_CSS)

    def test_unified_card_and_hero_classes(self) -> None:
        for token in ("--cfvi-hero-bg", ".ma-vi-hero", ".ma-vi-card", "--cfvi-sidebar-bg"):
            self.assertIn(token, _VI_CSS, msg=f"missing {token}")

    def test_hero_sync_in_router(self) -> None:
        self.assertIn("syncVisualHero", _APP_JS)
        self.assertIn("ma-vi-hero", _APP_JS)

    def test_carts_hero_unified(self) -> None:
        self.assertIn("ma-vi-hero", _TEMPLATE)
        self.assertIn("CartFlow يتابع سلال متجرك اليوم", _TEMPLATE)

    def test_hardening_chrome_and_cards(self) -> None:
        for token in (
            "--cfvi-chrome-bg",
            ".ma-global-topbar",
            ".ma-wa-mode-card.is-selected",
            ".ma-plan-card.is-current",
            ".ma-journey-gate-card",
        ):
            self.assertIn(token, _VI_CSS, msg=f"missing {token}")

    def test_page_purpose_hero_copy(self) -> None:
        self.assertIn("صحة تواصل متجرك", _APP_JS)
        self.assertIn("اشتراكك الحالي", _APP_JS)
        self.assertIn("إعداد متجرك", _APP_JS)


if __name__ == "__main__":
    unittest.main()
