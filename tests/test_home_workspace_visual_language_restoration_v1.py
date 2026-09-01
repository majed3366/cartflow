# -*- coding: utf-8 -*-
"""Home & Decision Workspace Visual Language Restoration V1 — current-line port."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

ROOT = Path(__file__).resolve().parents[1]
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
HOME_CSS = (ROOT / "static" / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
WS_JS = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
WS_CSS = (ROOT / "static" / "merchant_ui_v2_workspace.css").read_text(encoding="utf-8")
LANG_JS = (ROOT / "static" / "merchant_ui_v2_language.js").read_text(encoding="utf-8")
FRAME_CSS = (ROOT / "static" / "merchant_ui_v2_frame.css").read_text(encoding="utf-8")
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")


class HomeWorkspaceVisualLanguageRestorationV1Tests(unittest.TestCase):
    def test_home_restores_lkg_emitters_on_current_board(self) -> None:
        self.assertIn("home-stage-closure-v1", HOME_JS)
        self.assertIn("projectHomeSurface", HOME_JS)
        self.assertIn("CartFlowSemanticVisualV1", HOME_JS)
        self.assertIn("مركز الجاذبية", HOME_JS)
        self.assertIn("مشهد تنفيذي", HOME_JS)
        self.assertIn("gravity-well", HOME_JS)
        self.assertIn("NOT_CURRENTLY_SUPPORTED", HOME_JS)
        self.assertIn("isDuplicateTruth", HOME_JS)
        self.assertIn("الأهم الآن", HOME_JS)
        self.assertIn("/api/dashboard/summary", HOME_JS)
        self.assertIn("home_executive_summary_v1", HOME_JS)
        self.assertNotIn("L().commerceClause", HOME_JS)
        self.assertNotIn("commerceClause(sem", HOME_JS)

    def test_home_incomplete_and_empty_keep_identity(self) -> None:
        self.assertIn('data-cf2-truth="empty"', HOME_JS)
        self.assertIn('data-cf2-silence="quiet"', HOME_JS)
        self.assertIn("جاري تحميل معرفة متجرك", HOME_JS)
        self.assertIn("تعذّر تحميل معرفة المتجر", HOME_JS)
        self.assertNotIn("isWeakText", HOME_JS)

    def test_workspace_restores_co_row_on_current_decision_object(self) -> None:
        self.assertIn("workspace-composition-closure-v1", WS_JS)
        self.assertIn("unwrapProjection", WS_JS)
        self.assertIn("projectWorkspace", WS_JS)
        self.assertIn("formation", WS_JS)
        self.assertIn("living-route", WS_JS)
        self.assertIn("cf2-dmass", WS_JS)
        self.assertIn("/api/cart-workspace/v1/projection", WS_JS)
        self.assertIn("projectWorkspace", WS_JS)
        self.assertIn("decision_readiness", WS_JS)
        self.assertIn("core-silence", WS_JS)
        self.assertNotIn("L().commerceClause", WS_JS)
        self.assertNotIn("commerceClause(sem", WS_JS)

    def test_current_shell_and_startup_preserved(self) -> None:
        self.assertIn("UtilityRow", V2_HTML)
        self.assertIn("cf2-utility", V2_HTML)
        self.assertIn("cf2-global", FRAME_CSS)
        self.assertIn("cf2-ctx-handle", FRAME_CSS)
        self.assertIn("SURFACE_PRODUCT_INIT", APP_JS)
        self.assertIn("function initSurfaceProductData(section, opts)", APP_JS)
        self.assertNotIn("openGlobalNav", APP_JS)

    def test_cache_bust_and_queuepool_markers(self) -> None:
        self.assertIn("semvis1", V2_HTML)
        self.assertIn("langrest1", V2_HTML)
        self.assertIn("psg1", V2_HTML)
        self.assertIn("qpool1", V2_HTML)
        self.assertIn("nvis1-fanout1", V2_HTML)
        self.assertIn("resid1", V2_HTML)

    def test_home_css_keeps_stage_board_and_shows_rail(self) -> None:
        self.assertIn("border-inline-start: 5px solid", HOME_CSS)
        self.assertIn("data-cf2-gravity", HOME_CSS)
        self.assertIn(".cf2-home__kicker", HOME_CSS)
        self.assertIn("gravity-well", HOME_CSS)

    def test_workspace_css_co_row_is_operational_not_poster(self) -> None:
        self.assertIn("border-inline-start: 4px solid", WS_CSS)
        self.assertIn("data-cf2-organism=\"formation\"", WS_CSS)
        self.assertIn("cf2-ws__void", WS_CSS)

    def test_language_helpers_unchanged(self) -> None:
        self.assertIn("function commerceObject", LANG_JS)
        self.assertIn("function momentumTrace", LANG_JS)
        self.assertIn("function mapHomeObjects", LANG_JS)
        self.assertIn("function mapWorkspaceObjects", LANG_JS)

    def test_dashboard_hosts_restoration_cache_bust(self) -> None:
        prev = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            html = TestClient(app).get("/dashboard?cf_ui=v2").text
            self.assertIn("semvis1", html)
            self.assertIn("langrest1", html)
            self.assertIn("merchant_ui_v2_home.js", html)
            self.assertIn("merchant_ui_v2_workspace.js", html)
            self.assertIn("cf2-utility", html)
            self.assertIn("cf2-ctx-handle", html)
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev
