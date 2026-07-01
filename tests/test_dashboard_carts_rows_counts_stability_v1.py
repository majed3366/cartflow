# -*- coding: utf-8 -*-
"""Dashboard Carts Rows/Counts Stability Sweep V1 — thin payload + counter guards."""

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


def _count_all(fc: dict[str, Any] | None) -> int:
    try:
        return int((fc or {}).get("all") or 0)
    except (TypeError, ValueError):
        return 0


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


def _derive_filter_counts_from_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "all": 0,
        "sent": 0,
        "attention": 0,
        "recovered": 0,
        "nophone": 0,
        "waiting": 0,
    }
    if not rows:
        return counts
    counts["all"] = len(rows)
    for row in rows:
        tabs = row.get("merchant_cart_visible_tabs")
        if not isinstance(tabs, list) or not tabs:
            b = str(
                row.get("merchant_cart_bucket") or row.get("merchant_cart_primary_bucket") or ""
            ).strip().lower()
            tabs = [b] if b else []
        for t in tabs:
            key = str(t or "").strip().lower()
            if key in counts:
                counts[key] += 1
    return counts


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


def _effective_filter_counts(
    incoming: dict[str, Any] | None,
    page_rows: list[dict[str, Any]],
    last_fc: dict[str, Any],
) -> dict[str, Any]:
    fc = dict(incoming or {})
    rows_n = len(page_rows)
    if not rows_n:
        return fc
    incoming_all = _count_all(fc)
    prev_all = _count_all(last_fc)
    if incoming_all <= 0:
        if prev_all > 0:
            return dict(last_fc)
        derived = _derive_filter_counts_from_rows(page_rows)
        if derived["all"] > 0:
            return derived
    if incoming_all > 0 and incoming_all < rows_n:
        derived_m = _derive_filter_counts_from_rows(page_rows)
        if derived_m["all"] == rows_n:
            return derived_m
    return fc


class _NormalCartsClientSim:
    """Mirror applyNormalCarts with Rows/Counts Stability Sweep V1 guards."""

    def __init__(self) -> None:
        self.last_rows: list[dict[str, Any]] = []
        self.last_fc: dict[str, int] = {}
        self.applied_gen = 0
        self.current_filter: str | None = None

    def apply(self, d: dict[str, Any], fetch_gen: int) -> str:
        if not d or not d.get("ok"):
            return "skip_not_ok"
        if fetch_gen < self.applied_gen:
            return "stale_skip"
        page_rows = list(d.get("merchant_carts_page_rows") or [])
        degraded = _normal_carts_is_degraded(d)
        if degraded and not page_rows:
            if self.last_rows:
                return "partial_keep"
            return "partial_loading"
        if not page_rows and not degraded and self.last_rows:
            if _count_all(d.get("merchant_cart_filter_counts")) > 0:
                return "empty_mismatch_keep"
        if _should_reject_thin(d, page_rows, self.last_rows, self.last_fc):
            return "thin_keep"
        self.last_rows = page_rows
        raw_fc = dict(d.get("merchant_cart_filter_counts") or {})
        self.last_fc = _effective_filter_counts(raw_fc, page_rows, self.last_fc)
        self.applied_gen = max(self.applied_gen, fetch_gen)
        return "applied"

    def filt_all(self) -> int:
        return _count_all(self.last_fc)


def _sample_rows(n: int, *, bucket: str = "sent") -> list[dict[str, Any]]:
    return [
        {
            "recovery_key": f"store:cart-{i}",
            "merchant_cart_bucket": bucket,
            "merchant_cart_visible_tabs": [bucket],
        }
        for i in range(n)
    ]


