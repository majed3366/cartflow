# -*- coding: utf-8 -*-
"""Merchant Platform Visual Identity Residual Closure V1 — R1/R2/R3 only."""
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
HOME_CSS = (ROOT / "static" / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
WS_CSS = (ROOT / "static" / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")
SHELL_CSS = (ROOT / "static" / "merchant_ui_v2_frame.css").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(
    encoding="utf-8"
)
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")


def _block(css: str, needle: str) -> str:
    return css.split(needle, 1)[1].split("}", 1)[0]


class MerchantPlatformVisualIdentityResidualClosureV1Tests(unittest.TestCase):
    def test_r1_carts_selected_is_open_start_not_teal_outline(self) -> None:
        selected = _block(CARTS_CSS, ".cf2-carts__row.is-selected {")
        self.assertIn("border-inline-start-color: var(--cf2-navy)", selected)
        self.assertIn("box-shadow: none", selected)
        self.assertNotIn("var(--cf2-teal)", selected)
        self.assertNotIn("inset 3px 0 0 var(--cf2-teal)", CARTS_CSS)
        row = _block(CARTS_CSS, "body[data-cf-ui=\"v2\"] .cf2-carts__row {")
        self.assertIn("border-inline-start: 3px solid transparent", row)

    def test_r2_comms_list_detail_are_not_twin_white_panes(self) -> None:
        after_list = COMMS_CSS.split(
            "body[data-cf-ui=\"v2\"] .cf2-comms__list {", 1
        )[1]
        detail = _block(after_list, "body[data-cf-ui=\"v2\"] .cf2-comms__detail {")
        self.assertIn("background: transparent", detail)
        self.assertIn("border-inline-start: 3px solid rgba(8, 32, 72, 0.2)", detail)
        self.assertNotIn("var(--cf2-surface)", detail)
        self.assertNotIn("border-radius: var(--cf2-r-md)", detail)
        selected = _block(COMMS_CSS, ".cf2-comms__row.is-selected {")
        self.assertIn("border-inline-start-color: var(--cf2-navy)", selected)
        self.assertIn("box-shadow: none", selected)
        self.assertNotIn("inset 3px 0 0 var(--cf2-teal)", COMMS_CSS)
        mobile = COMMS_CSS.split("@media (max-width: 1023px)", 1)[1]
        self.assertIn("border-inline-start: 0", mobile)

    def test_r3_settings_overview_rows_are_not_filled_cards(self) -> None:
        row = _block(SETTINGS_CSS, "[data-cf-ui=\"v2\"] .cf2-settings__row {")
        self.assertIn("background: transparent", row)
        self.assertIn("border-inline-start: 3px solid transparent", row)
        self.assertIn("border-radius: 0", row)
        self.assertNotIn("var(--cf2-surface)", row)
        self.assertIn("border-inline-start-color: rgba(122, 78, 12, 0.42)", SETTINGS_CSS)
        self.assertIn("border-inline-start-color: var(--cf2-navy)", SETTINGS_CSS)
        self.assertNotIn("inset 3px 0 0 var(--cf2-teal)", SETTINGS_CSS)
        self.assertNotIn("rgba(24, 176, 168, 0.45)", SETTINGS_CSS)

    def test_m3_settings_detail_object_edge_unchanged(self) -> None:
        detail = _block(SETTINGS_CSS, '[data-cf-ui="v2"] .cf2-settings__detail {')
        self.assertIn("border-inline-start: 3px solid rgba(8, 32, 72, 0.2)", detail)
        card = SETTINGS_CSS.split('[data-cf-ui="v2"] .cf2-settings .setting-card', 1)[1]
        card = card.split("}", 1)[0]
        self.assertNotIn("border-inline-start", card)
        self.assertIn("border: 1px solid var(--cf2-border)", card)

    def test_home_workspace_shell_untouched(self) -> None:
        self.assertIn("border-inline-start: 5px solid", HOME_CSS)
        self.assertIn("border-inline-start: 4px solid", WS_CSS)
        self.assertIn(".cf2-root", SHELL_CSS)

    def test_queuepool_and_settings_load_preserved(self) -> None:
        self.assertIn("settings-queuepool-pressure-remediation-v1", SETTINGS_JS)
        self.assertNotIn("Promise.all", SETTINGS_JS)
        self.assertIn("qpool1", V2_HTML)
        self.assertIn("nvis1-fanout1", V2_HTML)
        self.assertIn("resid1", V2_HTML)

    def test_dashboard_hosts_residual_cache_bust(self) -> None:
        prev = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            html = TestClient(app).get("/dashboard?cf_ui=v2").text
            self.assertIn("resid1", html)
            self.assertIn("qpool1", html)
            self.assertIn("nvis1-fanout1", html)
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev
