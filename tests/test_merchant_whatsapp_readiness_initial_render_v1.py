# -*- coding: utf-8 -*-
"""WhatsApp readiness initial render — no fallback CTA flicker."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


class WhatsappReadinessInitialRenderV1Tests(unittest.TestCase):
    def test_dashboard_whatsapp_shows_loading_state_initially(self) -> None:
        html = Path("templates/merchant_app.html").read_text(encoding="utf-8")
        self.assertIn("جاري تحميل إعدادات واتساب", html)
        self.assertIn("ma-wa-v2-loading", html)
        self.assertIn('id="ma-wa-mode-selection-root"', html)
        self.assertIn('id="ma-wa-current-path-root"', html)

    def test_legacy_enable_cta_hidden_in_html(self) -> None:
        html = Path("templates/merchant_app.html").read_text(encoding="utf-8")
        snippet = html[html.index('id="ma-wa-enable-recovery-btn"') : html.index('id="ma-wa-enable-recovery-btn"') + 120]
        self.assertIn("hidden", snippet)

    def test_js_suppresses_legacy_cta_until_readiness_resolves(self) -> None:
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("showReadinessLoading", js)
        self.assertIn("showReadinessError", js)
        self.assertIn("setLegacyEnableCtaVisible(false)", js)
        self.assertIn("جاري التحقق من جاهزية واتساب", js)
        self.assertIn("تعذر التحقق من جاهزية واتساب حالياً", js)
        self.assertIn("data-cf-wa-primary-cta", js)

    def test_js_renders_v2_sections_only_after_load(self) -> None:
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        load_idx = js.index("function loadSettings")
        loading_idx = js.index("showPageLoading();", load_idx)
        fill_idx = js.index("fillForm(x.data)", load_idx)
        self.assertLess(loading_idx, fill_idx)
        self.assertIn("function renderCurrentPath", js)
        self.assertIn("function renderAdvancedSettings", js)

    def test_api_failure_shows_calm_fallback(self) -> None:
        js = Path("static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertIn("READINESS_ERROR_AR", js)
        self.assertIn("ma-wa-v2-error", js)

    def test_dashboard_page_includes_loading_not_visible_legacy_cta(self) -> None:
        r = TestClient(app).get("/dashboard")
        self.assertEqual(r.status_code, 200, r.text[:500])
        t = r.text or ""
        self.assertIn("جاري تحميل إعدادات واتساب", t)
        self.assertIn('id="ma-wa-enable-recovery-btn" hidden', t)


if __name__ == "__main__":
    unittest.main()
