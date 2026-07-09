# -*- coding: utf-8 -*-
"""Carts archive/reopen regression — footer move must not break lifecycle actions."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")


def _extract_js_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_fn = re.search(r"\n  function \w+\(", source[start + 1 :])
    end = start + 1 + next_fn.start() if next_fn else len(source)
    return source[start:end]


class CartsArchiveReopenRegressionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._js = _LAZY_JS

    def test_lifecycle_actions_bind_after_panel_footer_render(self) -> None:
        block = _extract_js_function(self._js, "renderPeV2CartPanel")
        self.assertIn("merchantPeV2ConversationFooterHtml", self._js)
        self.assertIn("bindCustomerLifecycleActions(panel)", block)
        self.assertIn("bindCustomerLifecycleActions(mobile)", block)

    def test_shared_footer_includes_archive_and_reopen_markers(self) -> None:
        block = _extract_js_function(self._js, "merchantPeV2ConversationFooterHtml")
        self.assertIn("merchantPeV2SecondaryActionsHtml", block)
        secondary = _extract_js_function(self._js, "merchantPeV2SecondaryActionsHtml")
        self.assertIn("data-lc-archive", secondary)
        self.assertIn("data-lc-reopen", secondary)
        self.assertIn("data-recovery-key", secondary)

    def test_mobile_panel_uses_shared_footer_for_lifecycle_actions(self) -> None:
        block = _extract_js_function(self._js, "merchantPeV2MobilePanelHtml")
        self.assertIn("merchantPeV2ConversationFooterHtml", block)
        self.assertIn("v2-conversation--mobile", block)

    def test_secondary_actions_prefer_row_dashboard_action_over_stale_projection(self) -> None:
        block = _extract_js_function(self._js, "merchantPeV2SecondaryActionsHtml")
        idx_act = block.index("customer_lifecycle_dashboard_action")
        idx_lc = block.index("lc.archive_visible")
        self.assertLess(idx_act, idx_lc)
        self.assertIn('act === "archive"', block)
        self.assertIn('act === "reopen"', block)
        self.assertIn("isArchivedVisual(mc)", block)

    def test_archive_handler_moves_row_and_refreshes_completed(self) -> None:
        block = self._js[
            self._js.index("[data-lc-archive]") : self._js.index("[data-lc-reopen]")
        ]
        self.assertIn("patchCartRowArchivedVisual(rk, true", block)
        self.assertIn("refreshCompletedCartsTableAfterLifecycleChange", block)
        self.assertIn("lifecycleActionPayload(mc, rk)", block)
        self.assertIn('fetch("/api/dashboard/cart-lifecycle/archive"', block)

    def test_reopen_handler_sends_payload_and_refreshes(self) -> None:
        block = self._js[
            self._js.index("[data-lc-reopen]") : self._js.index("function cartRowHome")
        ]
        self.assertIn("lifecycleActionPayload(mc, rk)", block)
        self.assertIn('fetch("/api/dashboard/cart-lifecycle/reopen"', block)
        self.assertIn("syncReopenedCartRowMemory", block)
        self.assertIn("refreshCompletedCartsTableAfterLifecycleChange", block)

    def test_sync_archived_cart_row_memory_moves_normal_to_archived_pool(self) -> None:
        fn = _extract_js_function(self._js, "syncArchivedCartRowMemory")
        self.assertIn("lastNormalCartsPageRows = lastNormalCartsPageRows.filter", fn)
        self.assertIn("lastArchivedCartsPageRows.push", fn)
        self.assertIn("patchCartRowLifecycleUi", fn)

    def test_patch_cart_row_archived_visual_delegates_to_sync_archived(self) -> None:
        fn = _extract_js_function(self._js, "patchCartRowArchivedVisual")
        self.assertIn("syncArchivedCartRowMemory", fn)
        self.assertNotIn("customer_lifecycle_is_archived_visual = true", fn)

    def test_active_workspace_excludes_archived_visual_rows(self) -> None:
        fn = _extract_js_function(self._js, "activeNormalCartRows")
        self.assertIn("isArchivedVisual", fn)
        rerender = _extract_js_function(self._js, "rerenderAllCartsTable")
        self.assertIn("activeNormalCartRows", rerender)
        render = _extract_js_function(self._js, "renderNormalCartsTables")
        self.assertIn("activeNormalCartRows", render)

    def test_test_hooks_expose_archive_reopen_memory_helpers(self) -> None:
        hooks = self._js[
            self._js.index("window.__maNormalCartsTestHooks")
            : self._js.index("window.__maVipCartsTestHooks")
        ]
        for name in (
            "syncArchivedCartRowMemory",
            "activeNormalCartRows",
            "patchCartRowLifecycleUi",
        ):
            self.assertIn(name, hooks, msg=f"missing hook {name}")


if __name__ == "__main__":
    unittest.main()
