# -*- coding: utf-8 -*-
"""Tests for rule-based Admin Operations action engine (V1 / V1.1)."""
from __future__ import annotations

import unittest

from services.admin_operations_action_engine_v1 import (
    resolve_alert_guidance,
    resolve_current_issue_guidance,
    resolve_dashboard_db_ready_guidance,
    resolve_operations_guidance,
    resolve_widget_issue_guidance,
)


class AdminOperationsActionEngineTests(unittest.TestCase):
    def test_dashboard_restart_survival_failed_operational_action(self) -> None:
        g = resolve_alert_guidance("dashboard_restart_survival_failed")
        self.assertIn("Verify Startup Warm", g["action_en"])
        self.assertNotIn("logs", g["action_en"].lower())
        self.assertIn("Review DB Ready diagnostics", g["investigation_lines_en"])
        self.assertEqual(g["verification_lines_en"], ["Restart Survival = PASS"])

    def test_dashboard_db_init_slow_operational_action(self) -> None:
        g = resolve_alert_guidance("dashboard_db_init_slow")
        self.assertIn("No immediate action required", g["action_en"])
        self.assertNotIn("logs", g["action_en"].lower())
        self.assertIn("Restart Survival = FAIL", g["investigation_lines_en"])
        self.assertIn("Restart Survival = PASS", g["verification_lines_en"])

    def test_widget_runtime_missing_operational_action(self) -> None:
        g = resolve_alert_guidance("widget_runtime_missing")
        self.assertIn("runtime connectivity", g["action_en"].lower())
        self.assertIn("Widget Health = Healthy", g["verification_lines_en"])
        self.assertIn("Runtime beacon received", g["verification_lines_en"])

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

    def test_slow_dashboard_protected_guidance(self) -> None:
        g = resolve_dashboard_db_ready_guidance(
            operational_status="slow",
            diagnostics={
                "last_duration_ms": 4200.0,
                "last_request_cached_verification": True,
                "restart_survival": {
                    "verification_result": "PASS",
                    "first_dashboard_duration_ms": 367.0,
                    "first_dashboard_cached_verification": True,
                },
            },
        )
        self.assertIn("slower than expected", g["problem_en"])
        self.assertIn("No immediate action required", g["action_en"])
        self.assertIn("Investigate only if:", g["investigation_intro_en"])
        self.assertNotIn("logs", g["action_en"].lower())

    def test_slow_dashboard_unprotected_guidance(self) -> None:
        g = resolve_dashboard_db_ready_guidance(
            operational_status="slow",
            diagnostics={
                "last_duration_ms": 4200.0,
                "restart_survival": {"verification_result": "PENDING"},
            },
        )
        self.assertIn("confirm startup protection", g["action_en"].lower())
        self.assertIn("Review DB Ready diagnostics", g["investigation_lines_en"])

    def test_fail_restart_survival_guidance(self) -> None:
        g = resolve_dashboard_db_ready_guidance(
            operational_status="healthy",
            diagnostics={
                "restart_survival": {"verification_result": "FAIL"},
            },
        )
        self.assertIn("protection failed", g["problem_en"])
        self.assertIn("Verify Startup Warm", g["action_en"])
        self.assertIn("Review DB Ready diagnostics", g["investigation_lines_en"])
        self.assertEqual(g["verification_lines_en"], ["Restart Survival = PASS"])

    def test_resolve_operations_guidance_unified(self) -> None:
        g = resolve_operations_guidance(
            card_key="dashboard_db_ready",
            operational_status="healthy",
            diagnostics={"last_duration_ms": 200.0},
        )
        self.assertEqual(g["where_en"], "Dashboard Initialization")

        alert = resolve_operations_guidance(alert_type="dashboard_db_init_slow")
        self.assertIn("slower than expected", alert["problem_en"])
        self.assertIn("No immediate action required", alert["action_en"])

    def test_current_issue_guidance_full_fields(self) -> None:
        g = resolve_current_issue_guidance("dashboard_restart_survival_failed")
        self.assertTrue(g["problem_en"])
        self.assertTrue(g["impact_en"])
        self.assertEqual(g["where_en"], "Dashboard Initialization")
        self.assertTrue(g["action_en"])
        self.assertTrue(g["verification_lines_en"])

    def test_widget_issue_guidance_maps_runtime_missing(self) -> None:
        g = resolve_widget_issue_guidance("widget_runtime_missing")
        self.assertIn("runtime", g["problem_en"].lower())
        self.assertIn("connectivity", g["suggested_action_en"].lower())
        self.assertIn("Runtime beacon received", g["verification_lines_en"])

    def test_no_check_logs_in_primary_actions(self) -> None:
        for kind in (
            "dashboard_restart_survival_failed",
            "dashboard_db_init_slow",
            "failed_recovery",
            "stale_recovery",
        ):
            g = resolve_alert_guidance(kind)
            self.assertNotIn("check logs", g["action_en"].lower())
            self.assertNotIn("review db ready stages in logs", g["action_en"].lower())


if __name__ == "__main__":
    unittest.main()
