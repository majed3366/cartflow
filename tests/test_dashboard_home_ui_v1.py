# -*- coding: utf-8 -*-
"""Dashboard Home Intelligence-First V3 — presentation + readiness contract."""
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


def _section_order_positions(js: str) -> list[int]:
    """Return render call order positions inside renderHome."""
    m = re.search(r"function renderHome\(summary\)[\s\S]*?return\s*\(([\s\S]*?)\);\s*\}", js)
    assert m, "renderHome body not found"
    body = m.group(1)
    keys = [
        "renderHero(",
        "renderKnowledge(",
        "renderMetrics(",
        "renderAttention(",
        "renderPerformance(",
        "renderTimeline(",
    ]
    return [body.index(k) for k in keys]


class DashboardHomeIntelV3Tests(unittest.TestCase):
    def test_assets_wired_in_template(self) -> None:
        self.assertIn("merchant_dashboard_home_v1.js", _TMPL)
        self.assertIn("merchant_dashboard_home_v1.css", _TMPL)

    def test_apply_export_and_lazy_priority(self) -> None:
        self.assertIn("maApplyDashboardHomeV1", _JS)
        self.assertIn("maApplyDashboardHomeV1", _LAZY)

    def test_canonical_section_order_hero_knowledge_first(self) -> None:
        positions = _section_order_positions(_JS)
        self.assertEqual(positions, sorted(positions))
        # Explicit markers for intelligence-first order
        self.assertIn('data-ecc-section="hero"', _JS)
        self.assertIn('data-ecc-section="knowledge"', _JS)
        self.assertIn('data-ecc-section="metrics"', _JS)
        self.assertIn('data-ecc-section="attention"', _JS)
        self.assertIn('data-ecc-section="performance"', _JS)
        self.assertIn('data-ecc-section="timeline"', _JS)
        hero_i = _JS.index('data-ecc-section="hero"')
        kl_i = _JS.index('data-ecc-section="knowledge"')
        metrics_i = _JS.index('data-ecc-section="metrics"')
        self.assertLess(hero_i, kl_i)
        self.assertLess(kl_i, metrics_i)

    def test_exactly_four_quick_metrics(self) -> None:
        for label in (
            "الإيرادات المستعادة",
            "العملاء المشترون",
            "العملاء العائدون",
            "حالة المعرفة",
        ):
            self.assertIn(label, _JS)
        # Only one metrics block
        self.assertEqual(_JS.count('data-ecc-section="metrics"'), 1)

    def test_knowledge_structure(self) -> None:
        for step in ("الملاحظة", "الدليل", "التفسير", "التوصية", "الثقة"):
            self.assertIn(step, _JS)
        self.assertIn("ma-ecc-band--knowledge", _CSS)

    def test_timeline_empty_preserves_structure(self) -> None:
        self.assertIn("ma-ecc-timeline--empty", _JS)
        self.assertIn("ma-ecc-timeline__item--placeholder", _JS)
        self.assertIn("سيظهر هنا عند تسجيل شراء حقيقي", _JS)

    def test_no_fake_returned_kpi(self) -> None:
        self.assertIn("Customers returned: no governed today-KPI", _JS)
        self.assertIn("never invent", _JS.lower())

    def test_mobile_metric_grid_2x2(self) -> None:
        self.assertIn("grid-template-columns: 1fr 1fr", _CSS)
        self.assertIn(".ma-ecc-metrics", _CSS)

    def test_desktop_split_grid(self) -> None:
        self.assertIn(".ma-ecc-split", _CSS)
        self.assertIn("grid-template-columns: 1.15fr 0.85fr", _CSS)

    def test_diagnostics_absent_from_home(self) -> None:
        self.assertNotIn('data-home-nav="test-tools"', _TMPL)
        self.assertNotIn("page-home-test-tools", _TMPL)
        self.assertNotIn("page-home-test-tools", _LAZY)
        self.assertIn("settings-diagnostics", _TMPL)
        self.assertIn("settings-diagnostics", _APP)

    def test_store_readiness_no_recovery_row(self) -> None:
        # Extract applySetupReadinessPanel body
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
