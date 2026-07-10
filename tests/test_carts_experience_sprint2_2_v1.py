# -*- coding: utf-8 -*-
"""Carts Experience Sprint 2.2 — truth & loading stabilization contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APP = (_ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")
_LAZY = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_POLISH = (_ROOT / "static" / "merchant_product_polish_v1.css").read_text(
    encoding="utf-8"
)
_TMPL = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


class CartsExperienceSprint22V1Tests(unittest.TestCase):
    def test_no_technical_hero_pending_copy(self) -> None:
        self.assertNotIn("جارٍ تجهيز صورة السلال", _APP)
        self.assertNotIn("جارٍ تجهيز صورة السلال", _LAZY)
        self.assertNotIn("CARTS_HERO_STORY_PENDING", _APP)

    def test_pending_hero_story_returns_null(self) -> None:
        fn = _LAZY[
            _LAZY.index("function cartsHeroStoryFromVerdict") : _LAZY.index(
                "function cartsHeroSupportFromVerdict"
            )
        ]
        self.assertIn("return null", fn)
        self.assertNotIn("تجهيز", fn)

    def test_reveal_gate_holds_until_final(self) -> None:
        self.assertIn("function cartsPlanIsCanonicalReveal", _LAZY)
        self.assertIn("rsc_commit_hold_reveal", _LAZY)
        self.assertIn("data-carts-ready", _APP)
        self.assertIn("data-carts-ready", _POLISH)
        self.assertIn("ma-carts-unified-loading", _TMPL)
        paint = _LAZY[
            _LAZY.index("function paintCartPageFromRsc") : _LAZY.index(
                "function renderMiCartsV1Pending"
            )
        ]
        self.assertIn("cartsPlanIsCanonicalReveal", paint)
        self.assertIn("cartsExperienceRevealed = true", paint)

    def test_filter_overlap_hint(self) -> None:
        self.assertIn("ma-cart-filters-hint", _TMPL)
        self.assertIn("تصنيفات لنفس السلال", _TMPL)
        self.assertIn("أكثر من تصنيف", _TMPL)

    def test_reveal_safety_timeout(self) -> None:
        self.assertIn("scheduleCartsRevealSafety", _LAZY)
        self.assertIn("carts_reveal_safety", _LAZY)
        self.assertIn("maScheduleCartsRevealSafety", _APP)

    def test_unified_loading_outside_shell(self) -> None:
        idx_loading = _TMPL.index('id="ma-carts-unified-loading"')
        idx_shell = _TMPL.index('class="ma-pe-v2-carts-shell')
        self.assertLess(idx_loading, idx_shell)


if __name__ == "__main__":
    unittest.main()
