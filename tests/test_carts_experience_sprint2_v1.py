# -*- coding: utf-8 -*-
"""Carts Experience Sprint 2 — shared Hero contracts (no redesign)."""
from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APP_JS = (_ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")
_LAZY = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_POLISH = (_ROOT / "static" / "merchant_product_polish_v1.css").read_text(
    encoding="utf-8"
)
_TMPL = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


class CartsExperienceSprint2V1Tests(unittest.TestCase):
    def test_carts_uses_shared_global_hero_not_inline_list(self) -> None:
        start = _APP_JS.index("PAGES_WITH_INLINE_HERO")
        block = _APP_JS[start : start + 180]
        self.assertNotIn("carts:", block)
        self.assertIn("followup:", block)
        self.assertIn('data-shared-hero-carts', _APP_JS)
        self.assertIn("ملخص ما يحتاج انتباهك", _APP_JS)
        self.assertIn("ما الذي يحتاج انتباهك الآن؟", _APP_JS)

    def test_polish_does_not_hide_global_hero_on_carts(self) -> None:
        self.assertNotIn(
            'body[data-ma-page="carts"] #ma-page-hero-global',
            _POLISH,
        )

    def test_inline_carts_hero_hidden_in_template(self) -> None:
        self.assertIn('id="ma-carts-hero" hidden', _TMPL)
        self.assertIn('id="ma-page-hero-global"', _TMPL)

    def test_lazy_fills_shared_hero_from_verdict(self) -> None:
        self.assertIn("function fillSharedCartsHero", _LAZY)
        self.assertIn("function cartsHeroStoryFromVerdict", _LAZY)
        self.assertIn("لديك ", _LAZY)
        self.assertIn("سلة تحتاج انتباهك.", _LAZY)
        self.assertIn("لا توجد سلال تحتاج تدخلك اليوم.", _LAZY)
        self.assertIn("fillSharedCartsHero(verdict)", _LAZY)
        self.assertIn("fillSharedCartsHero(", _LAZY)
        # Must not paint Carts Hero while another page is active.
        fill_fn = _LAZY[
            _LAZY.index("function fillSharedCartsHero") : _LAZY.index(
                "function renderCartsAttentionVerdictV1"
            )
        ]
        self.assertIn('pageKey === "carts"', fill_fn)
        self.assertNotIn('setAttribute("data-ma-page", "carts")', fill_fn)

    def test_attention_verdict_host_stays_quiet(self) -> None:
        # Hero owns story — paint paths hide inline verdict host.
        paint = _LAZY[
            _LAZY.index("function paintAttentionVerdictFromPlan") : _LAZY.index(
                "function paintCartBodyPendingFromPlan"
            )
        ]
        self.assertIn("fillSharedCartsHero", paint)
        self.assertIn("host.hidden = true", paint)


if __name__ == "__main__":
    unittest.main()
