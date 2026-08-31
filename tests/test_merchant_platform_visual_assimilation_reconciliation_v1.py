# -*- coding: utf-8 -*-
"""Merchant Platform Visual Assimilation Production Reconciliation V1 — M1/M2/M3 only."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

ROOT = Path(__file__).resolve().parents[1]
CARTS_CSS = (ROOT / "static" / "merchant_ui_v2_carts.css").read_text(encoding="utf-8")
COMMS_CSS = (ROOT / "static" / "merchant_ui_v2_comms.css").read_text(encoding="utf-8")
SETTINGS_CSS = (ROOT / "static" / "merchant_ui_v2_settings.css").read_text(
    encoding="utf-8"
)
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(
    encoding="utf-8"
)
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
SUB_JS = (ROOT / "static" / "merchant_subscription.js").read_text(encoding="utf-8")
HOME_CSS = (ROOT / "static" / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
WS_CSS = (ROOT / "static" / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")
SHELL_CSS = (ROOT / "static" / "merchant_ui_v2_frame.css").read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")


class MerchantPlatformVisualAssimilationReconciliationV1Tests(unittest.TestCase):
    def test_m1_carts_empty_is_not_dashed_shell(self) -> None:
        self.assertIn(".cf2-carts__empty", CARTS_CSS)
        self.assertNotIn("dashed", CARTS_CSS)
        self.assertIn("border: 1px solid var(--cf2-border)", CARTS_CSS)
        self.assertIn("border-inline-start: 3px solid rgba(8, 32, 72, 0.22)", CARTS_CSS)
        self.assertIn("تعذّر تأكيد الطابور", CARTS_JS)
        self.assertIn("الحقيقة غير مكتملة — لا سلال مخترعة ولا هدوء افتراضي.", CARTS_JS)

    def test_m1_comms_empty_is_not_dashed_shell(self) -> None:
        self.assertIn(".cf2-comms__empty", COMMS_CSS)
        self.assertNotIn("dashed", COMMS_CSS)
        self.assertIn("border: 1px solid var(--cf2-border)", COMMS_CSS)
        self.assertIn("border-inline-start: 3px solid rgba(8, 32, 72, 0.22)", COMMS_CSS)
        self.assertIn("cf2-comms__empty", COMMS_JS)
        self.assertIn("function emptyCopy", COMMS_JS)

    def test_m2_settings_overview_reduced_open_start(self) -> None:
        self.assertIn("border-inline-start: 3px solid transparent", SETTINGS_CSS)
        self.assertIn("border-inline-start-color: rgba(122, 78, 12, 0.42)", SETTINGS_CSS)
        self.assertIn("border-inline-start-color: var(--cf2-navy)", SETTINGS_CSS)
        self.assertIn(".cf2-settings__row.is-selected.is-needs", SETTINGS_CSS)
        self.assertNotIn("inset 3px 0 0 var(--cf2-teal)", SETTINGS_CSS)
        self.assertNotIn("rgba(24, 176, 168, 0.45)", SETTINGS_CSS)
        self.assertIn(".cf2-settings__row:focus-visible", SETTINGS_CSS)
        for key in ("READY", "NEEDS_SETUP", "PARTIAL", "READ_ONLY", "UNAVAILABLE"):
            self.assertIn(key, SETTINGS_JS)
            self.assertIn('[data-state="' + key + '"]', SETTINGS_CSS)

    def test_m3_settings_detail_has_one_object_edge(self) -> None:
        detail = SETTINGS_CSS.split('[data-cf-ui="v2"] .cf2-settings__detail {', 1)[1]
        detail = detail.split("}", 1)[0]
        self.assertIn("border-inline-start: 3px solid rgba(8, 32, 72, 0.2)", detail)
        card = SETTINGS_CSS.split('[data-cf-ui="v2"] .cf2-settings .setting-card', 1)[1]
        card = card.split("}", 1)[0]
        self.assertNotIn("border-inline-start", card)
        self.assertIn("border: 1px solid var(--cf2-border)", card)

    def test_home_workspace_shell_css_untouched_by_this_pass(self) -> None:
        self.assertIn("border-inline-start: 5px solid", HOME_CSS)
        self.assertIn("border-inline-start: 4px solid", WS_CSS)
        self.assertIn(".cf2-root", SHELL_CSS)

    def test_queuepool_and_lazy_init_preserved(self) -> None:
        self.assertIn("settings-queuepool-pressure-remediation-v1", SETTINGS_JS)
        self.assertNotIn("Promise.all", SETTINGS_JS)
        self.assertIn("SURFACE_PRODUCT_INIT", APP_JS)
        self.assertIn("function settingsSurfaceActive()", SUB_JS)
        self.assertIn("qpool1", V2_HTML)
        self.assertIn("nvis1", V2_HTML)
        self.assertIn("fanout1", V2_HTML)
        self.assertIn("assim1", V2_HTML)
        self.assertIn("resid1", V2_HTML)

    def test_dashboard_hosts_assimilation_cache_bust(self) -> None:
        prev = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            html = TestClient(app).get("/dashboard?cf_ui=v2").text
            self.assertIn("cartsempty1-assim1", html)
            self.assertIn("commshier1-assim1", html)
            self.assertIn("nvis1-assim1-resid1", html)
            self.assertIn("qpool1", html)
            self.assertIn("nvis1-fanout1", html)
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev
