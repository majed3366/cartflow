# -*- coding: utf-8 -*-
"""Tests for rule-based Admin Operations action engine (V1)."""
from __future__ import annotations

import unittest

from services.admin_operations_action_engine_v1 import (
    resolve_alert_guidance,
    resolve_current_issue_guidance,
    resolve_dashboard_db_ready_guidance,
    resolve_operations_guidance,
    resolve_widget_issue_guidance,
)
from services.db_ready_operational_snapshot_v1 import HEALTHY_MAX_MS


class AdminOperationsActionEngineTests(unittest.TestCase):
    def test_dashboard_restart_survival_failed_alert(self) -> None:
        g = resolve_alert_guidance("dashboard_restart_survival_failed")
        self.assertIn("Startup Warm", g["action_en"])
        self.assertIn("PASS", g["verification_en"])

    def test_dashboard_db_init_slow_alert(self) -> None:
        g = resolve_alert_guidance("dashboard_db_init_slow")
        self.assertIn("DB Ready", g["action_en"])
        self.assertIn(str(int(HEALTHY_MAX_MS)), g["verification_en"])

    def test_widget_runtime_missing_alert(self) -> None:
        g = resolve_alert_guidance("widget_runtime_missing")
        self.assertIn("runtime beacon", g["action_en"].lower())
        self.assertIn("Widget Health", g["verification_en"])

    def test_healthy_dashboard_guidance(self) -> None:
        g = resolve_dashboard_db_ready_guidance(
            operational_status="healthy",
            diagnostics={
                "last_duration_ms": 367.0,
                "startup_warm_status": "succeeded",
                "last_request_cached_verification": True,
                "restart_survival": {
                    "verification_result": "PASS",
                    "first_dashboard_duration_ms": 367.0,
                    "first_dashboard_cached_verification": True,
                },
            },
        )
        self.assertIn("operating normally", g["problem_en"])
        self.assertIn("No action required", g["action_en"])
        lines = " ".join(g["verification_lines_en"])
        self.assertIn("Restart Survival = PASS", lines)
        self.assertIn("Cached verification = Yes", lines)

    def test_slow_dashboard_guidance(self) -> None:
        g = resolve_dashboard_db_ready_guidance(
            operational_status="slow",
            diagnostics={"last_duration_ms": 4200.0},
        )
        self.assertIn("slower than expected", g["problem_en"])
        self.assertIn("DB Ready", g["action_en"])

    def test_fail_restart_survival_guidance(self) -> None:
        g = resolve_dashboard_db_ready_guidance(
            operational_status="healthy",
            diagnostics={
                "restart_survival": {"verification_result": "FAIL"},
            },
        )
        self.assertIn("protection failed", g["problem_en"])
        self.assertIn("Startup Warm", g["action_en"])

    def test_resolve_operations_guidance_unified(self) -> None:
        g = resolve_operations_guidance(
            card_key="dashboard_db_ready",
            operational_status="healthy",
            diagnostics={"last_duration_ms": 200.0},
        )
        self.assertEqual(g["where_en"], "Dashboard Initialization")

        alert = resolve_operations_guidance(alert_type="dashboard_db_init_slow")
        self.assertIn("slower than expected", alert["problem_en"])

    def test_current_issue_guidance_full_fields(self) -> None:
        g = resolve_current_issue_guidance("dashboard_restart_survival_failed")
        self.assertTrue(g["problem_en"])
        self.assertTrue(g["impact_en"])
        self.assertEqual(g["where_en"], "Dashboard Initialization")
        self.assertTrue(g["action_en"])
        self.assertTrue(g["verification_en"])

    def test_widget_issue_guidance_maps_runtime_missing(self) -> None:
        g = resolve_widget_issue_guidance("widget_runtime_missing")
        self.assertIn("runtime", g["problem_en"].lower())
        self.assertIn("beacon", g["suggested_action_en"].lower())


if __name__ == "__main__":
    unittest.main()
