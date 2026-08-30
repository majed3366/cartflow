# -*- coding: utf-8 -*-
"""Settings Narrow Visual Refinement V1 — presentation only; QueuePool path unchanged."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(
    encoding="utf-8"
)
SETTINGS_CSS = (ROOT / "static" / "merchant_ui_v2_settings.css").read_text(
    encoding="utf-8"
)
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
WA_JS = (ROOT / "static" / "merchant_whatsapp_settings.js").read_text(
    encoding="utf-8"
)
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
PARTIAL = (
    ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html"
).read_text(encoding="utf-8")


class SettingsNarrowVisualRefinementV1Tests(unittest.TestCase):
    def test_overview_can_express_all_five_state_classes(self) -> None:
        for key in ("READY", "NEEDS_SETUP", "PARTIAL", "READ_ONLY", "UNAVAILABLE"):
            self.assertIn(key, SETTINGS_JS)
        self.assertIn("قراءة فقط", SETTINGS_JS)
        self.assertIn("غير متاح", SETTINGS_JS)
        self.assertIn('state: "READ_ONLY"', SETTINGS_JS)
        self.assertIn('state: "UNAVAILABLE"', SETTINGS_JS)
        self.assertIn("cf2-settings__states", SETTINGS_JS)
        self.assertIn('[data-state="READ_ONLY"]', SETTINGS_CSS)
        self.assertIn('[data-state="UNAVAILABLE"]', SETTINGS_CSS)
        self.assertIn('[data-state="PARTIAL"]', SETTINGS_CSS)

    def test_store_hidden_actions_cannot_show_as_flex(self) -> None:
        self.assertIn(".ma-sc-actions[hidden]", SETTINGS_CSS)
        self.assertIn("display: none !important", SETTINGS_CSS)
        self.assertIn('id="ma-sc-actions-not-connected"', PARTIAL)
        self.assertIn('id="ma-sc-actions-connected"', PARTIAL)
        self.assertIn("hidden", PARTIAL.split('id="ma-sc-actions-connected"', 1)[1][:40])

    def test_communication_path_has_one_dominant_cta(self) -> None:
        self.assertIn("ma-wa-mode-select-btn is-secondary", WA_JS)
        self.assertIn("ma-fw-save ma-wa-mode-select-btn is-current", WA_JS)
        self.assertNotIn(
            'class="ma-fw-save ma-wa-mode-select-btn" +\n          (isSelected ? " is-current" : "")',
            WA_JS,
        )
        self.assertIn(".ma-wa-mode-select-btn.is-secondary", SETTINGS_CSS)
        self.assertIn("فتح القوالب", PARTIAL)

    def test_mobile_detail_hides_full_canonical_question(self) -> None:
        self.assertIn(
            "ما الذي أحتاج ضبطه لكي يعمل CartFlow بشكل صحيح وآمن؟",
            PARTIAL,
        )
        self.assertIn(
            ".cf2-settings.is-detail-open .cf-settings-canonical__q",
            SETTINGS_CSS,
        )
        self.assertIn("رجوع · ", SETTINGS_JS)
        self.assertIn("cf2-settings-back", PARTIAL)

    def test_dual_teal_selection_focus_collision_removed(self) -> None:
        self.assertNotIn("rgba(24, 176, 168, 0.45)", SETTINGS_CSS)
        self.assertIn(".cf2-settings__row.is-needs", SETTINGS_CSS)
        self.assertIn(".cf2-settings__row:focus-visible", SETTINGS_CSS)
        self.assertIn("document.activeElement.blur()", SETTINGS_JS)
        self.assertIn("inset 3px 0 0 var(--cf2-teal)", SETTINGS_CSS)

    def test_settings_nav_scrolls_active_item_into_view(self) -> None:
        self.assertIn("revealActiveNavItem", APP_JS)
        self.assertIn("scrollIntoView", APP_JS)
        self.assertIn("nav.scrollBy", APP_JS)
        self.assertIn('getElementById("cf2-nav")', APP_JS)

    def test_empty_detail_is_not_a_dashed_shell(self) -> None:
        self.assertIn(".cf2-settings__detail-empty", SETTINGS_CSS)
        self.assertNotIn("1px dashed", SETTINGS_CSS)
        self.assertIn("اختر منطقة لعرض حالتها وضبطها.", PARTIAL)

    def test_queuepool_load_path_untouched(self) -> None:
        self.assertIn("settings-queuepool-pressure-remediation-v1", SETTINGS_JS)
        self.assertIn('jsonGet("/api/merchant/store-connection")', SETTINGS_JS)
        self.assertIn('jsonGet("/api/recovery-settings")', SETTINGS_JS)
        self.assertNotIn("Promise.all", SETTINGS_JS)
        self.assertNotIn("initExisting", SETTINGS_JS)
        self.assertIn("qpool1", V2_HTML)
        self.assertIn("nvis1", V2_HTML)

    def test_dashboard_hosts_refinement_cache_bust(self) -> None:
        prev = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            html = TestClient(app).get("/dashboard?cf_ui=v2").text
            self.assertIn("merchant_ui_v2_settings.css", html)
            self.assertIn("nvis1", html)
            self.assertIn("qpool1", html)
            self.assertIn("merchant_ui_v2_app.js", html)
            self.assertIn('data-cf-settings-composition="v1"', html)
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev


if __name__ == "__main__":
    unittest.main()
