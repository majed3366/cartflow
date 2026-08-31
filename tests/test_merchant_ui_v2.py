# -*- coding: utf-8 -*-
"""Merchant UI V2 clean-slate vertical slice contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.merchant_ui_v2.flag_v1 import (
    DEFAULT_MERCHANT_UI_V2,
    FLAG_MERCHANT_UI_V2,
    merchant_ui_v2_requested,
)

ROOT = Path(__file__).resolve().parents[1]
V2_TEMPLATE = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
V1_TEMPLATE = (ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


class MerchantUiV2FlagTests(unittest.TestCase):
    def test_default_on_production_baseline(self) -> None:
        self.assertTrue(DEFAULT_MERCHANT_UI_V2)
        self.assertTrue(merchant_ui_v2_requested(query={}, cookies={}))

    def test_query_v2(self) -> None:
        self.assertTrue(merchant_ui_v2_requested(query={"cf_ui": "v2"}, cookies={}))

    def test_query_v1_rollback_overrides_default(self) -> None:
        self.assertFalse(merchant_ui_v2_requested(query={"cf_ui": "v1"}, cookies={}))

    def test_query_v1_overrides_cookie(self) -> None:
        self.assertFalse(
            merchant_ui_v2_requested(query={"cf_ui": "v1"}, cookies={"cf_ui_v2": "1"})
        )

    def test_cookie_v1_is_ignored_not_silent_rollback(self) -> None:
        self.assertTrue(
            merchant_ui_v2_requested(query={}, cookies={"cf_ui_v2": "0"})
        )

class MerchantUiV2TemplateTests(unittest.TestCase):
    def test_v2_namespace_and_no_legacy_css(self) -> None:
        self.assertIn('data-cf-ui="v2"', V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_ds.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_frame.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_language.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_home.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_workspace.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_carts.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_comms.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_language.js", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_carts.js", V2_TEMPLATE)
        self.assertNotIn("merchant_frame_v1.css", V2_TEMPLATE)
        self.assertNotIn("merchant_pe_v2.css", V2_TEMPLATE)
        self.assertNotIn("decision_workspace_visual_assimilation", V2_TEMPLATE)
        self.assertNotIn("merchant_experience_home_v1.css", V2_TEMPLATE)

    def test_v2_frame_separates_appbar_and_ctx(self) -> None:
        self.assertIn("cf2-chrome", V2_TEMPLATE)
        self.assertIn('data-cf2-appbar="shell-integration-v1"', V2_TEMPLATE)
        self.assertIn("cf2-utility", V2_TEMPLATE)
        self.assertIn("cf2-global", V2_TEMPLATE)
        self.assertIn('id="cf2-nav"', V2_TEMPLATE)
        self.assertIn('id="cf2-ctx-handle"', V2_TEMPLATE)
        self.assertIn("cf2-utility__account", V2_TEMPLATE)
        self.assertIn("cf2-utility__identity", V2_TEMPLATE)
        self.assertIn("cf2-utility__identity-name", V2_TEMPLATE)
        self.assertIn("cf2-menu-btn__bars", V2_TEMPLATE)
        self.assertIn("cf2-ctx", V2_TEMPLATE)
        self.assertIn("cf2-stage", V2_TEMPLATE)
        self.assertIn("cf2-drawer", V2_TEMPLATE)
        self.assertIn("cf2-nav", V2_TEMPLATE)
        self.assertNotIn("cf2-global-btn", V2_TEMPLATE)
        self.assertNotIn("cf2-global-panel", V2_TEMPLATE)
        self.assertNotIn("cf2-drawer-global", V2_TEMPLATE)
        self.assertNotIn("cf2-appbar__section", V2_TEMPLATE)
        self.assertNotIn("cf2-page-chrome", V2_TEMPLATE)
        self.assertNotIn("cf2-ctx-btn", V2_TEMPLATE)
        self.assertNotIn("👤", V2_TEMPLATE)
        self.assertNotIn(">الباقة<", V2_TEMPLATE)
        self.assertNotIn('href="/logout">خروج', V2_TEMPLATE)

    def test_v2_slice_pages_only(self) -> None:
        self.assertIn('data-cf2-page="home"', V2_TEMPLATE)
        self.assertIn('data-cf2-page="workspace"', V2_TEMPLATE)
        self.assertIn("ماذا يجب أن أعرف الآن عن متجري؟", V2_TEMPLATE)
        self.assertIn("ما القرار الذي يجب أن أتخذه الآن، ولماذا؟", V2_TEMPLATE)
        self.assertIn("ماذا حدث في التواصل مع العملاء، وما الذي يحتاج متابعتي الآن؟", V2_TEMPLATE)
        self.assertIn('id="cf2-comms-root"', V2_TEMPLATE)
        self.assertNotIn("قسم التواصل خارج شريحة V2", V2_TEMPLATE)

    def test_v1_unchanged_default_template(self) -> None:
        self.assertIn("merchant_frame_v1.css", V1_TEMPLATE)


class MerchantUiV2RouteTests(unittest.TestCase):
    def test_dashboard_v2_query_serves_v2_template(self) -> None:
        html = TestClient(app).get("/dashboard?cf_ui=v2").text
        self.assertIn('data-cf-ui="v2"', html)
        self.assertIn("merchant_ui_v2_frame.css", html)
        self.assertNotIn("merchant_frame_v1.css", html)

    def test_dashboard_default_serves_v2_production_baseline(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn('data-cf-ui="v2"', html)
        self.assertIn("merchant_ui_v2_frame.css", html)
        self.assertIn("merchant_ui_v2_home.css", html)
        self.assertNotIn("merchant_frame_v1.css", html)

    def test_dashboard_v1_query_rollback(self) -> None:
        html = TestClient(app).get("/dashboard?cf_ui=v1").text
        self.assertNotIn('data-cf-ui="v2"', html)
        self.assertIn("merchant_frame_v1.css", html)

    def test_visual_language_primitives_exist(self) -> None:
        lang_css = (ROOT / "static" / "merchant_ui_v2_language.css").read_text(
            encoding="utf-8"
        )
        lang_js = (ROOT / "static" / "merchant_ui_v2_language.js").read_text(
            encoding="utf-8"
        )
        home_js = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(
            encoding="utf-8"
        )
        ws_js = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(
            encoding="utf-8"
        )
        for token in (
            "cf2-co--",
            "cf2-evfield",
            "cf2-route",
            "cf2-dmass",
            "cf2-mtrace",
            "cf2-capsule",
            "cf2-terminus",
            "cf2-co-row--rail",
        ):
            self.assertIn(token, lang_css)
        self.assertIn("commerceObject", lang_js)
        self.assertIn("ev-converging", lang_js)
        self.assertIn("decision-ready", lang_js)
        self.assertIn("mapWorkspaceObjects", lang_js)
        self.assertIn("home-stage-closure-v1", home_js)
        self.assertIn("cf2-home__scene", home_js)
        self.assertIn("cf2-home__monitor", home_js)
        self.assertIn("الأهم الآن", home_js)
        self.assertIn("الأدلة ما زالت محدودة", home_js)
        self.assertIn("isDuplicateTruth", home_js)
        self.assertIn("ما يراقبه CartFlow أيضًا", home_js)
        self.assertIn("cf2-dobj", ws_js)
        self.assertIn("living-route", ws_js)
        self.assertIn("workspace-composition-closure-v1", ws_js)
        self.assertIn("mobile-hierarchy-v1", ws_js)
        self.assertIn("unwrapProjection", ws_js)
        self.assertIn("is-ready", ws_js)
        self.assertIn("is-armed", ws_js)
        self.assertIn("is-arriving", ws_js)
        app_js = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("paintGlobalNavigation", app_js)
        self.assertIn("NAV.global", app_js)
        self.assertIn("is-drawer-open", app_js)
        self.assertIn("cf2-account-btn", app_js)
        self.assertIn("cf2-ctx-handle", app_js)
        self.assertIn("الملخص", app_js)
        self.assertNotIn("cf2-global-btn", app_js)
        self.assertNotIn("openGlobalNav", app_js)
        self.assertNotIn("is-global-nav-open", app_js)
        frame_css = (ROOT / "static" / "merchant_ui_v2_frame.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("document (html/body) scrolls vertically", frame_css)
        self.assertIn("UtilityRow → GlobalUpbar", frame_css)
        self.assertIn("cf2-utility", frame_css)
        self.assertIn("cf2-global", frame_css)
        self.assertIn("cf2-ctx-handle", frame_css)
        self.assertIn("body[data-cf-ui=\"v2\"].is-drawer-open", frame_css)
        self.assertNotIn("cf2-global-btn", frame_css)
        self.assertNotIn("cf2-global-panel", frame_css)
        self.assertNotIn("is-global-nav-open", frame_css)
        # GlobalUpbar must remain visible on mobile
        self.assertNotRegex(
            frame_css,
            r"@media\s*\(max-width:\s*1023px\)[\s\S]*?\.cf2-nav\s*\{[^}]*display:\s*none",
        )
        self.assertIn("home-stage-closure-v1", home_js)
        self.assertIn("workspace-composition-closure-v1", ws_js)
        self.assertIn("cf2-ws--mobile-hierarchy-v1", ws_js)
        ws_css = (ROOT / "static" / "merchant_ui_v2_workspace.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("Mobile Hierarchy Refinement V1", ws_css)
        self.assertIn("Mobile CIM Footprint Closure V1", ws_css)
        self.assertIn("@media (max-width: 1023px)", ws_css)
        self.assertIn("min-height: 0", ws_css)

    def test_assets_exist(self) -> None:
        for rel in (
            "static/merchant_ui_v2_ds.css",
            "static/merchant_ui_v2_frame.css",
            "static/merchant_ui_v2_language.css",
            "static/merchant_ui_v2_home.css",
            "static/merchant_ui_v2_workspace.css",
            "static/merchant_ui_v2_carts.css",
            "static/merchant_ui_v2_comms.css",
            "static/merchant_ui_v2_app.js",
            "static/merchant_ui_v2_language.js",
            "static/merchant_ui_v2_home.js",
            "static/merchant_ui_v2_workspace.js",
            "static/merchant_ui_v2_carts.js",
            "static/merchant_ui_v2_comms.js",
            "templates/merchant_app_v2.html",
            "services/merchant_ui_v2/flag_v1.py",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_flag_constant(self) -> None:
        self.assertEqual(FLAG_MERCHANT_UI_V2, "CARTFLOW_MERCHANT_UI_V2")


if __name__ == "__main__":
    unittest.main()
