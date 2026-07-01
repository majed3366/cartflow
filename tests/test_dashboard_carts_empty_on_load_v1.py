# -*- coding: utf-8 -*-
"""Dashboard Carts Empty-On-Load Fix V1 — #carts must not depend on #completed."""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any


def _read(rel: str) -> str:
    return (Path(__file__).resolve().parents[1] / rel).read_text(encoding="utf-8")


def _normal_carts_is_degraded(d: dict[str, Any] | None) -> bool:
    if not d:
        return True
    if d.get("dashboard_partial") or d.get("dashboard_timeout"):
        return True
    if d.get("snapshot_degraded") or d.get("snapshot_stale"):
        return True
    snap = d.get("_snapshot") if isinstance(d.get("_snapshot"), dict) else {}
    if snap.get("degraded") or snap.get("stale"):
        return True
    perf = d.get("_perf") if isinstance(d.get("_perf"), dict) else {}
    if perf.get("partial") or perf.get("degraded"):
        return True
    return False


def _payload_partial_or_thin(d: dict[str, Any] | None) -> bool:
    if not d:
        return True
    if _normal_carts_is_degraded(d):
        return True
    if d.get("snapshot_stale") or d.get("snapshot_degraded"):
        return True
    if d.get("dashboard_partial") or d.get("dashboard_timeout"):
        return True
    snap = d.get("_snapshot") if isinstance(d.get("_snapshot"), dict) else {}
    return bool(snap.get("degraded") or snap.get("stale"))


def _count_all(fc: dict[str, Any] | None) -> int:
    try:
        return int((fc or {}).get("all") or 0)
    except (TypeError, ValueError):
        return 0


def _filter_counts_explicit_zero(fc: dict[str, Any] | None) -> bool:
    if not fc or not isinstance(fc, dict):
        return False
    try:
        n = int(fc.get("all"))
    except (TypeError, ValueError):
        return False
    return n == 0


def _payload_source(d: dict[str, Any] | None) -> str:
    if not d:
        return "unknown"
    if d.get("__ma_payload_source"):
        return str(d["__ma_payload_source"])
    if d.get("snapshot_mode") or d.get("_snapshot"):
        return "snapshot"
    if _normal_carts_is_degraded(d):
        return "degraded"
    return "fetch"


def _is_confirmed_full_empty(d: dict[str, Any], page_rows: list[dict[str, Any]]) -> bool:
    if page_rows:
        return False
    if _payload_partial_or_thin(d):
        return False
    if not _filter_counts_explicit_zero(d.get("merchant_cart_filter_counts")):
        return False
    src = _payload_source(d)
    if src == "snapshot" or d.get("snapshot_mode"):
        return False
    if d.get("_snapshot"):
        return False
    return True


def _should_reject_thin(
    d: dict[str, Any],
    page_rows: list[dict[str, Any]],
    last_rows: list[dict[str, Any]],
    last_fc: dict[str, Any],
) -> bool:
    prev_n = len(last_rows)
    if prev_n < 1:
        return False
    incoming_n = len(page_rows)
    incoming_all = _count_all(d.get("merchant_cart_filter_counts"))
    if incoming_n == 0 and not _payload_partial_or_thin(d) and incoming_all == 0:
        return False
    if incoming_n >= prev_n:
        return False
    prev_all = _count_all(last_fc) or prev_n
    partial = _payload_partial_or_thin(d)
    count_suspect = incoming_all <= 0 or incoming_all < prev_all or incoming_all < incoming_n
    return incoming_n < prev_n and (partial or count_suspect)


class _NormalCartsClientSim:
    """Mirror applyNormalCarts with Empty-On-Load Fix V1 guards."""

    def __init__(self) -> None:
        self.last_rows: list[dict[str, Any]] = []
        self.last_fc: dict[str, int] = {}
        self.applied_gen = 0
        self.ui_state = "unknown"

    def apply(self, d: dict[str, Any], fetch_gen: int) -> str:
        if not d or not d.get("ok"):
            return "skip_not_ok"
        if fetch_gen < self.applied_gen:
            return "stale_skip"
        page_rows = list(d.get("merchant_carts_page_rows") or [])
        degraded = _normal_carts_is_degraded(d)
        if degraded and not page_rows:
            if self.last_rows:
                self.ui_state = "memory_keep"
                return "partial_keep"
            self.ui_state = "loading"
            return "partial_loading"
        if not page_rows and not degraded:
            if _count_all(d.get("merchant_cart_filter_counts")) > 0:
                self.ui_state = "loading" if not self.last_rows else "memory_keep"
                return "empty_mismatch_retry"
        if _should_reject_thin(d, page_rows, self.last_rows, self.last_fc):
            self.ui_state = "loading" if not self.last_rows else "memory_keep"
            return "thin_keep"
        if not page_rows and not _is_confirmed_full_empty(d, page_rows):
            self.ui_state = "loading" if not self.last_rows else "memory_keep"
            return "unconfirmed_empty"
        self.last_rows = page_rows
        self.last_fc = dict(d.get("merchant_cart_filter_counts") or {})
        self.applied_gen = max(self.applied_gen, fetch_gen)
        self.ui_state = "empty" if not page_rows else "rows"
        return "applied"


def _sample_rows(n: int, *, bucket: str = "sent") -> list[dict[str, Any]]:
    return [
        {
            "recovery_key": f"store:cart-{i}",
            "merchant_cart_bucket": bucket,
            "merchant_cart_visible_tabs": [bucket],
        }
        for i in range(n)
    ]


class DashboardCartsEmptyOnLoadV1BehaviorTests(unittest.TestCase):
    def test_cold_start_snapshot_empty_not_confirmed_shows_loading(self) -> None:
        sim = _NormalCartsClientSim()
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "snapshot_mode": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {"all": 0},
                },
                1,
            ),
            "unconfirmed_empty",
        )
        self.assertEqual(len(sim.last_rows), 0)
        self.assertEqual(sim.ui_state, "loading")

    def test_cold_start_degraded_empty_shows_loading(self) -> None:
        sim = _NormalCartsClientSim()
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "snapshot_degraded": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {},
                },
                1,
            ),
            "partial_loading",
        )
        self.assertEqual(sim.ui_state, "loading")

    def test_cold_start_valid_response_renders_rows(self) -> None:
        sim = _NormalCartsClientSim()
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "merchant_carts_page_rows": _sample_rows(12),
                    "merchant_cart_filter_counts": {"all": 12, "sent": 12},
                },
                1,
            ),
            "applied",
        )
        self.assertEqual(len(sim.last_rows), 12)
        self.assertEqual(sim.ui_state, "rows")

    def test_confirmed_live_empty_still_applies(self) -> None:
        sim = _NormalCartsClientSim()
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {"all": 0},
                },
                1,
            ),
            "applied",
        )
        self.assertEqual(len(sim.last_rows), 0)
        self.assertEqual(sim.ui_state, "empty")

    def test_unconfirmed_then_valid_populates_without_completed_tab(self) -> None:
        sim = _NormalCartsClientSim()
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "snapshot_mode": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {"all": 0},
                },
                1,
            ),
            "unconfirmed_empty",
        )
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "merchant_carts_page_rows": _sample_rows(8),
                    "merchant_cart_filter_counts": {"all": 8, "sent": 8},
                },
                2,
            ),
            "applied",
        )
        self.assertEqual(len(sim.last_rows), 8)

    def test_cold_start_thin_empty_degraded_shows_loading_not_empty(self) -> None:
        sim = _NormalCartsClientSim()
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "snapshot_stale": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {"all": 0},
                    "_snapshot": {"stale": True},
                },
                1,
            ),
            "partial_loading",
        )
        self.assertEqual(sim.ui_state, "loading")
        self.assertEqual(len(sim.last_rows), 0)

    def test_thin_keep_with_prior_memory_shows_loading_when_memory_cleared(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(5),
                "merchant_cart_filter_counts": {"all": 5},
            },
            1,
        )
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "merchant_carts_page_rows": _sample_rows(1),
                    "merchant_cart_filter_counts": {},
                },
                2,
            ),
            "thin_keep",
        )
        self.assertEqual(len(sim.last_rows), 5)
        self.assertEqual(sim.ui_state, "memory_keep")

    def test_ambiguous_fc_without_explicit_zero_is_unconfirmed(self) -> None:
        sim = _NormalCartsClientSim()
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {},
                },
                1,
            ),
            "unconfirmed_empty",
        )
        self.assertEqual(sim.ui_state, "loading")


class DashboardCartsEmptyOnLoadV1JsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._lazy_js = _read("static/merchant_dashboard_lazy.js")

    def test_lazy_js_has_confirmed_empty_gate(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function applyNormalCarts")
            : self._lazy_js.index("function fetchNormalCarts")
        ]
        self.assertIn("normalCartsIsConfirmedFullEmpty", fn)
        self.assertIn("normal_carts_unconfirmed_empty", fn)
        self.assertIn("__ma_confirmed_empty", fn)

    def test_render_guards_empty_state(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function renderNormalCartsTables")
            : self._lazy_js.index("function reapplyNormalCartFilterAfterRender")
        ]
        self.assertIn("confirmedEmpty", fn)
        self.assertIn("showNormalCartsLoadingState", fn)

    def test_boot_calls_ensure_not_only_completed(self) -> None:
        boot = self._lazy_js[
            self._lazy_js.index("function bootLazyDashboard")
            : self._lazy_js.index("window.maApplyVipCartsPayload")
        ]
        self.assertIn("ensureNormalCartsPageReady", boot)
        self.assertIn('fetchNormalCarts("boot_priority")', boot)

    def test_completed_tab_fetch_is_supplemental(self) -> None:
        self.assertIn('fetchNormalCarts("completed_tab_retry")', self._lazy_js)
        self.assertIn("function ensureNormalCartsPageReady", self._lazy_js)
        self.assertIn("window.maEnsureNormalCartsPageReady", self._lazy_js)

    def test_thin_reject_empty_memory_uses_loading_in_js(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function applyNormalCarts")
            : self._lazy_js.index("function fetchNormalCarts")
        ]
        thin = fn[fn.index("normal_carts_thin_reject") : fn.index("if (!pageRows.length && !normalCartsIsConfirmedFullEmpty")]
        self.assertIn("showNormalCartsLoadingState", thin)
        self.assertIn("lastNormalCartsPageRows.length", thin)

    def test_rerender_empty_memory_shows_loading(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function rerenderCartsFromMemory")
            : self._lazy_js.index("function syncCartsPageOnHashChange")
        ]
        self.assertIn("showNormalCartsLoadingState", fn)


if __name__ == "__main__":
    unittest.main()
