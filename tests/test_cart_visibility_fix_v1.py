# -*- coding: utf-8 -*-
"""Cart visibility fix V1 — degraded empty must not wipe prior normal-carts rows."""
from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

from services.dashboard_snapshot_read_v1 import (
    _degraded_normal_carts_payload,
    apply_normal_carts_snapshot_client_guards,
)


def _normal_carts_is_degraded(d: dict[str, Any] | None) -> bool:
    """Mirror of static/merchant_dashboard_lazy.js normalCartsIsDegraded."""
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


class _NormalCartsClientSim:
    """Minimal applyNormalCarts state machine for regression tests."""

    def __init__(self) -> None:
        self.last_rows: list[dict[str, Any]] = []
        self.last_fc: dict[str, int] = {}
        self.applied_gen = 0

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
            fc = d.get("merchant_cart_filter_counts") or {}
            try:
                filter_all = int(fc.get("all") or 0)
            except (TypeError, ValueError):
                filter_all = 0
            if filter_all > 0:
                return "empty_mismatch_keep"
        self.last_rows = page_rows
        self.last_fc = dict(d.get("merchant_cart_filter_counts") or {})
        self.applied_gen = max(self.applied_gen, fetch_gen)
        return "applied"

    def filt_all(self) -> int:
        try:
            return int(self.last_fc.get("all") or 0)
        except (TypeError, ValueError):
            return 0


def _sample_rows(n: int) -> list[dict[str, Any]]:
    return [{"recovery_key": f"store:cart-{i}", "merchant_cart_value": 100 + i} for i in range(n)]


class CartVisibilityFixV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._lazy_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_dashboard_lazy.js"
        ).read_text(encoding="utf-8")

    def test_js_detects_snapshot_degraded_as_partial(self) -> None:
        js = self._lazy_js
        self.assertIn("snapshot_degraded", js)
        self.assertIn("snapshot_stale", js)
        self.assertIn("snap.degraded", js)
        self.assertIn("perf.partial", js)
        self.assertIn("normalCartsDegradedRetryStage", js)

    def test_degraded_normal_carts_payload_has_client_partial_flags(self) -> None:
        body = _degraded_normal_carts_payload(reason="no_snapshot")
        self.assertTrue(body.get("snapshot_degraded"))
        self.assertTrue(body.get("dashboard_partial"))
        self.assertTrue(body.get("dashboard_timeout"))
        self.assertEqual(body.get("dashboard_timeout_stage"), "no_snapshot")

    def test_apply_guards_adds_partial_flags_for_stale_empty_snapshot(self) -> None:
        body = apply_normal_carts_snapshot_client_guards(
            {
                "snapshot_degraded": True,
                "snapshot_reason": "stale_snapshot",
                "merchant_carts_page_rows": [],
                "merchant_cart_filter_counts": {},
                "_snapshot": {"stale": True, "degraded": True},
            }
        )
        self.assertTrue(body.get("dashboard_partial"))
        self.assertTrue(body.get("dashboard_timeout"))
        self.assertEqual(body.get("dashboard_timeout_stage"), "stale_snapshot")

    def test_apply_guards_skips_when_rows_present(self) -> None:
        body = apply_normal_carts_snapshot_client_guards(
            {
                "snapshot_degraded": True,
                "merchant_carts_page_rows": [{"recovery_key": "a"}],
            }
        )
        self.assertNotIn("dashboard_partial", body)

    def test_good_then_degraded_empty_keeps_rows_and_counts(self) -> None:
        sim = _NormalCartsClientSim()
        n = 3
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "merchant_carts_page_rows": _sample_rows(n),
                    "merchant_cart_filter_counts": {"all": n},
                },
                1,
            ),
            "applied",
        )
        self.assertEqual(len(sim.last_rows), n)
        self.assertEqual(sim.filt_all(), n)

        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "snapshot_degraded": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {},
                },
                2,
            ),
            "partial_keep",
        )
        self.assertEqual(len(sim.last_rows), n)
        self.assertEqual(sim.filt_all(), n)

    def test_degraded_empty_does_not_set_filt_all_zero_when_rows_retained(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(2),
                "merchant_cart_filter_counts": {"all": 2},
            },
            1,
        )
        sim.apply(
            {
                "ok": True,
                "snapshot_degraded": True,
                "snapshot_reason": "no_snapshot",
                "merchant_carts_page_rows": [],
                "merchant_cart_filter_counts": {"all": 0},
            },
            2,
        )
        self.assertEqual(sim.filt_all(), 2)

    def test_confirmed_full_empty_clears_rows(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(2),
                "merchant_cart_filter_counts": {"all": 2},
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

    def test_newer_degraded_empty_does_not_beat_older_good_stale_skip(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(4),
                "merchant_cart_filter_counts": {"all": 4},
            },
            5,
        )
        self.assertEqual(
            sim.apply(
                {
                    "ok": True,
                    "snapshot_degraded": True,
                    "merchant_carts_page_rows": [],
                    "merchant_cart_filter_counts": {},
                },
                4,
            ),
            "stale_skip",
        )
        self.assertEqual(len(sim.last_rows), 4)

    def test_tab_switch_memory_after_degraded_empty_keeps_rows(self) -> None:
        sim = _NormalCartsClientSim()
        sim.apply(
            {
                "ok": True,
                "merchant_carts_page_rows": _sample_rows(2),
                "merchant_cart_filter_counts": {"all": 2},
            },
            1,
        )
        sim.apply(
            {
                "ok": True,
                "snapshot_degraded": True,
                "merchant_carts_page_rows": [],
                "merchant_cart_filter_counts": {},
            },
            2,
        )
        # hashchange → rerenderCartsFromMemory uses last_rows unchanged
        self.assertEqual(len(sim.last_rows), 2)
        self.assertEqual(sim.filt_all(), 2)


if __name__ == "__main__":
    unittest.main()
