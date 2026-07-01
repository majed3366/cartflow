# -*- coding: utf-8 -*-
"""Dashboard Carts UI Stability & Copy Sweep V1 — filter, counters, deprecated copy."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any


def _read(rel: str) -> str:
    return (Path(__file__).resolve().parents[1] / rel).read_text(encoding="utf-8")


DEPRECATED = {
    "اطلب من العميل إكمال بيانات التواصل في الودجيت.": (
        "لا توجد وسيلة تواصل متاحة حالياً — سيبدأ التواصل تلقائياً عند توفر بيانات التواصل."
    ),
    "أضف رقم العميل ليكمل النظام المسار.": (
        "لا توجد وسيلة تواصل متاحة حالياً — سيبدأ التواصل تلقائياً عند توفر بيانات التواصل."
    ),
    "راجع السلة واتخذ إجراءً يدوياً عند الحاجة.": (
        "أوقف CartFlow المسار الآلي مؤقتاً بانتظار إزالة العائق أو اكتمال البيانات."
    ),
    "راجع إعدادات الاسترجاع أو انتظر اكتمال بيانات السلة.": (
        "بانتظار اكتمال بيانات السلة — سيتابع CartFlow تلقائياً عند الجاهزية."
    ),
}


def _sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    wn = str(row.get("customer_lifecycle_what_next_ar") or "")
    repl = DEPRECATED.get(wn)
    if not repl:
        return row
    out = dict(row)
    out["customer_lifecycle_what_next_ar"] = repl
    return out


def _effective_filter_counts(
    incoming: dict[str, Any] | None,
    page_rows: list[dict[str, Any]],
    last_fc: dict[str, Any],
) -> dict[str, Any]:
    fc = dict(incoming or {})
    rows_n = len(page_rows)
    if not rows_n:
        return fc
    try:
        incoming_all = int(fc.get("all") or 0)
    except (TypeError, ValueError):
        incoming_all = 0
    try:
        prev_all = int(last_fc.get("all") or 0)
    except (TypeError, ValueError):
        prev_all = 0
    if incoming_all <= 0 and prev_all > 0:
        return dict(last_fc)
    return fc


class _FilterClientSim:
    """Mirror merchant_app filter persistence + lazy reapply rules."""

    def __init__(self) -> None:
        self.current: str | None = None
        self.applied: list[tuple[str, bool]] = []
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
        self.applied.append((mode, persist))

    def filter_btn_click(self, data_filter: str) -> None:
        self.set_current(data_filter)
        self.applied.append((self.current or "all", True))

    def activate_carts_page(self, parsed_cart_tab: str, url_tab: str | None = None) -> None:
        if url_tab:
            self.apply_cart_tab_filters(url_tab, persist=True)
        elif self.current:
            self.apply_cart_tab_filters(self.current, persist=False)
        else:
            self.apply_cart_tab_filters(parsed_cart_tab or "all", persist=True)

    def reapply_after_render(self) -> None:
        if self.hash_page == "#completed":
            self.applied.append(("__completed_refresh__", False))
            return
        if self.hash_tab:
            self.apply_cart_tab_filters(self.hash_tab, persist=True)
            return
        if self.current:
            self.apply_cart_tab_filters(self.current, persist=False)
        else:
            self.apply_cart_tab_filters("all", persist=True)


class DashboardCartsUiStabilityV1FilterTests(unittest.TestCase):
    def test_sent_filter_survives_successful_fetch(self) -> None:
        sim = _FilterClientSim()
        sim.filter_btn_click("sent")
        sim.applied.clear()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "sent")
        self.assertEqual([m for m, _ in sim.applied], ["sent"])

    def test_attention_filter_survives_retry(self) -> None:
        sim = _FilterClientSim()
        sim.filter_btn_click("attention")
        sim.applied.clear()
        sim.reapply_after_render()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "attention")
        self.assertEqual([m for m, _ in sim.applied], ["attention", "attention"])

    def test_background_fetch_does_not_force_all(self) -> None:
        sim = _FilterClientSim()
        sim.filter_btn_click("recovered")
        sim.applied.clear()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "recovered")
        self.assertNotIn("all", [m for m, _ in sim.applied])

    def test_cache_hydrate_reapply_does_not_override_selected_filter(self) -> None:
        sim = _FilterClientSim()
        sim.filter_btn_click("sent")
        sim.applied.clear()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "sent")
        persist_calls = [p for _, p in sim.applied]
        self.assertIn(False, persist_calls)

    def test_activate_page_hash_all_does_not_wipe_persisted_sent(self) -> None:
        sim = _FilterClientSim()
        sim.filter_btn_click("sent")
        sim.applied.clear()
        sim.activate_carts_page(parsed_cart_tab="all", url_tab=None)
        self.assertEqual(sim.current, "sent")
        self.assertEqual(sim.applied, [("sent", False)])

    def test_go_to_cart_tab_all_still_intentionally_sets_all(self) -> None:
        sim = _FilterClientSim()
        sim.filter_btn_click("sent")
        sim.apply_cart_tab_filters("all", persist=True)
        sim.applied.clear()
        sim.reapply_after_render()
        self.assertEqual(sim.current, "all")
        self.assertEqual([m for m, _ in sim.applied], ["all"])

    def test_completed_hash_unaffected(self) -> None:
        sim = _FilterClientSim()
        sim.filter_btn_click("attention")
        sim.hash_page = "#completed"
        sim.applied.clear()
        sim.reapply_after_render()
        self.assertEqual(sim.applied, [("__completed_refresh__", False)])
        self.assertEqual(sim.current, "attention")


class DashboardCartsUiStabilityV1DegradedTests(unittest.TestCase):
    def test_degraded_empty_does_not_clear_rows_or_counters(self) -> None:
        rows = [{"recovery_key": "store:cart-1"}]
        last_fc = {"all": 50, "sent": 10}
        fc = _effective_filter_counts({}, rows, last_fc)
        self.assertEqual(fc["all"], 50)
        self.assertEqual(len(rows), 1)

    def test_confirmed_empty_can_zero_counters(self) -> None:
        fc = _effective_filter_counts({"all": 0}, [], {"all": 50})
        self.assertEqual(fc.get("all"), 0)


class DashboardCartsUiStabilityV1CopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._pairs = list(DEPRECATED.items())

    def test_all_deprecated_strings_replaced(self) -> None:
        for old, new in self._pairs:
            row = {"customer_lifecycle_what_next_ar": old}
            out = _sanitize_row(row)
            self.assertEqual(out["customer_lifecycle_what_next_ar"], new)

    def test_unknown_copy_unchanged(self) -> None:
        row = {"customer_lifecycle_what_next_ar": "نص حالي صحيح."}
        out = _sanitize_row(row)
        self.assertEqual(out["customer_lifecycle_what_next_ar"], "نص حالي صحيح.")

    def test_lazy_js_has_safety_map_and_cache_v2(self) -> None:
        js = _read("static/merchant_dashboard_lazy.js")
        self.assertIn("DEPRECATED_LIFECYCLE_WHAT_NEXT_AR", js)
        self.assertIn("function sanitizeNormalCartRowLifecycleCopy", js)
        self.assertIn('NORMAL_CARTS_CACHE_KEY = "ma_normal_carts_cache_v2"', js)
        for old in DEPRECATED:
            self.assertIn(old, js)


class DashboardCartsUiStabilityV1JsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app_js = _read("static/merchant_app.js")
        cls._lazy_js = _read("static/merchant_dashboard_lazy.js")

    def test_activate_page_respects_persisted_filter_over_parse_hash_all(self) -> None:
        block = self._app_js[
            self._app_js.index('if (visiblePage === "carts")')
            : self._app_js.index('if (visiblePage === "completed"')
        ]
        self.assertIn("getUrlCartTabFromHash()", block)
        self.assertIn("persist: false", block)
        self.assertIn('source: "persisted"', block)

    def test_apply_cart_tab_filters_supports_persist_flag(self) -> None:
        fn = self._app_js[
            self._app_js.index("function applyCartTabFilters")
            : self._app_js.index("function activatePage")
        ]
        self.assertIn("options.persist !== false", fn)
        self.assertIn("selected_filter_before", fn)

    def test_reapply_uses_persist_false_for_stored_filter(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function reapplyNormalCartFilterAfterRender")
            : self._lazy_js.index("function applyNormalCarts")
        ]
        self.assertIn("persist: false", fn)
        self.assertIn('source: "persisted_reapply"', fn)

    def test_render_preserves_counts_when_degraded(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function renderNormalCartsTables")
            : self._lazy_js.index("function reapplyNormalCartFilterAfterRender")
        ]
        self.assertIn("effectiveFilterCounts", fn)

    def test_apply_normal_carts_sanitizes_before_render(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function applyNormalCarts")
            : self._lazy_js.index("function fetchNormalCarts")
        ]
        self.assertIn("prepareNormalCartsPayload", fn)


if __name__ == "__main__":
    unittest.main()
