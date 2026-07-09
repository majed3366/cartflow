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
_WORKSPACE_CSS = (_ROOT / "static" / "merchant_workspace_expansion_v1.css").read_text(
    encoding="utf-8"
)
_PE_CSS = (_ROOT / "static" / "merchant_pe_v2.css").read_text(encoding="utf-8")
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
        # Freshness: pending/cache must not emit final count headlines.
        self.assertIn("refreshing", block)
        self.assertIn("جارٍ تحديث الصورة", block)
        self.assertIn('freshness: "pending"', block)
        self.assertIn('freshness: "final"', block)

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
        # Hotfix: verdict must not suppress the cart body empty/pending host.
        self.assertNotIn('byId("ma-carts-queue-empty")', block)
        self.assertNotIn("emptyWhisper", block)

    def test_pending_with_rows_shows_visible_body(self) -> None:
        block = _extract_js_function(_LAZY_JS, "renderMiCartsV1Pending")
        self.assertIn("يجهّز فهم هذه السلال", block)
        self.assertIn("لن تحتاج لاتخاذ إجراء حتى تكتمل القراءة", block)
        self.assertIn("data-mi-pending", block)
        self.assertIn("hasRows", block)
        # Must pass real rows into verdict when available
        self.assertIn("renderCartsAttentionVerdictV1(activeRows)", block)
        self.assertNotIn("renderCartsAttentionVerdictV1([], { loading: true })\n    if (!cartsV2UiEnabled())", block)
        # Empty whisper only hidden when groups host owns pending body
        self.assertIn("ma-carts-queue-empty", block)

    def test_pending_without_rows_uses_calm_loading_verdict(self) -> None:
        block = _extract_js_function(_LAZY_JS, "renderMiCartsV1Pending")
        self.assertIn("يجهّز فهم المتجر", block)
        self.assertIn(
            'renderCartsAttentionVerdictV1([], { loading: true, freshness: "pending" })',
            block,
        )

    def test_workspace_pending_passes_rows(self) -> None:
        block = _extract_js_function(_LAZY_JS, "renderMiCartsV1Workspace")
        self.assertIn("renderMiCartsV1Pending(rows)", block)
        self.assertNotIn('renderMiCartsV1Pending("CartFlow', block)

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

    def test_desktop_queue_column_not_stuck_at_360px(self) -> None:
        """Desktop regression: verdict + MI body must not sit in a fixed 360px track."""
        # Base PE still documents the legacy split (other surfaces / fallback).
        self.assertIn("grid-template-columns: 360px 1fr", _PE_CSS)
        # Carts desktop override must widen the queue/MI column past 360px.
        self.assertIn(
            "grid-template-columns: minmax(480px, 1.2fr) minmax(360px, 0.8fr)",
            _CSS,
        )
        self.assertIn(
            "grid-template-columns: minmax(480px, 1.2fr) minmax(360px, 0.8fr)",
            _WORKSPACE_CSS,
        )
        # Verdict + groups fill the queue column (no leftover 1080px cap).
        verdict_block = _CSS[
            _CSS.index(".ma-carts-attention-verdict {") : _CSS.index(
                ".ma-carts-attention-verdict[hidden]"
            )
        ]
        self.assertIn("max-width: none", verdict_block)
        self.assertIn("width: 100%", verdict_block)
        # DOM contract: body host remains under verdict in the queue column.
        idx_verdict = _TMPL.index("ma-carts-attention-verdict-v1")
        idx_groups = _TMPL.index('id="ma-carts-groups-v2"')
        idx_panel = _TMPL.index('id="ma-carts-panel-v2"')
        self.assertLess(idx_verdict, idx_groups)
        self.assertLess(idx_groups, idx_panel)

    def test_dashboard_route_passes_flag(self) -> None:
        pages = (_ROOT / "routes" / "merchant_pages.py").read_text(encoding="utf-8")
        self.assertIn("merchant_carts_v2_ui", pages)
        self.assertIn("carts_v2_ui_enabled", pages)

    def test_cache_hydrate_marks_verdict_pending(self) -> None:
        block = _extract_js_function(_LAZY_JS, "hydrateNormalCartsCache")
        self.assertIn("cartsAttentionVerdictPending = true", block)
        self.assertIn("cartsAttentionVerdictFresh = false", block)
        self.assertIn('verdict_freshness: "pending"', block)
        # Cache still paints tables (body not blank) but verdict stays non-final.
        self.assertIn('prepareNormalCartsPayload(', block)
        self.assertIn('"cache"', block)

    def test_fresh_apply_marks_verdict_final(self) -> None:
        block = _extract_js_function(_LAZY_JS, "applyNormalCarts")
        # Successful apply clears pending before render.
        idx_clear = block.index("cartsAttentionVerdictPending = false")
        idx_fresh = block.index("cartsAttentionVerdictFresh = true")
        idx_render = block.index("renderNormalCartsTables(prepared)")
        self.assertLess(idx_clear, idx_render)
        self.assertLess(idx_fresh, idx_render)
        self.assertIn('verdict_freshness: "final"', block)
        # Keep-old-rows paths must not leave a final stale verdict.
        self.assertIn('rerenderCartsFromMemory("partial_keep")', block)
        self.assertIn('rerenderCartsFromMemory("thin_keep")', block)
        self.assertIn('rerenderCartsFromMemory("unconfirmed_empty_keep")', block)
        self.assertIn('markAttentionVerdictRefreshing("partial_empty")', block)

    def test_memory_keep_paths_force_pending_verdict(self) -> None:
        block = _extract_js_function(_LAZY_JS, "rerenderCartsFromMemory")
        self.assertIn("_keep", block)
        self.assertIn("cartsAttentionVerdictPending = true", block)
        self.assertIn("cartsAttentionVerdictFresh = false", block)

    def test_render_exposes_freshness_attr(self) -> None:
        block = _extract_js_function(_LAZY_JS, "renderCartsAttentionVerdictV1")
        self.assertIn("data-verdict-freshness", block)
        self.assertIn("resolveAttentionVerdictPending", block)

    def test_setup_render_build_bumped_for_verdict_freshness(self) -> None:
        from services.merchant_setup_render_build import MERCHANT_SETUP_RENDER_BUILD

        self.assertIn("verdict-freshness", MERCHANT_SETUP_RENDER_BUILD)
        self.assertNotEqual(
            MERCHANT_SETUP_RENDER_BUILD, "ui-setup-v8d-home-closure-v3"
        )


if __name__ == "__main__":
    unittest.main()