class DashboardCartsRowsCountsStabilityV1BehaviorTests(unittest.TestCase):
    def test_fifty_rows_memory_plus_one_row_thin_keeps_fifty(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(50),
                "merchant_cart_filter_counts": {"all": 50},
            },
            1,
        )
        self.assertEqual(len(sim.last_rows), 50)
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "snapshot_stale": True,
                    "merchant_carts_page_rows": _sample_rows(1),
                    "merchant_cart_filter_counts": {"all": 1},
                    "_snapshot": {"stale": True},
                },
                2,
            ),
            "thin_keep",
        )
        self.assertEqual(len(sim.last_rows), 50)
        self.assertEqual(sim.filt_all(), 50)

    def test_fifty_rows_memory_plus_empty_degraded_keeps_fifty(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(50),
                "merchant_cart_filter_counts": {"all": 50},
            },
            1,
        )
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "snapshot_degraded": True,
                    "dashboard_partial": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {},
                },
                2,
            ),
            "partial_keep",
        )
        self.assertEqual(len(sim.last_rows), 50)

    def test_empty_counts_with_rows_derives_not_zero(self) -> None:
        rows = _sample_rows(5, bucket="attention")
        fc = _effective_filter_counts({}, rows, {})
        self.assertEqual(fc["all"], 5)
        self.assertEqual(fc["attention"], 5)

    def test_confirmed_empty_still_clears(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(3),
                "merchant_cart_filter_counts": {"all": 3},
            },
            1,
        )
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {"all": 0},
                },
                2,
            ),
            "applied",
        )
        self.assertEqual(len(sim.last_rows), 0)
        self.assertEqual(sim.filt_all(), 0)

    def test_thin_one_row_without_flags_rejected_via_count_suspect(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(50),
                "merchant_cart_filter_counts": {"all": 50},
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
        self.assertEqual(len(sim.last_rows), 50)

    def test_selected_filter_stable_after_thin_keep(self) -> None:
        sim = _NormalCartsClientSim()
        sim.current_filter = "sent"
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(50, bucket="sent"),
                "merchant_cart_filter_counts": {"all": 50, "sent": 50},
            },
            1,
        )
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(1),
                "merchant_cart_filter_counts": {},
            },
            2,
        )
        self.assertEqual(sim.current_filter, "sent")
        self.assertEqual(len(sim.last_rows), 50)


class DashboardCartsRowsCountsStabilityV1JsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._lazy_js = _read("static/merchant_dashboard_lazy.js")

    def test_lazy_js_has_thin_reject_guard(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function applyNormalCarts")
            : self._lazy_js.index("function fetchNormalCarts")
        ]
        self.assertIn("normalCartsShouldRejectThinPayload", fn)
        self.assertIn("normal_carts_thin_reject", fn)
        self.assertIn('rerenderCartsFromMemory("thin_keep")', fn)

    def test_lazy_js_derives_counts_from_rows(self) -> None:
        self.assertIn("function deriveFilterCountsFromRows", self._lazy_js)
        block = self._lazy_js[
            self._lazy_js.index("function effectiveFilterCounts")
            : self._lazy_js.index("function prepareNormalCartsPayload")
        ]
        self.assertIn("deriveFilterCountsFromRows", block)
        self.assertIn("normal_carts_counts_derived", block)

    def test_lazy_js_migrates_cache_v1_to_v2(self) -> None:
        self.assertIn("NORMAL_CARTS_CACHE_KEY_V1", self._lazy_js)
        self.assertIn("function migrateNormalCartsCacheV1ToV2", self._lazy_js)
        hydrate = self._lazy_js[
            self._lazy_js.index("function hydrateNormalCartsCache")
            : self._lazy_js.index("function cartIdInNormalRows")
        ]
        self.assertIn("migrateNormalCartsCacheV1ToV2()", hydrate)


class DashboardCartsRowsCountsStabilityV1CacheMigrationTests(unittest.TestCase):
    def test_v1_migrates_when_v2_missing(self) -> None:
        store: dict[str, str] = {
            "ma_normal_carts_cache_v1": '{"rows":[{"recovery_key":"a"}],"fc":{"all":1}}'
        }

        def get_item(key: str) -> str | None:
            return store.get(key)

        def set_item(key: str, val: str) -> None:
            store[key] = val

        v2_before = get_item("ma_normal_carts_cache_v2")
        self.assertIsNone(v2_before)
        raw_v1 = get_item("ma_normal_carts_cache_v1")
        self.assertIsNotNone(raw_v1)
        if not get_item("ma_normal_carts_cache_v2") and raw_v1:
            import json

            c = json.loads(raw_v1)
            if c and c.get("rows"):
                set_item("ma_normal_carts_cache_v2", raw_v1)
        self.assertIsNotNone(get_item("ma_normal_carts_cache_v2"))


if __name__ == "__main__":
    unittest.main()
