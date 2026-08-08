# -*- coding: utf-8 -*-
"""Merchant UI V2 clean-slate vertical slice contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.merchant_ui_v2.flag_v1 import (
    FLAG_MERCHANT_UI_V2,
    merchant_ui_v2_requested,
)

ROOT = Path(__file__).resolve().parents[1]
V2_TEMPLATE = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
V1_TEMPLATE = (ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


class MerchantUiV2FlagTests(unittest.TestCase):
    def test_default_off(self) -> None:
        self.assertFalse(merchant_ui_v2_requested(query={}, cookies={}))

    def test_query_v2(self) -> None:
        self.assertTrue(merchant_ui_v2_requested(query={"cf_ui": "v2"}, cookies={}))

    def test_query_v1_overrides_cookie(self) -> None:
        self.assertFalse(
            merchant_ui_v2_requested(query={"cf_ui": "v1"}, cookies={"cf_ui_v2": "1"})
        )


class MerchantUiV2TemplateTests(unittest.TestCase):
    def test_v2_namespace_and_no_legacy_css(self) -> None:
        self.assertIn('data-cf-ui="v2"', V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_ds.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_frame.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_home.css", V2_TEMPLATE)
        self.assertIn("merchant_ui_v2_workspace.css", V2_TEMPLATE)
        self.assertNotIn("merchant_frame_v1.css", V2_TEMPLATE)
        self.assertNotIn("merchant_pe_v2.css", V2_TEMPLATE)
        self.assertNotIn("decision_workspace_visual_assimilation", V2_TEMPLATE)
        self.assertNotIn("merchant_experience_home_v1.css", V2_TEMPLATE)

    def test_v2_frame_separates_appbar_and_ctx(self) -> None:
        self.assertIn("cf2-appbar", V2_TEMPLATE)
        self.assertIn("cf2-ctx", V2_TEMPLATE)
        self.assertIn("cf2-stage", V2_TEMPLATE)
        self.assertIn("cf2-drawer", V2_TEMPLATE)
        self.assertIn("cf2-nav", V2_TEMPLATE)

    def test_v2_slice_pages_only(self) -> None:
        self.assertIn('data-cf2-page="home"', V2_TEMPLATE)
        self.assertIn('data-cf2-page="workspace"', V2_TEMPLATE)
        self.assertIn("ماذا يجب أن أعرف الآن عن متجري؟", V2_TEMPLATE)
        self.assertIn("ما القرار الذي يجب أن أتخذه الآن، ولماذا؟", V2_TEMPLATE)

    def test_v1_unchanged_default_template(self) -> None:
        self.assertIn("merchant_frame_v1.css", V1_TEMPLATE)


class MerchantUiV2RouteTests(unittest.TestCase):
    def test_dashboard_v2_query_serves_v2_template(self) -> None:
        html = TestClient(app).get("/dashboard?cf_ui=v2").text
        self.assertIn('data-cf-ui="v2"', html)
        self.assertIn("merchant_ui_v2_frame.css", html)
        self.assertNotIn("merchant_frame_v1.css", html)

    def test_dashboard_default_serves_v1(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertNotIn('data-cf-ui="v2"', html)
        self.assertIn("merchant_frame_v1.css", html)

    def test_assets_exist(self) -> None:
        for rel in (
            "static/merchant_ui_v2_ds.css",
            "static/merchant_ui_v2_frame.css",
            "static/merchant_ui_v2_home.css",
            "static/merchant_ui_v2_workspace.css",
            "static/merchant_ui_v2_app.js",
            "static/merchant_ui_v2_home.js",
            "static/merchant_ui_v2_workspace.js",
            "templates/merchant_app_v2.html",
            "services/merchant_ui_v2/flag_v1.py",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_flag_constant(self) -> None:
        self.assertEqual(FLAG_MERCHANT_UI_V2, "CARTFLOW_MERCHANT_UI_V2")


if __name__ == "__main__":
    unittest.main()
