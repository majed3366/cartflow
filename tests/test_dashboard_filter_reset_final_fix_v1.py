# -*- coding: utf-8 -*-
"""Dashboard Filter Reset Final Fix V1 — manual filter bar wins over ?tab=all."""

from __future__ import annotations

import unittest
from pathlib import Path


def _read(rel: str) -> str:
    return (Path(__file__).resolve().parents[1] / rel).read_text(encoding="utf-8")


class _FilterResetSim:
    """Mirror merchant_app + lazy reapply with url tab=all ignored."""

    def __init__(self) -> None:
        self.current: str | None = None
        self.storage: str | None = None
        self.applied: list[tuple[str, bool, str]] = []
        self.hash_tab: str | None = None

    def cart_tab_to_filter_mode(self, cart_tab: str) -> str:
        t = (cart_tab or "all").strip().lower()
        if t in ("intervention", "followup"):
            return "attention"
        if t == "completed":
            return "recovered"
        if t == "no_phone":
            return "nophone"
        return t

    def url_applies(self, url_tab: str | None) -> bool:
        if not url_tab:
            return False
        return url_tab.strip().lower() != "all"

    def effective(self) -> str | None:
        return self.current or self.storage

    def set_current(self, mode_or_tab: str) -> None:
        self.current = self.cart_tab_to_filter_mode(mode_or_tab)
        if self.current and self.current != "all":
            self.storage = self.current
        elif self.current == "all":
            self.storage = None

    def filter_click(self, data_filter: str) -> None:
        self.set_current(data_filter)

    def apply(self, cart_tab: str, *, persist: bool, source: str) -> None:
        mode = self.cart_tab_to_filter_mode(cart_tab)
        if persist:
            self.set_current(mode)
        self.applied.append((mode, persist, source))

    def activate_carts(self, url_tab: str | None = None) -> None:
        if url_tab and self.url_applies(url_tab):
            self.apply(url_tab, persist=True, source="url")
        elif self.effective():
            self.apply(self.effective() or "all", persist=False, source="persisted")
        else:
            self.apply("all", persist=True, source="default")

    def reapply_after_render(self) -> None:
        if self.hash_tab and self.url_applies(self.hash_tab):
            self.apply(self.hash_tab, persist=True, source="url_reapply")
        elif self.effective():
            self.apply(self.effective() or "all", persist=False, source="persisted_reapply")
        else:
            self.apply("all", persist=True, source="default_reapply")

    def nav_all_click(self) -> None:
        self.set_current("all")
        self.apply("all", persist=True, source="nav_all")
        self.hash_tab = None


class DashboardFilterResetFinalFixV1BehaviorTests(unittest.TestCase):
    def test_sent_survives_background_reapply_with_tab_all_in_hash(self) -> None:
        sim = _FilterResetSim()
        sim.filter_click("sent")
        sim.hash_tab = "all"
        sim.applied.clear()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "sent")
        self.assertEqual([a[0] for a in sim.applied], ["sent"])
        self.assertEqual(sim.applied[0][1], False)

    def test_attention_survives_hash_sync_without_tab(self) -> None:
        sim = _FilterResetSim()
        sim.filter_click("attention")
        sim.hash_tab = None
        sim.applied.clear()
        sim.activate_carts(url_tab=None)
        sim.reapply_after_render()
        self.assertEqual(sim.current, "attention")
        self.assertTrue(all(a[0] == "attention" for a in sim.applied))

    def test_recovered_survives_refresh_reapply(self) -> None:
        sim = _FilterResetSim()
        sim.filter_click("recovered")
        sim.applied.clear()
        sim.reapply_after_render()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "recovered")
        self.assertEqual([a[0] for a in sim.applied], ["recovered", "recovered"])

    def test_explicit_all_click_sets_all(self) -> None:
        sim = _FilterResetSim()
        sim.filter_click("sent")
        sim.nav_all_click()
        sim.applied.clear()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "all")
        self.assertIsNone(sim.storage)
        self.assertEqual([a[0] for a in sim.applied], ["all"])

    def test_sidebar_waiting_url_still_applies(self) -> None:
        sim = _FilterResetSim()
        sim.filter_click("sent")
        sim.hash_tab = "waiting"
        sim.applied.clear()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "waiting")

    def test_storage_hydrates_after_reload_simulation(self) -> None:
        sim = _FilterResetSim()
        sim.filter_click("sent")
        stored = sim.storage
        sim2 = _FilterResetSim()
        sim2.storage = stored
        sim2.current = None
        sim2.activate_carts(url_tab="all")
        self.assertEqual(sim2.effective(), "sent")
        self.assertEqual([a[0] for a in sim2.applied], ["sent"])


class DashboardFilterResetFinalFixV1JsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app_js = _read("static/merchant_app.js")
        cls._lazy_js = _read("static/merchant_dashboard_lazy.js")

    def test_app_js_ignores_url_tab_all_for_filter_bar(self) -> None:
        self.assertIn("function urlCartTabShouldApplyToFilterBar", self._app_js)
        fn = self._app_js[
            self._app_js.index("function urlCartTabShouldApplyToFilterBar")
            : self._app_js.index("function getCurrentNormalCartFilter")
        ]
        self.assertIn('t !== "all"', fn)

    def test_activate_page_uses_url_cart_tab_should_apply(self) -> None:
        block = self._app_js[
            self._app_js.index('if (visiblePage === "carts")')
            : self._app_js.index('if (visiblePage === "completed"')
        ]
        self.assertIn("urlCartTabShouldApplyToFilterBar(urlTab)", block)
        self.assertIn("getEffectiveNormalCartFilter()", block)

    def test_go_to_section_carts_does_not_force_all(self) -> None:
        block = self._app_js[
            self._app_js.index("window.goToSection")
            : self._app_js.index("window.applyCartTabFilters")
        ]
        self.assertIn('goTo("carts")', block)
        self.assertNotIn('goToCartTab("all")', block)

    def test_go_to_cart_tab_all_explicitly_sets_all(self) -> None:
        fn = self._app_js[
            self._app_js.index("window.goToCartTab")
            : self._app_js.index("window.goToSection")
        ]
        self.assertIn('tab === "all"', fn)
        self.assertIn('source: "nav_all"', fn)

    def test_lazy_reapply_ignores_tab_all(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function reapplyNormalCartFilterAfterRender")
            : self._lazy_js.index("function applyNormalCarts")
        ]
        self.assertIn("urlCartTabShouldApplyToFilterBar", fn)
        self.assertIn("getEffectiveNormalCartFilter", fn)

    def test_session_storage_key_present(self) -> None:
        self.assertIn("ma_normal_cart_filter_v1", self._app_js)
        self.assertIn("readPersistedNormalCartFilterFromStorage", self._app_js)


if __name__ == "__main__":
    unittest.main()
