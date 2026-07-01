# -*- coding: utf-8 -*-
"""Dashboard Tab Stability V1-A — persisted cart filter survives normal-carts refresh."""

from __future__ import annotations

import unittest
from pathlib import Path


def _read(rel: str) -> str:
    return (Path(__file__).resolve().parents[1] / rel).read_text(encoding="utf-8")


class _TabFilterClientSim:
    """Minimal mirror of merchant_app + lazy reapply after renderNormalCartsTables."""

    def __init__(self) -> None:
        self.current: str | None = None
        self.applied: list[str] = []
        self.hash_tab: str | None = None
        self.hash_page = "#carts"

    def cart_tab_to_filter_mode(self, cart_tab: str) -> str:
        t = (cart_tab or "all").strip().lower()
        if t in ("intervention", "followup"):
            return "attention"
        if t == "completed":
            return "recovered"
        if t == "no_phone":
            return "nophone"
        return t

    def set_current(self, mode_or_tab: str) -> None:
        self.current = self.cart_tab_to_filter_mode(mode_or_tab)

    def apply_cart_tab_filters(self, cart_tab: str, *, persist: bool = True) -> None:
        mode = self.cart_tab_to_filter_mode(cart_tab)
        if persist:
            self.set_current(mode)
        self.applied.append(mode)

    def filter_btn_click(self, data_filter: str) -> None:
        self.set_current(data_filter)
        self.applied.append(self.current or "all")

    def reapply_after_render(self) -> None:
        if self.hash_page == "#completed":
            self.applied.append("__completed_refresh__")
            return
        if self.hash_tab and self.hash_tab.strip().lower() != "all":
            self.apply_cart_tab_filters(self.hash_tab, persist=True)
            return
        if self.current:
            self.apply_cart_tab_filters(self.current, persist=False)
        else:
            self.apply_cart_tab_filters("all", persist=True)

    def fetch_applied(self) -> None:
        self.reapply_after_render()


class DashboardTabStabilityV1aJsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app_js = _read("static/merchant_app.js")
        cls._lazy_js = _read("static/merchant_dashboard_lazy.js")

    def test_app_js_persists_current_normal_cart_filter(self) -> None:
        js = self._app_js
        self.assertIn("var currentNormalCartFilter = null", js)
        self.assertIn("function getCurrentNormalCartFilter", js)
        self.assertIn("function setCurrentNormalCartFilter", js)
        self.assertIn("window.getCurrentNormalCartFilter = getCurrentNormalCartFilter", js)
        click_block = js[js.index("initCartFiltersOnce") : js.index("function setContextSection")]
        self.assertIn("setCurrentNormalCartFilter(mode)", click_block)
        apply_block = js[js.index("function applyCartTabFilters") : js.index("function activatePage")]
        self.assertIn("options.persist !== false", apply_block)
        self.assertIn("setCurrentNormalCartFilter(mode)", apply_block)

    def test_lazy_js_reapplies_persisted_filter_not_unconditional_all(self) -> None:
        js = self._lazy_js
        self.assertIn("function reapplyNormalCartFilterAfterRender", js)
        fn = js[
            js.index("function reapplyNormalCartFilterAfterRender")
            : js.index("function applyNormalCarts")
        ]
        self.assertIn("getCurrentNormalCartFilter", fn)
        self.assertIn("persist: false", fn)
        self.assertIn('source: "persisted_reapply"', fn)
        self.assertNotIn('else if (typeof window.applyCartTabFilters === "function") {\n        window.applyCartTabFilters("all");', fn)
        render_block = js[
            js.index("function renderNormalCartsTables")
            : js.index("function reapplyNormalCartFilterAfterRender")
        ]
        self.assertIn("reapplyNormalCartFilterAfterRender();", render_block)
        self.assertNotIn('applyCartTabFilters("all")', render_block)

    def test_reopen_still_intentionally_resets_to_all(self) -> None:
        block = self._lazy_js[
            self._lazy_js.index('fetchNormalCarts("lifecycle_reopen")')
            : self._lazy_js.index("function cartRowHome")
        ]
        self.assertIn('goToCartTab("all")', block)

    def test_completed_hash_unchanged(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function reapplyNormalCartFilterAfterRender")
            : self._lazy_js.index("function applyNormalCarts")
        ]
        self.assertIn('hashRaw === "#completed"', fn)
        self.assertIn("maRefreshCompletedCartsTable", fn)


class DashboardTabStabilityV1aBehaviorTests(unittest.TestCase):
    def test_sent_filter_survives_fetch_refresh(self) -> None:
        sim = _TabFilterClientSim()
        sim.filter_btn_click("sent")
        self.assertEqual(sim.current, "sent")
        sim.applied.clear()
        sim.fetch_applied()
        self.assertEqual(sim.applied, ["sent"])

    def test_attention_survives_retry_refresh(self) -> None:
        sim = _TabFilterClientSim()
        sim.filter_btn_click("attention")
        sim.applied.clear()
        sim.fetch_applied()
        sim.fetch_applied()
        self.assertEqual(sim.applied, ["attention", "attention"])

    def test_go_to_cart_tab_all_resets_intentionally(self) -> None:
        sim = _TabFilterClientSim()
        sim.filter_btn_click("sent")
        sim.apply_cart_tab_filters("all")
        sim.applied.clear()
        sim.fetch_applied()
        self.assertEqual(sim.current, "all")
        self.assertEqual(sim.applied, ["all"])

    def test_hash_tab_takes_precedence_over_persisted(self) -> None:
        sim = _TabFilterClientSim()
        sim.filter_btn_click("sent")
        sim.hash_tab = "waiting"
        sim.applied.clear()
        sim.fetch_applied()
        self.assertEqual(sim.applied, ["waiting"])
        self.assertEqual(sim.current, "waiting")

    def test_completed_page_does_not_apply_filter_bar(self) -> None:
        sim = _TabFilterClientSim()
        sim.filter_btn_click("attention")
        sim.hash_page = "#completed"
        sim.applied.clear()
        sim.fetch_applied()
        self.assertEqual(sim.applied, ["__completed_refresh__"])
        self.assertEqual(sim.current, "attention")


if __name__ == "__main__":
    unittest.main()
