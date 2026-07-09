# -*- coding: utf-8 -*-
"""Cart Page V2 Phase 2 — Attention Verdict contract tests."""
from __future__ import annotations

import os
import re
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parent.parent
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_CSS = (_ROOT / "static" / "merchant_product_polish_v1.css").read_text(encoding="utf-8")
_TMPL = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


def _extract_js_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_fn = re.search(r"\n  function \w+\(", source[start + 1 :])
    end = start + 1 + next_fn.start() if next_fn else len(source)
    return source[start:end]


class CartPageAttentionVerdictV1Tests(unittest.TestCase):
    def test_template_host_and_flag_attr(self) -> None:
        self.assertIn('id="ma-carts-attention-verdict-v1"', _TMPL)
        self.assertIn("merchant_carts_v2_ui", _TMPL)
        self.assertIn("data-carts-v2-ui", _TMPL)
        self.assertIn("ma-carts--v2-ui", _TMPL)
        # Verdict host appears before legacy hero
        idx_verdict = _TMPL.index("ma-carts-attention-verdict-v1")
        idx_hero = _TMPL.index('id="ma-carts-hero"')
        self.assertLess(idx_verdict, idx_hero)

    def test_flag_default_on(self) -> None:
        from services.cart_page_v2_ui_flag_v1 import carts_v2_ui_enabled

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CARTFLOW_CARTS_V2_UI", None)
            self.assertTrue(carts_v2_ui_enabled())
        with mock.patch.dict(os.environ, {"CARTFLOW_CARTS_V2_UI": "0"}):
            self.assertFalse(carts_v2_ui_enabled())

    def test_verdict_builder_modes(self) -> None:
        block = _extract_js_function(_LAZY_JS, "buildCartsAttentionVerdictV1")
        self.assertIn("needs_you", block)
        self.assertIn("automatic", block)
        self.assertIn("لا يلزم إجراء منك الآن", block)
        self.assertIn("تحتاج انتباهك", block)
        self.assertIn("تابع من البطاقات أدناه", block)
        self.assertIn("countCartPagePrimaryActions", block)

    def test_counts_use_primary_action_resolver(self) -> None:
        block = _extract_js_function(_LAZY_JS, "countCartPagePrimaryActions")
        self.assertIn("resolveCartPagePrimaryAction", block)
        self.assertIn("isArchivedVisual", block)
        self.assertIn("contact_customer", block)
        self.assertIn("follow_up_manually", block)
        self.assertIn("review_cart", block)
        self.assertIn("wait", block)

    def test_render_hides_competing_summaries(self) -> None:
        block = _extract_js_function(_LAZY_JS, "renderCartsAttentionVerdictV1")
        self.assertIn("ma-carts-hero", block)
        self.assertIn("ma-carts-queue-sub", block)
        self.assertIn("ma-carts-product-language-v1", block)
        self.assertIn("cartsV2UiEnabled", block)

    def test_mpl_skipped_when_v2_ui(self) -> None:
        block = _extract_js_function(_LAZY_JS, "renderMiCartsProductLanguageNarrative")
        self.assertIn("cartsV2UiEnabled", block)
        idx_flag = block.index("cartsV2UiEnabled")
        idx_compose = block.index("composePageInsightV1")
        self.assertLess(idx_flag, idx_compose)

    def test_workspace_calls_verdict(self) -> None:
        block = _extract_js_function(_LAZY_JS, "renderMiCartsV1Workspace")
        self.assertIn("renderCartsAttentionVerdictV1", block)
        idx_verdict = block.index("renderCartsAttentionVerdictV1")
        idx_mpl = block.index("renderMiCartsProductLanguageNarrative")
        self.assertLess(idx_verdict, idx_mpl)

    def test_css_hides_legacy_when_v2(self) -> None:
        self.assertIn("#page-carts.ma-carts--v2-ui #ma-carts-hero", _CSS)
        self.assertIn(".ma-carts-attention-verdict__headline", _CSS)

    def test_dashboard_route_passes_flag(self) -> None:
        pages = (_ROOT / "routes" / "merchant_pages.py").read_text(encoding="utf-8")
        self.assertIn("merchant_carts_v2_ui", pages)
        self.assertIn("carts_v2_ui_enabled", pages)


if __name__ == "__main__":
    unittest.main()
