# -*- coding: utf-8 -*-
"""Tests for Admin Operations V2 Critical Alert Hook."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from services.admin_operations_critical_alerts_v1 import (
    _should_raise_db_init_slow_alert,
    build_critical_alerts_readonly,
)
from services.db_ready_operational_snapshot_v1 import (
    clear_db_ready_operational_snapshot_for_tests,
    record_db_ready_run,
    record_restart_survival_snapshot,
)


def _no_widget_alerts():
    return patch(
        "services.admin_operations_critical_alerts_v1._collect_widget_runtime_alert",
        return_value=None,
    )


class CriticalAlertsFilterTests(unittest.TestCase):
    def test_db_init_slow_suppressed_when_protected(self) -> None:
        snap = {"last_request_cached_verification": True, "last_duration_ms": 4200.0}
        rs = {
            "verification_result": "PASS",
            "first_dashboard_duration_ms": 367.0,
            "first_dashboard_cached_verification": True,
        }
        self.assertFalse(_should_raise_db_init_slow_alert(snap, rs))

    def test_db_init_slow_raised_when_survival_not_pass(self) -> None:
        snap = {"last_request_cached_verification": True}
        rs = {"verification_result": "PENDING", "first_dashboard_duration_ms": 0}
        self.assertTrue(_should_raise_db_init_slow_alert(snap, rs))

    def test_db_init_slow_raised_when_first_request_slow(self) -> None:
        snap = {"last_request_cached_verification": True}
        rs = {
            "verification_result": "PASS",
            "first_dashboard_duration_ms": 1500.0,
            "first_dashboard_cached_verification": True,
        }
        self.assertTrue(_should_raise_db_init_slow_alert(snap, rs))

    def test_db_init_slow_not_raised_when_fail_covered_elsewhere(self) -> None:
        snap = {}
        rs = {"verification_result": "FAIL", "first_dashboard_duration_ms": 2000.0}
        self.assertFalse(_should_raise_db_init_slow_alert(snap, rs))


class CriticalAlertsBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_db_ready_operational_snapshot_for_tests()

    def tearDown(self) -> None:
        clear_db_ready_operational_snapshot_for_tests()

    def test_healthy_when_no_issues(self) -> None:
        with _no_widget_alerts():
            record_db_ready_run(
                {
                    "trace_id": "ok111111",
                    "duration_ms": 200.0,
                    "slowest_stage": "schema_verify",
                    "success": True,
                }
            )
            record_restart_survival_snapshot(
                {
                    "startup_warm_status": "succeeded",
                    "restart_first_dashboard_duration_ms": 200.0,
                    "restart_first_dashboard_cached_verification": True,
                    "restart_survival_result": "PASS",
                }
            )
            payload = build_critical_alerts_readonly()
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["alerts"], [])
        self.assertIn("No critical operational issues", payload["healthy"]["message_en"])

    def test_restart_survival_fail_alert(self) -> None:
        with _no_widget_alerts():
            record_restart_survival_snapshot(
                {
                    "startup_warm_status": "failed",
                    "restart_first_dashboard_duration_ms": 500.0,
                    "restart_survival_result": "FAIL",
                }
            )
            payload = build_critical_alerts_readonly()
        kinds = [a["kind"] for a in payload["alerts"]]
        self.assertIn("dashboard_restart_survival_failed", kinds)
        alert = next(a for a in payload["alerts"] if a["kind"] == "dashboard_restart_survival_failed")
        self.assertEqual(alert["severity"], "critical")
        self.assertIn("startup protection failed", alert["problem_en"].lower())

    def test_no_db_init_slow_when_protected_pass(self) -> None:
        with _no_widget_alerts():
            record_db_ready_run(
                {
                    "trace_id": "slow2222",
                    "duration_ms": 4200.0,
                    "slowest_stage": "identity_backfill",
                    "success": True,
                }
            )
            record_restart_survival_snapshot(
                {
                    "startup_warm_status": "succeeded",
                    "restart_first_dashboard_duration_ms": 367.0,
                    "restart_first_dashboard_cached_verification": True,
                    "restart_survival_result": "PASS",
                }
            )
            payload = build_critical_alerts_readonly()
        kinds = [a["kind"] for a in payload["alerts"]]
        self.assertNotIn("dashboard_db_init_slow", kinds)

    def test_request_health_failure_alert(self) -> None:
        with _no_widget_alerts():
            record_db_ready_run(
                {
                    "trace_id": "fail3333",
                    "duration_ms": 900.0,
                    "slowest_stage": "schema_verify",
                    "success": False,
                    "error": "bootstrap lock timeout",
                }
            )
            payload = build_critical_alerts_readonly()
        kinds = [a["kind"] for a in payload["alerts"]]
        self.assertIn("request_health_failure", kinds)

    def test_widget_runtime_alert_ignores_demo_stores(self) -> None:
        widget_health = {
            "issues": [
                {
                    "kind": "runtime_beacon_missing",
                    "severity": "critical",
                    "store_slug": "loadtest-store-013",
                    "store_name": "Load Test",
                }
            ]
        }
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value=widget_health,
        ):
            record_restart_survival_snapshot(
                {
                    "startup_warm_status": "succeeded",
                    "restart_survival_result": "PASS",
                }
            )
            payload = build_critical_alerts_readonly()
        kinds = [a["kind"] for a in payload["alerts"]]
        self.assertNotIn("widget_runtime_missing", kinds)


if __name__ == "__main__":
    unittest.main()
