# -*- coding: utf-8 -*-
"""Settings Product Composition V1 — overview/detail host from existing truth."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

ROOT = Path(__file__).resolve().parents[1]
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
PARTIAL = (
    ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html"
).read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(
    encoding="utf-8"
)
SETTINGS_CSS = (ROOT / "static" / "merchant_ui_v2_settings.css").read_text(
    encoding="utf-8"
)
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")


class SettingsProductCompositionV1Tests(unittest.TestCase):
    def test_composition_marker_and_question(self) -> None:
        self.assertIn('data-cf-settings-composition="v1"', PARTIAL)
        self.assertIn("ما الذي أحتاج ضبطه لكي يعمل CartFlow بشكل صحيح وآمن؟", PARTIAL)
        self.assertIn("settings-product-composition-v1", SETTINGS_JS)
        self.assertIn("merchant_ui_v2_settings.js", V2_HTML)
        self.assertIn("CartFlowUiV2Settings.loadAndPaint", APP_JS)

    def test_overview_and_detail_hosts(self) -> None:
        self.assertIn("cf2-settings__overview", PARTIAL)
        self.assertIn("cf2-settings__detail", PARTIAL)
        self.assertIn("cf2-settings-back", PARTIAL)
        self.assertIn('data-cf2-settings-panel="store"', PARTIAL)
        self.assertIn('data-cf2-settings-panel="communication"', PARTIAL)
        self.assertIn('data-cf2-settings-panel="recovery"', PARTIAL)
        self.assertIn('data-cf2-settings-panel="policy"', PARTIAL)
        self.assertIn('data-cf2-settings-panel="experience"', PARTIAL)

    def test_existing_writers_remain(self) -> None:
        self.assertIn("ma-store-connection-root", PARTIAL)
        self.assertIn("ma-wa-settings-form", PARTIAL)
        self.assertIn("ma-recovery-policy-form", PARTIAL)
        self.assertIn("ma-vip-settings-form", PARTIAL)
        self.assertIn("ma-general-settings-form", PARTIAL)
        self.assertIn("ma-general-widget-name", PARTIAL)
        self.assertIn("cf2-settings-templates", PARTIAL)

    def test_salla_not_configurable(self) -> None:
        self.assertNotIn("ma-sc-connect-salla", PARTIAL)
        self.assertIn("سلة: غير متاحة حالياً", PARTIAL)
        self.assertIn("Shopify غير مُتاح", PARTIAL)
        self.assertNotIn("ma-sc-connect-shopify", PARTIAL)

    def test_no_invented_categories(self) -> None:
        banned = ("مركز الفوترة", "مفاتيح API", "الصلاحيات", "الفريق", "سوق التكاملات")
        blob = PARTIAL + SETTINGS_JS
        for needle in banned:
            self.assertNotIn(needle, blob)

    def test_mobile_is_not_side_by_side(self) -> None:
        self.assertIn("is-detail-open", SETTINGS_CSS)
        self.assertIn("@media (max-width: 1023px)", SETTINGS_CSS)
        self.assertIn(".cf2-settings.is-detail-open .cf2-settings__overview", SETTINGS_CSS)

    def test_hash_handoffs_open_areas(self) -> None:
        self.assertIn('whatsapp: "communication"', SETTINGS_JS)
        self.assertIn('widget: "experience"', SETTINGS_JS)
        self.assertIn('"trigger-templates": "communication"', SETTINGS_JS)

    def test_protected_surfaces_untouched_by_this_file(self) -> None:
        self.assertNotIn("settings-product-composition-v1", HOME_JS)
        self.assertNotIn("settings-product-composition-v1", CARTS_JS)
        self.assertNotIn("settings-product-composition-v1", COMMS_JS)
        self.assertNotIn("settings-product-composition-v1", WS_JS)

    def test_dashboard_v2_serves_composition(self) -> None:
        prev = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            html = TestClient(app).get("/dashboard?cf_ui=v2").text
            self.assertIn('data-cf-settings-composition="v1"', html)
            self.assertIn("merchant_ui_v2_settings.js", html)
            self.assertIn("cf2-settings__overview", html)
            self.assertIn("ma-recovery-policy-form", html)
            self.assertIn("ما الذي أحتاج ضبطه لكي يعمل CartFlow بشكل صحيح وآمن؟", html)
            self.assertIn("سلة: غير متاحة حالياً", html)
            self.assertNotIn("ma-sc-connect-salla", html)
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev


if __name__ == "__main__":
    unittest.main()
