# -*- coding: utf-8 -*-
"""Dashboard Home UI V1 — presentation contract (structure only)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_JS = (_ROOT / "static" / "merchant_dashboard_home_v1.js").read_text(encoding="utf-8")
_CSS = (_ROOT / "static" / "merchant_dashboard_home_v1.css").read_text(encoding="utf-8")
_TMPL = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_LAZY = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")


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
            "أولوية اليوم",
            "الإيرادات المستعادة",
            "العملاء المشترون",
            "العملاء العائدون",
            "طبقة المعرفة",
            "ما يحتاج انتباهك",
            "ملخص الأداء",
            "آخر النشاطات",
            "سلال اليوم",
            "رسائل واتساب",
            "معدل التحويل",
        ):
            self.assertIn(marker, _JS)

    def test_no_fake_returned_kpi(self) -> None:
        self.assertIn("Customers returned: no governed today-KPI", _JS)
        self.assertIn("never invent", _JS.lower())

    def test_token_usage_in_css(self) -> None:
        for token in (
            "--pds-space-",
            "--v2-",
            "--cfpds-card-",
            "ma-dh-metric-grid",
            "ma-dh-card--elevated",
        ):
            self.assertIn(token, _CSS)

    def test_states_present(self) -> None:
        for name in ("renderLoading", "renderError", "ma-dh-empty", "ma-dh-skel"):
            self.assertTrue(name in _JS or name in _CSS)


if __name__ == "__main__":
    unittest.main()
