# -*- coding: utf-8 -*-
"""Dashboard Home Executive Control Center (V3) — presentation contract."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_JS = (_ROOT / "static" / "merchant_dashboard_home_v1.js").read_text(encoding="utf-8")
_CSS = (_ROOT / "static" / "merchant_dashboard_home_v1.css").read_text(encoding="utf-8")
_TMPL = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_LAZY = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_APP = (_ROOT / "static" / "merchant_app.js").read_text(encoding="utf-8")


class DashboardHomeUiV1Tests(unittest.TestCase):
    def test_assets_wired_in_template(self) -> None:
        self.assertIn("merchant_dashboard_home_v1.js", _TMPL)
        self.assertIn("merchant_dashboard_home_v1.css", _TMPL)

    def test_apply_export_and_lazy_priority(self) -> None:
        self.assertIn("maApplyDashboardHomeV1", _JS)
        self.assertIn("maApplyDashboardHomeV1", _LAZY)
        self.assertRegex(
            _LAZY,
            re.compile(
                r"if\s*\(\s*!homeV1Rendered\s*&&\s*!pulseRendered\s*&&\s*window\.maApplyHomeExperience\s*\)"
            ),
        )

    def test_section_order_markers(self) -> None:
        for marker in (
            "اليوم في متجرك",
            "ملخص تنفيذي",
            "أعلى أولوية اليوم",
            "أحدث فهم مهم",
            "الإيرادات المستعادة",
            "العملاء المشترون",
            "العملاء العائدون",
            "طبقة المعرفة",
            "مركز الانتباه",
            "ملخص الأداء",
            "آخر النشاطات",
            "اتجاه الاسترجاع",
            "اتجاه التحويل",
            "نشاط واتساب",
            "الصحة التشغيلية",
            "الملاحظة",
            "الدليل",
            "التفسير",
            "التوصية",
            "الثقة",
        ):
            self.assertIn(marker, _JS)

    def test_executive_control_center_surface(self) -> None:
        self.assertIn("ma-ecc", _JS)
        self.assertIn("ma-dash-home-v3", _JS)
        self.assertIn("ma-ecc-hero", _CSS)
        self.assertIn("ma-ecc-kl", _CSS)
        self.assertIn("ma-ecc-attention", _CSS)
        self.assertIn("ma-ecc-metrics", _CSS)

    def test_no_fake_returned_kpi(self) -> None:
        self.assertIn("Customers returned: no governed today-KPI", _JS)
        self.assertIn("never invent", _JS.lower())

    def test_token_usage_in_css(self) -> None:
        for token in (
            "--pds-space-",
            "--v2-",
            "--cfpds-card-",
            "ma-ecc-metrics",
            "ma-ecc-band--knowledge",
        ):
            self.assertIn(token, _CSS)

    def test_states_present(self) -> None:
        for name in ("renderLoading", "renderError", "ma-ecc-calm", "ma-ecc-skel"):
            self.assertTrue(name in _JS or name in _CSS)

    def test_diagnostics_moved_to_settings(self) -> None:
        self.assertNotIn('data-home-nav="test-tools"', _TMPL)
        self.assertIn("settings-diagnostics", _TMPL)
        self.assertIn("page-settings-diagnostics", _TMPL)
        self.assertIn("تشخيص واختبار", _TMPL)
        self.assertIn("settings-diagnostics", _APP)
        self.assertIn("#home-test-tools", _APP)
        self.assertIn('"settings-diagnostics"', _APP)
        self.assertNotIn("page-home-test-tools", _TMPL)
        self.assertNotIn("page-home-test-tools", _LAZY)


if __name__ == "__main__":
    unittest.main()
