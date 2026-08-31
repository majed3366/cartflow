# -*- coding: utf-8 -*-
"""Visual-structure contracts for canonical Merchant UI V2. Not pixel tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.merchant_ui_v2.flag_v1 import merchant_ui_v2_requested
from services.merchant_visual_identity_v1 import (
    CANONICAL_CARTS_EMITTERS,
    CANONICAL_COMMS_EMITTERS,
    CANONICAL_HOME_EMITTERS,
    CANONICAL_SETTINGS_EMITTERS,
    CANONICAL_SHELL_MARKERS,
    CANONICAL_WORKSPACE_EMITTERS,
    FORBIDDEN_CANONICAL_MARKERS,
    VISUAL_SYSTEM_VERSION,
    forbidden_present,
    missing_markers,
)

ROOT = Path(__file__).resolve().parents[1]
V2 = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
CARTS_CSS = (ROOT / "static" / "merchant_ui_v2_carts.css").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(encoding="utf-8")
SETTINGS_HTML = (
    ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html"
).read_text(encoding="utf-8")
LANG_CSS = (ROOT / "static" / "merchant_ui_v2_language.css").read_text(encoding="utf-8")
LANG_JS = (ROOT / "static" / "merchant_ui_v2_language.js").read_text(encoding="utf-8")


class VisualIdentitySourceContracts(unittest.TestCase):
    def test_shell_and_language_layer(self) -> None:
        self.assertEqual(missing_markers(V2, CANONICAL_SHELL_MARKERS), [])
        self.assertIn("merchant_ui_v2_language.css", V2)
        self.assertEqual(forbidden_present(V2, FORBIDDEN_CANONICAL_MARKERS), [])

    def test_home_emitters(self) -> None:
        blob = HOME_JS + LANG_JS
        self.assertEqual(missing_markers(blob, CANONICAL_HOME_EMITTERS), [])
        self.assertIn("evidenceFieldFromSufficiency", HOME_JS)
        self.assertIn("projectHomeSurface", HOME_JS)

    def test_workspace_emitters(self) -> None:
        self.assertEqual(missing_markers(WS_JS, CANONICAL_WORKSPACE_EMITTERS), [])

    def test_carts_emitters_no_dashed_empty(self) -> None:
        self.assertEqual(missing_markers(CARTS_JS, CANONICAL_CARTS_EMITTERS), [])
        self.assertNotIn("dashed", CARTS_CSS)

    def test_comms_not_inbox(self) -> None:
        self.assertEqual(missing_markers(COMMS_JS, CANONICAL_COMMS_EMITTERS), [])

    def test_settings_overview_detail(self) -> None:
        blob = SETTINGS_JS + SETTINGS_HTML
        self.assertEqual(missing_markers(blob, CANONICAL_SETTINGS_EMITTERS), [])

    def test_language_primitives_css(self) -> None:
        for token in ("cf2-co-row", "cf2-evfield", "cf2-mtrace", "cf2-route", "cf2-dmass"):
            self.assertIn(token, LANG_CSS)


class VisualIdentityRuntimeContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_dashboard_default_is_canonical_v2(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-UI-Version"), "v2")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Renderer"), "merchant_ui_v2")
        self.assertEqual(
            r.headers.get("X-CartFlow-Merchant-Visual-System"), VISUAL_SYSTEM_VERSION
        )
        self.assertIn('data-cf-ui="v2"', r.text)
        self.assertIn("CARTFLOW_MERCHANT_RUNTIME", r.text)
        self.assertIn(VISUAL_SYSTEM_VERSION, r.text)
        self.assertEqual(forbidden_present(r.text), [])

    def test_leftover_v1_cookie_does_not_select_legacy(self) -> None:
        self.assertTrue(merchant_ui_v2_requested(query={}, cookies={"cf_ui_v2": "0"}))
        r = self.client.get("/dashboard", cookies={"cf_ui_v2": "0"})
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-UI-Version"), "v2")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Renderer"), "merchant_ui_v2")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Role"), "canonical")
        self.assertNotIn("home_executive_summary_v1.js", r.text)
        self.assertIn("merchant_ui_v2_home.js", r.text)
        set_cookie = ";".join(r.headers.get_list("set-cookie"))
        self.assertIn("cf_ui_v2=1", set_cookie)

    def test_explicit_v1_query_still_rollback(self) -> None:
        r = self.client.get("/dashboard?cf_ui=v1")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-UI-Version"), "v1")
        self.assertEqual(r.headers.get("X-CartFlow-Merchant-Role"), "rollback_only")
        self.assertIn("home_executive_summary_v1.js", r.text)


if __name__ == "__main__":
    unittest.main()
