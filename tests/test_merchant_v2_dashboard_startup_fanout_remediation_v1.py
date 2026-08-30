# -*- coding: utf-8 -*-
"""Merchant V2 dashboard startup fan-out remediation V1 — active-surface budget."""
from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(
    encoding="utf-8"
)
SUB_JS = (ROOT / "static" / "merchant_subscription.js").read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")


class MerchantV2DashboardStartupFanoutRemediationV1Tests(unittest.TestCase):
    def test_router_uses_canonical_hash_surface(self) -> None:
        self.assertIn("function currentHash()", APP_JS)
        self.assertIn("SETTINGS_HASH_ALIASES", APP_JS)
        self.assertIn("loadSection(currentHash())", APP_JS)
        self.assertIn("currentHash: currentHash", APP_JS)
        self.assertNotIn("location.pathname", APP_JS)

    def test_lazy_surface_init_is_one_shot_unless_forced(self) -> None:
        self.assertIn("SURFACE_PRODUCT_INIT", APP_JS)
        self.assertIn("function initSurfaceProductData(section, opts)", APP_JS)
        self.assertIn("SURFACE_PRODUCT_INIT[section] && !force", APP_JS)
        self.assertIn("initSurfaceProductData(section, opts)", APP_JS)
        self.assertIn("loadSection(id, { force: true })", APP_JS)
        self.assertIn("CartFlowUiV2Home.loadAndPaint", APP_JS)
        self.assertIn("CartFlowUiV2Workspace.loadAndPaint", APP_JS)
        self.assertIn("CartFlowUiV2Carts.loadAndPaint", APP_JS)
        self.assertIn("CartFlowUiV2Comms.loadAndPaint", APP_JS)
        self.assertIn("CartFlowUiV2Settings.loadAndPaint", APP_JS)
        home_calls = APP_JS.count("CartFlowUiV2Home.loadAndPaint")
        ws_calls = APP_JS.count("CartFlowUiV2Workspace.loadAndPaint")
        carts_calls = APP_JS.count("CartFlowUiV2Carts.loadAndPaint")
        comms_calls = APP_JS.count("CartFlowUiV2Comms.loadAndPaint")
        settings_calls = APP_JS.count("CartFlowUiV2Settings.loadAndPaint")
        self.assertEqual(home_calls, 1)
        self.assertEqual(ws_calls, 1)
        self.assertEqual(carts_calls, 1)
        self.assertEqual(comms_calls, 1)
        self.assertEqual(settings_calls, 1)

    def test_owned_startup_reads_remain_surface_local(self) -> None:
        self.assertIn('fetch("/api/dashboard/summary"', HOME_JS)
        self.assertIn('fetch("/api/cart-workspace/v1/projection"', WS_JS)
        self.assertIn('fetch("/api/dashboard/normal-carts"', CARTS_JS)
        self.assertIn('fetchJson("/api/dashboard/messages")', COMMS_JS)
        self.assertIn('fetchJson("/api/dashboard/followups")', COMMS_JS)
        self.assertIn('fetchJson("/api/dashboard/summary")', COMMS_JS)
        self.assertIn('jsonGet("/api/merchant/store-connection")', SETTINGS_JS)
        self.assertIn('jsonGet("/api/recovery-settings")', SETTINGS_JS)
        self.assertNotIn("/api/cart-workspace/v1/projection", HOME_JS)
        self.assertNotIn("/api/dashboard/normal-carts", HOME_JS)
        self.assertNotIn("/api/dashboard/messages", HOME_JS)
        self.assertNotIn("/api/merchant/store-connection", HOME_JS)
        self.assertNotIn("/api/dashboard/summary", WS_JS)
        self.assertNotIn("/api/dashboard/normal-carts", WS_JS)
        self.assertNotIn("/api/dashboard/messages", CARTS_JS)
        self.assertNotIn("/api/cart-workspace/v1/projection", COMMS_JS)
        self.assertNotIn("/api/dashboard/normal-carts", SETTINGS_JS)
        self.assertNotIn("/api/cart-workspace/v1/projection", SETTINGS_JS)

    def test_subscription_bind_is_settings_active_only(self) -> None:
        self.assertIn("function settingsSurfaceActive()", SUB_JS)
        self.assertIn("if (settingsSurfaceActive())", SUB_JS)
        self.assertIn("if (loaded && !(opts && opts.force)) return", SUB_JS)
        self.assertIn("if (!settingsSurfaceActive()) return", SUB_JS)
        self.assertNotIn(
            "bound = true;\n    loadSubscription();",
            SUB_JS,
        )
        bind_idx = SUB_JS.index("function bind()")
        bind_body = SUB_JS[bind_idx : bind_idx + 420]
        self.assertIn("if (settingsSurfaceActive())", bind_body)
        self.assertIn("loadSubscription()", bind_body)
        self.assertNotIn("h.indexOf(\"#settings\")", bind_body)

    def test_settings_queuepool_remediation_preserved(self) -> None:
        self.assertIn("settings-queuepool-pressure-remediation-v1", SETTINGS_JS)
        self.assertIn("loadOverviewTruth", SETTINGS_JS)
        self.assertIn("paintFirstOverview", SETTINGS_JS)
        self.assertIn("initDetail", SETTINGS_JS)
        self.assertNotIn("Promise.all", SETTINGS_JS)
        self.assertNotIn("initExisting", SETTINGS_JS)
        self.assertNotIn("scope=vip", SETTINGS_JS)
        self.assertNotIn("scope=general", SETTINGS_JS)
        self.assertIn("qpool1", V2_HTML)
        self.assertIn("nvis1", V2_HTML)
        self.assertIn("fanout1", V2_HTML)

    def test_communication_active_surface_promise_all_preserved(self) -> None:
        self.assertIn("Promise.all([", COMMS_JS)
        self.assertIn('fetchJson("/api/dashboard/messages")', COMMS_JS)
        self.assertIn('fetchJson("/api/dashboard/followups")', COMMS_JS)
        self.assertIn('fetchJson("/api/dashboard/summary")', COMMS_JS)

    def test_request_map_harness_active_surface_only(self) -> None:
        script = (
            ROOT
            / "docs"
            / "ops"
            / "merchant_v2_dashboard_startup_fanout_remediation_v1"
            / "_request_map.js"
        )
        raw = subprocess.check_output(["node", str(script)], cwd=str(ROOT), text=True)
        data = json.loads(raw)
        self.assertEqual(data["home_active"], ["/api/dashboard/summary"])
        self.assertEqual(data["nav_workspace"], ["/api/cart-workspace/v1/projection"])
        self.assertEqual(data["nav_carts"], ["/api/dashboard/normal-carts"])
        self.assertEqual(
            data["nav_comms"],
            [
                "/api/dashboard/messages",
                "/api/dashboard/followups",
                "/api/dashboard/summary",
            ],
        )
        self.assertEqual(
            data["nav_settings"],
            [
                "/api/merchant/subscription",
                "/api/merchant/store-connection",
                "/api/recovery-settings",
            ],
        )
        self.assertEqual(data["return_visits"], [])
        self.assertEqual(
            data["workspace_active_only"],
            ["/api/cart-workspace/v1/projection"],
        )
        self.assertEqual(data["carts_active_only"], ["/api/dashboard/normal-carts"])
        self.assertEqual(
            data["comms_active_only"],
            [
                "/api/dashboard/messages",
                "/api/dashboard/followups",
                "/api/dashboard/summary",
            ],
        )
        self.assertEqual(
            data["settings_active_only"],
            [
                "/api/merchant/subscription",
                "/api/merchant/store-connection",
                "/api/recovery-settings",
            ],
        )
        self.assertEqual(data["two_home_viewports"]["a"], ["/api/dashboard/summary"])
        self.assertEqual(data["two_home_viewports"]["b"], ["/api/dashboard/summary"])

    def test_ping_health_login_remain_responsive(self) -> None:
        c = TestClient(app)
        ping = c.get("/ping")
        self.assertEqual(ping.status_code, 200)
        self.assertTrue((ping.json() or {}).get("ok"))
        health = c.get("/health?db=1")
        self.assertEqual(health.status_code, 200, health.text)
        self.assertTrue((health.json() or {}).get("ok"))
        login = c.get("/login")
        self.assertEqual(login.status_code, 200)
        self.assertIn("ma-auth-form", login.text)

    def test_dashboard_hosts_fanout_cache_bust(self) -> None:
        prev = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            html = TestClient(app).get("/dashboard?cf_ui=v2").text
            self.assertIn("merchant_ui_v2_app.js", html)
            self.assertIn("nvis1-fanout1", html)
            self.assertIn("setcomp1-fanout1", html)
            self.assertIn("qpool1", html)
            self.assertIn("merchant_ui_v2_settings.js", html)
            self.assertIn("merchant_subscription.js", html)
            self.assertNotIn("merchant_dashboard_lazy.js", html)
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev


if __name__ == "__main__":
    unittest.main()
