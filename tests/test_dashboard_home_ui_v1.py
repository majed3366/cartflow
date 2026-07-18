# -*- coding: utf-8 -*-
"""Dashboard Home — Daily Business Brief V1 presentation + readiness contract."""
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


class DashboardHomeDailyBriefV1Tests(unittest.TestCase):
    def test_assets_wired_in_template(self) -> None:
        self.assertIn("merchant_dashboard_home_v1.js", _TMPL)
        self.assertIn("merchant_dashboard_home_v1.css", _TMPL)

    def test_apply_export_and_lazy_priority(self) -> None:
        self.assertIn("maApplyDashboardHomeV1", _JS)
        self.assertIn("maApplyDashboardHomeV1", _LAZY)

    def test_canonical_brief_section_order(self) -> None:
        # Adaptive Cognition V2: order is data-driven via section_order / renderSectionByKey.
        self.assertIn("DEFAULT_SECTION_ORDER", _JS)
        self.assertIn("resolveSectionOrder", _JS)
        self.assertIn("renderSectionByKey", _JS)
        self.assertIn("adaptive_cognition_v1", _JS)
        self.assertIn("ma-ecc--acf-v2", _JS)
        self.assertIn("ma-ecc--reality-v1", _JS)
        self.assertIn("ma-ecc-focus", _JS)
        self.assertIn("PATH_FOCUS_AR", _JS)
        self.assertIn("maAcfSummaryQuery", _JS)
        self.assertIn("maAcfSummaryQuery", _LAZY)
        self.assertIn("acf_trigger", _LAZY)
        # Layout integrity: attention cards must not force a 40px-only first column.
        self.assertIn("ma-ecc-attention__item", _CSS)
        self.assertIn("display: flex", _CSS)
        self.assertIn(
            "A single-child 40px|1fr grid collapses body text",
            _CSS,
        )
        for section in (
            "health",
            "risk",
            "opportunity",
            "priority",
            "understanding",
            "learning",
            "timeline",
        ):
            self.assertIn(f'data-ecc-section="{section}"', _JS)
        self.assertIn("daily-brief-v1", _JS)
        # Retired redistribution KPI band — health owns direction.
        self.assertNotIn('data-ecc-section="metrics"', _JS)
        self.assertNotIn("renderMetrics", _JS)

    def test_understanding_business_meaning_structure(self) -> None:
        for step in (
            "الملاحظة",
            "الدليل",
            "المعنى التجاري",
            "الأثر التجاري",
            "الاتجاه الموصى به",
            "الثقة",
        ):
            self.assertIn(step, _JS)
        self.assertIn("ma-ecc-band--knowledge", _CSS)

    def test_timeline_contextual_why(self) -> None:
        self.assertIn("لماذا يهم:", _JS)
        self.assertIn("why_it_matters_ar", _JS)
        self.assertIn("renderBusinessTimeline", _JS)

    def test_priority_is_single_recommendation_surface(self) -> None:
        self.assertIn("renderTodaysPriority", _JS)
        self.assertIn("أولوية اليوم", _JS)
        # No multi-item queue list markup for priority.
        pri = _JS[
            _JS.find("function renderTodaysPriority") : _JS.find(
                "function renderBusinessUnderstanding"
            )
        ]
        self.assertNotIn("<ol class=\"ma-ecc-attention\">", pri)

    def test_diagnostics_absent_from_home(self) -> None:
        self.assertNotIn('data-home-nav="test-tools"', _TMPL)
        self.assertNotIn("page-home-test-tools", _TMPL)
        self.assertNotIn("page-home-test-tools", _LAZY)
        self.assertIn("settings-diagnostics", _TMPL)
        self.assertIn("settings-diagnostics", _APP)

    def test_store_readiness_no_recovery_row(self) -> None:
        m = re.search(
            r"function applySetupReadinessPanel\(d\)\s*\{([\s\S]*?)\n  function ",
            _LAZY,
        )
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertNotIn("الاسترجاع", body)
        self.assertNotIn("recoveryStatusFromWaCard", body)
        self.assertIn("ربط المتجر", body)
        self.assertIn("الودجيت", body)
        self.assertIn("واتساب", body)
        self.assertIn("/ 3", body)
        self.assertIn("readyCount", body)
        self.assertNotIn("recoveryStatusFromWaCard", _LAZY)

    def test_home_routes_still_present(self) -> None:
        self.assertIn('id="page-home"', _TMPL)
        self.assertIn('id="page-home-setup"', _TMPL)
        self.assertIn('id="page-home-month"', _TMPL)
        self.assertIn("ma-home-experience-root", _TMPL)


if __name__ == "__main__":
    unittest.main()
