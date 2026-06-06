# -*- coding: utf-8 -*-
"""Tests for Admin Operations → Widget Health v1 (read-only observability)."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from services.widget_health_v1 import (
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    build_admin_widget_health_section_readonly,
    build_store_widget_health_row,
    widget_health_from_beacon,
)

_ROOT = Path(__file__).resolve().parents[1]
_LOADER = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_loader.js"
_CONFIG = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_config.js"
_WIDGET_LOADER = _ROOT / "static" / "widget_loader.js"


def _store(*, slug="demo-shop", name="Demo", page_url="https://demo.zid.store/",
           runtime_truth=None, last_seen="2026-06-01T00:00:00Z",
           truth_status="verified", beacon=True):
    beacon_json = None
    if beacon:
        body = {"page_url": page_url, "runtime_truth": runtime_truth or {}}
        beacon_json = json.dumps(body, ensure_ascii=False)
    return {
        "store_id": 1,
        "store_slug": slug,
        "display_name": name,
        "widget_last_runtime_slug": "v2-widget-health-v1",
        "widget_last_seen_at": last_seen,
        "widget_runtime_truth_status": truth_status,
        "widget_last_beacon_json": beacon_json,
    }


class WidgetHealthStatusRulesTests(unittest.TestCase):
    def test_healthy_store_all_signals(self):
        rt = {
            "config_loaded": True,
            "widget_enabled": True,
            "widget_rendered": True,
            "widget_health": {
                "module_load_status": "ok",
                "failed_modules": [],
                "bootstrap_ready": True,
                "bootstrap_blocked": False,
                "missing_runtime_objects": [],
                "runtime_version": "v2-widget-health-v1",
                "widget_shown": True,
            },
        }
        row = build_store_widget_health_row(_store(page_url="https://demo.zid.store/p/1", runtime_truth=rt))
        self.assertEqual(row["status"], STATUS_HEALTHY)
        self.assertEqual(row["issue_kinds"], [])
        self.assertEqual(row["platform"], "Zid")

    def test_missing_beacon_is_warning(self):
        row = build_store_widget_health_row(_store(beacon=False, last_seen="2026-06-01T00:00:00Z"))
        self.assertEqual(row["status"], STATUS_WARNING)
        self.assertIn("runtime_beacon_missing", row["issue_kinds"])

    def test_no_beacon_and_never_seen_flags_not_seen(self):
        row = build_store_widget_health_row(_store(beacon=False, last_seen=None))
        self.assertIn("widget_not_seen", row["issue_kinds"])
        self.assertIn("runtime_beacon_missing", row["issue_kinds"])


class WidgetHealthIncidentTests(unittest.TestCase):
    """The real-world Zid incident must be detectable."""

    def test_bootstrap_blocked_is_critical(self):
        rt = {
            "config_loaded": True,
            "widget_health": {
                "module_load_status": "failed",
                "failed_modules": ["cartflow_widget_triggers.js"],
                "bootstrap_ready": False,
                "bootstrap_blocked": True,
                "missing_runtime_objects": [
                    "CartflowWidgetRuntime.Triggers",
                    "CartflowWidgetRuntime.TriggerOrchestrator",
                ],
            },
        }
        row = build_store_widget_health_row(_store(runtime_truth=rt))
        self.assertEqual(row["status"], STATUS_CRITICAL)
        self.assertIn("widget_bootstrap_blocked", row["issue_kinds"])
        self.assertIn("widget_module_failed", row["issue_kinds"])
        self.assertIn("widget_runtime_object_missing", row["issue_kinds"])

    def test_module_failed_alone_is_critical(self):
        rt = {
            "config_loaded": True,
            "widget_health": {
                "module_load_status": "failed",
                "failed_modules": ["cartflow_widget_triggers.js"],
            },
        }
        row = build_store_widget_health_row(_store(runtime_truth=rt))
        self.assertEqual(row["status"], STATUS_CRITICAL)
        self.assertIn("widget_module_failed", row["issue_kinds"])


class WidgetHealthCartBridgeTests(unittest.TestCase):
    def test_cart_event_bridge_missing_on_cart_page(self):
        rt = {
            "config_loaded": True,
            "widget_health": {"bootstrap_ready": True, "module_load_status": "ok"},
        }
        row = build_store_widget_health_row(
            _store(page_url="https://demo.zid.store/cart", runtime_truth=rt)
        )
        self.assertIn("cart_event_bridge_missing", row["issue_kinds"])
        self.assertEqual(row["cart_event_bridge_status"], "missing")

    def test_widget_not_shown_after_cart_event_is_critical(self):
        rt = {
            "config_loaded": True,
            "hesitation_trigger_enabled": True,
            "cart_bridge": {
                "last_event_type": "add_to_cart",
                "last_event_at": "2026-06-01T01:00:00Z",
                "hesitation_armed_from_cart_event": True,
            },
            "widget_health": {
                "bootstrap_ready": True,
                "module_load_status": "ok",
                "widget_shown": False,
            },
        }
        row = build_store_widget_health_row(_store(runtime_truth=rt))
        self.assertEqual(row["status"], STATUS_CRITICAL)
        self.assertIn("widget_not_shown_after_cart_event", row["issue_kinds"])

    def test_hesitation_not_armed_warning(self):
        rt = {
            "config_loaded": True,
            "hesitation_trigger_enabled": True,
            "cart_bridge": {
                "last_event_type": "add_to_cart",
                "last_event_at": "2026-06-01T01:00:00Z",
                "hesitation_armed_from_cart_event": False,
            },
            "widget_health": {"bootstrap_ready": True, "module_load_status": "ok", "widget_shown": True},
        }
        row = build_store_widget_health_row(_store(runtime_truth=rt))
        self.assertIn("hesitation_not_armed", row["issue_kinds"])


class WidgetHealthParseTests(unittest.TestCase):
    def test_health_falls_back_to_top_level_runtime_version(self):
        beacon = json.dumps(
            {"runtime_version": "v2-x", "runtime_truth": {"config_loaded": True, "widget_health": {}}}
        )
        h = widget_health_from_beacon(beacon)
        self.assertEqual(h["runtime_version"], "v2-x")
        self.assertTrue(h["has_runtime_truth"])

    def test_cors_error_detected_from_last_runtime_error(self):
        rt = {
            "config_loaded": True,
            "widget_health": {
                "bootstrap_ready": True,
                "module_load_status": "ok",
                "last_runtime_error": "blocked by CORS policy",
            },
        }
        row = build_store_widget_health_row(_store(runtime_truth=rt))
        self.assertIn("widget_cors_error", row["issue_kinds"])


class WidgetHealthSectionTests(unittest.TestCase):
    def test_section_aggregates_stores_and_issues(self):
        healthy = _store(
            slug="ok-shop",
            page_url="https://ok.zid.store/p/1",
            runtime_truth={
                "config_loaded": True,
                "widget_health": {"bootstrap_ready": True, "module_load_status": "ok", "widget_shown": True},
            },
        )
        broken = _store(
            slug="broken-shop",
            runtime_truth={
                "config_loaded": True,
                "widget_health": {"bootstrap_blocked": True, "failed_modules": ["cartflow_widget_triggers.js"]},
            },
        )
        out = build_admin_widget_health_section_readonly(stores=[healthy, broken])
        self.assertEqual(out["section"], "widget_health")
        self.assertEqual(out["summary"]["total_stores"], 2)
        self.assertEqual(out["summary"]["critical"], 1)
        self.assertGreaterEqual(out["summary"]["total_issues"], 1)
        # Critical issues sorted first.
        self.assertEqual(out["issues"][0]["severity"], STATUS_CRITICAL)


class WidgetHealthIssueGroupingTests(unittest.TestCase):
    """V3 presentation-only grouping (route layer, no service changes)."""

    def _groups(self, issues):
        from routes.admin_operations import _widget_health_issue_groups

        return _widget_health_issue_groups(issues)

    def test_identical_issues_collapse_into_one_group(self):
        issues = [
            {"kind": "runtime_beacon_missing", "severity": "warning", "store_slug": "a", "store_name": "A"},
            {"kind": "runtime_beacon_missing", "severity": "warning", "store_slug": "b", "store_name": "B"},
            {"kind": "runtime_beacon_missing", "severity": "warning", "store_slug": "c", "store_name": "C"},
        ]
        groups = self._groups(issues)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["count"], 3)
        self.assertEqual(len(groups[0]["stores"]), 3)

    def test_groups_sorted_critical_first_then_count(self):
        issues = [
            {"kind": "runtime_beacon_missing", "severity": "warning", "store_slug": "a", "store_name": "A"},
            {"kind": "runtime_beacon_missing", "severity": "warning", "store_slug": "b", "store_name": "B"},
            {"kind": "widget_bootstrap_blocked", "severity": "critical", "store_slug": "c", "store_name": "C"},
        ]
        groups = self._groups(issues)
        self.assertEqual(groups[0]["kind"], "widget_bootstrap_blocked")
        self.assertEqual(groups[0]["severity"], "critical")
        self.assertEqual(groups[1]["kind"], "runtime_beacon_missing")
        self.assertEqual(groups[1]["count"], 2)

    def test_empty_issues_yields_no_groups(self):
        self.assertEqual(self._groups([]), [])


class WidgetHealthNeedsAttentionTests(unittest.TestCase):
    """V4 manager-first summary (route layer, presentation-only)."""

    def _attn(self, stores):
        from routes.admin_operations import _widget_health_needs_attention

        return _widget_health_needs_attention(stores)

    def test_one_row_per_affected_store_business_language(self):
        stores = [
            {"store_name": "CartFlow", "store_slug": "cf", "status": "critical",
             "issues": [{"kind": "widget_not_seen", "severity": "critical", "problem_ar": "x"}]},
            {"store_name": "X", "store_slug": "x", "status": "warning",
             "issues": [{"kind": "runtime_beacon_missing", "severity": "warning", "problem_ar": "x"}]},
            {"store_name": "OK", "store_slug": "ok", "status": "healthy", "issues": []},
        ]
        attn = self._attn(stores)
        self.assertEqual(len(attn), 2)  # healthy excluded
        names = {a["store_name"] for a in attn}
        self.assertEqual(names, {"CartFlow", "X"})
        cf = next(a for a in attn if a["store_name"] == "CartFlow")
        self.assertEqual(cf["headline_ar"], "الودجت لا يظهر للعملاء")
        self.assertEqual(cf["priority_key"], "high")
        # No technical terms leak into the headline.
        for a in attn:
            low = a["headline_ar"].lower()
            self.assertNotIn("beacon", low)
            self.assertNotIn("runtime", low)
            self.assertNotIn("config", low)

    def test_high_priority_sorted_first(self):
        stores = [
            {"store_name": "Low", "store_slug": "lo", "status": "warning",
             "issues": [{"kind": "widget_settings_mismatch", "severity": "warning", "problem_ar": "x"}]},
            {"store_name": "High", "store_slug": "hi", "status": "critical",
             "issues": [{"kind": "widget_bootstrap_blocked", "severity": "critical", "problem_ar": "x"}]},
        ]
        attn = self._attn(stores)
        self.assertEqual(attn[0]["store_name"], "High")
        self.assertEqual(attn[0]["priority_ar"], "عالية")

    def test_picks_most_important_issue_per_store(self):
        stores = [
            {"store_name": "Multi", "store_slug": "m", "status": "critical",
             "issues": [
                 {"kind": "widget_settings_mismatch", "severity": "warning", "problem_ar": "x"},
                 {"kind": "widget_bootstrap_blocked", "severity": "critical", "problem_ar": "x"},
             ]},
        ]
        attn = self._attn(stores)
        self.assertEqual(len(attn), 1)
        self.assertEqual(attn[0]["headline_ar"], "تعذر تشغيل الودجت")


class WidgetHealthJsWiringTests(unittest.TestCase):
    def test_loader_records_widget_health(self):
        text = _LOADER.read_text(encoding="utf-8")
        self.assertIn("__cartflowWidgetHealth", text)
        self.assertIn("bootstrap_blocked", text)
        self.assertIn("missing_runtime_objects", text)
        self.assertIn("failed_modules", text)

    def test_config_snapshot_includes_widget_health(self):
        text = _CONFIG.read_text(encoding="utf-8")
        self.assertIn("widget_health", text)
        self.assertIn("__cartflowWidgetHealth", text)

    def test_widget_loader_runtime_version_bumped(self):
        self.assertIn("v2-zid-cart-sync-v1", _WIDGET_LOADER.read_text(encoding="utf-8"))

    def test_admin_template_defaults_to_real_and_groups(self):
        overview = (_ROOT / "templates" / "admin_operations_center_v1.html").read_text(encoding="utf-8")
        self.assertIn("DEFAULT_TYPE = 'real'", overview)
        self.assertIn("data-wh-group", overview)
        self.assertIn("data-wh-attn", overview)
        partial = (
            _ROOT / "templates" / "partials" / "admin_operations_widget_health_section.html"
        ).read_text(encoding="utf-8")
        self.assertIn("data-wh-group", partial)
        self.assertIn("data-wh-affected-store", partial)
        self.assertIn("data-wh-count", partial)
        # V4: manager-first summary is the first section.
        self.assertIn("data-wh-attn", partial)
        self.assertIn("المتاجر التي تحتاج انتباهاً", partial)
        self.assertLess(
            partial.index("المتاجر التي تحتاج انتباهاً"),
            partial.index("المشاكل الحالية للودجِت"),
        )


if __name__ == "__main__":
    unittest.main()
