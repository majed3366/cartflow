# -*- coding: utf-8 -*-
"""Hero Experience Sprint 2.1 — Question → Answer → Optional contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_APP = (_ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")
_PULSE = (_ROOT / "static" / "merchant_pulse_v1.js").read_text(encoding="utf-8")
_LAZY = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_VI = (_ROOT / "static" / "merchant_visual_identity_v1.css").read_text(encoding="utf-8")


class HeroQuestionFirstNarrativeV1Tests(unittest.TestCase):
    def test_shared_helper_maps_slots(self) -> None:
        fn = _APP[
            _APP.index("function fillQuestionFirstHero") : _APP.index(
                "function clearQuestionFirstHero"
            )
        ]
        # question → pageSub (eyebrow), story → pageTitle (focus), support → pagePurpose
        self.assertIn("ps.textContent = question", fn)
        self.assertIn("pt.textContent = story", fn)
        self.assertIn("pp.textContent = support", fn)
        self.assertIn('data-hero-narrative", "question-first"', fn)

    def test_home_pulse_does_not_clobber_other_pages(self) -> None:
        fn = _PULSE[
            _PULSE.index("function fillSharedHero") : _PULSE.index(
                "function refillHomeSharedHero"
            )
        ]
        self.assertIn("homeActive", fn)
        self.assertIn('pageKey === "home"', fn)

    def test_home_question_first(self) -> None:
        self.assertIn("HOME_HERO_QUESTION", _PULSE)
        self.assertIn("ماذا حدث أثناء غيابك؟", _PULSE)
        self.assertNotIn("ملخص ما حدث أثناء غيابك", _PULSE)
        self.assertIn("homeHeroSupport", _PULSE)
        self.assertIn("CartFlow تابع عمليات الاسترداد أثناء غيابك.", _PULSE)

    def test_carts_question_first(self) -> None:
        self.assertIn("ما الذي يحتاج انتباهك الآن؟", _LAZY)
        self.assertIn("cartsHeroSupportFromVerdict", _LAZY)
        self.assertIn("تابع الحالات التي تحتاج قرارًا منك.", _LAZY)
        fill = _LAZY[
            _LAZY.index("function fillSharedCartsHero") : _LAZY.index(
                "function renderCartsAttentionVerdictV1"
            )
        ]
        self.assertNotIn("ملخص ما يحتاج انتباهك", fill)

    def test_css_orders_question_before_answer(self) -> None:
        block = _VI[
            _VI.index("data-hero-narrative") : _VI.index(
                "Global hero compact pages"
            )
        ]
        # pageSub (question) order 1 before pageTitle (answer) order 2
        self.assertLess(block.index("#pageSub"), block.index("#pageTitle"))
        self.assertIn("order: 1", block)
        self.assertIn("order: 2", block)


if __name__ == "__main__":
    unittest.main()
