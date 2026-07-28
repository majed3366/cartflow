# -*- coding: utf-8 -*-
"""Dashboard Constitution Implementation V1 — ownership / language guards."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DashboardConstitutionGuards(unittest.TestCase):
    def test_merchant_app_defaults_to_home(self) -> None:
        js = (ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")
        self.assertIn('h = "#home"', js)
        self.assertNotIn('h = window.CARTFLOW_CART_WORKSPACE_V1 ? "#workspace"', js)
        self.assertNotIn(
            'location.pathname + location.search + "#workspace"',
            js,
        )
        self.assertIn("Constitution: empty entry is Home", js)
        self.assertIn('if (h === "#home-month")', js)
        self.assertIn("ما حالة كل سلة؟", js)

    def test_home_cta_is_view_details_only(self) -> None:
        js = (ROOT / "static" / "home_executive_summary_v1.js").read_text(encoding="utf-8")
        self.assertIn(">عرض التفاصيل ←</a>", js)
        self.assertNotIn("وسّع في مساحة القرار", js)

    def test_carts_banner_has_no_systemic_decision_text(self) -> None:
        js = (ROOT / "static" / "commerce_situations_surfaces_v1.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("عرض القرارات في مساحة القرار", js)
        self.assertNotIn("قرار العمل:", js)
        self.assertNotIn("systemic.summary_ar", js)

    def test_settings_hides_automation_placeholder(self) -> None:
        html = (ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
        self.assertIn('id="ma-automation-mode-card" hidden', html)
        self.assertNotIn("للتذكير فقط — لا يغيّر آلية الاسترجاع حالياً", html)
        self.assertIn('id="ma-gtb-notify"', html)
        self.assertRegex(html, r'id="ma-gtb-notify"[^>]*\bhidden\b')
        self.assertIn('data-nav="communication"', html)
        self.assertNotIn("تشخيص واختبار", html)

    def test_communication_action_for_missing_phone(self) -> None:
        js = (
            ROOT / "static" / "merchant_experience_integration_v1.js"
        ).read_text(encoding="utf-8")
        self.assertIn("#carts?tab=nophone", js)
        self.assertIn("تم الإرسال", js)
        self.assertIn("لا يوجد رقم", js)
        cs = (ROOT / "static" / "commerce_situations_surfaces_v1.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('data-constitution="communication"', cs)
        self.assertIn("تم الإرسال", cs)
        self.assertIn("يحتاج متابعة", cs)

    def test_workspace_exposes_constitution_question(self) -> None:
        html = (ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
        self.assertIn('id="cw-constitution-question"', html)
        self.assertIn("ما القرار الذي يجب أن أتخذه الآن، ولماذا؟", html)


if __name__ == "__main__":
    unittest.main()
