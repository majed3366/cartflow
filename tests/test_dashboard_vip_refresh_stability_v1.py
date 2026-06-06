# -*- coding: utf-8 -*-
"""VIP dashboard refresh row stability — cache hydrate + independent fetch."""

from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


class DashboardVipRefreshStabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._client = TestClient(app)
        self._lazy_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_dashboard_lazy.js"
        ).read_text(encoding="utf-8")

    def test_lazy_js_vip_cache_hydrate_on_boot(self) -> None:
        js = self._lazy_js
        self.assertIn("VIP_CARTS_CACHE_KEY", js)
        self.assertIn("hydrateVipCartsCache", js)
        self.assertIn("persistVipCartsCache", js)
        self.assertIn("vip_carts_cache_hydrate", js)
        boot_idx = js.index("function bootLazyDashboard")
        boot_body = js[boot_idx : boot_idx + 1200]
        self.assertIn("hydrateVipCartsCache()", boot_body)
        self.assertIn("hydrateNormalCartsCache()", boot_body)

    def test_lazy_js_vip_fetch_not_blocked_by_normal_carts(self) -> None:
        js = self._lazy_js
        boot_idx = js.index("function bootLazyDashboard")
        boot_body = js[boot_idx : boot_idx + 1800]
        self.assertIn("fetchVipCarts(", boot_body)
        finally_idx = boot_body.index(".finally(function")
        vip_in_finally = "fetchVipCarts" in boot_body[finally_idx:]
        self.assertFalse(
            vip_in_finally,
            "VIP fetch must not live inside normal-carts finally block",
        )
        self.assertNotIn(
            'fetch("/api/dashboard/vip-carts"',
            boot_body[finally_idx:],
        )

    def test_lazy_js_vip_partial_error_does_not_clear_rows(self) -> None:
        js = self._lazy_js
        self.assertIn("vip_carts_partial_empty", js)
        self.assertIn("vip_carts_stale_skip", js)
        self.assertIn("partial_keep", js)
        self.assertIn("ok_false_keep", js)
        self.assertIn("fetch_error_keep", js)
        self.assertIn("lastVipPageRows.length", js)
        self.assertIn("vipCartsHasRenderedRows", js)
        self.assertIn("rerenderVipFromMemory", js)

    def test_lazy_js_vip_empty_only_without_cached_rows(self) -> None:
        js = self._lazy_js
        apply_idx = js.index("function applyVipCarts(d, fetchGen)")
        apply_body = js[apply_idx : apply_idx + 3500]
        self.assertIn("vip_carts_empty_mismatch_retry", apply_body)
        self.assertIn("showVipCartsLoadingState", apply_body)
        render_idx = js.index("function renderVipCartsTables(d)")
        render_body = js[render_idx : render_idx + 1200]
        self.assertIn("vipPageEmptyHtml()", render_body)

    def test_lazy_js_hash_vip_prioritizes_fetch(self) -> None:
        js = self._lazy_js
        self.assertIn('hashRaw === "#vip"', js)
        self.assertIn('fetchVipCarts("hash_vip")', js)
        self.assertIn('fetchVipCarts(bootHash === "#vip" ? "boot_vip_hash" : "boot_parallel")', js)

    def test_lazy_js_exposes_vip_test_hooks(self) -> None:
        self.assertIn("__maVipCartsTestHooks", self._lazy_js)
        self.assertIn("maFetchVipCartsNow", self._lazy_js)

    def test_dashboard_vip_shell_has_skeleton_not_false_empty(self) -> None:
        r = self._client.get("/dashboard")
        self.assertEqual(r.status_code, 200, r.text[:400])
        html = r.text or ""
        self.assertIn('id="ma-tbody-vip-page"', html)
        self.assertIn("ma-dash-skel-row", html)
        self.assertNotIn("لا توجد سلال VIP نشطة تحتاج تدخلك الآن", html)


if __name__ == "__main__":
    unittest.main()
