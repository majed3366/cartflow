# -*- coding: utf-8 -*-
"""Restart survival verification (Step 4B.4)."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

from services.db_ready_admin_v1 import (
    build_admin_db_ready_health_section_readonly,
    build_restart_survival_admin_alert,
)
from services.db_ready_operational_snapshot_v1 import (
    clear_db_ready_operational_snapshot_for_tests,
    record_restart_survival_snapshot,
)
from services.db_ready_restart_survival_v1 import (
    clear_restart_survival_for_tests,
    evaluate_restart_survival,
    record_first_dashboard_request,
    record_restart_cycle_begin,
)


class DbReadyRestartSurvivalV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        clear_restart_survival_for_tests()
        clear_db_ready_operational_snapshot_for_tests()

    def tearDown(self) -> None:
        clear_restart_survival_for_tests()
        clear_db_ready_operational_snapshot_for_tests()

    def test_evaluate_pass(self) -> None:
        state = {
            "startup_warm_status": "succeeded",
            "restart_warm_completed_at": "2026-06-05T10:00:00+00:00",
            "restart_first_dashboard_at": "2026-06-05T10:00:05+00:00",
            "restart_first_dashboard_cached_verification": True,
            "restart_first_dashboard_heavy_warm": False,
            "restart_first_dashboard_duration_ms": 373.0,
        }
        self.assertEqual(evaluate_restart_survival(state), "PASS")

    def test_evaluate_fail_slow_first_request(self) -> None:
        state = {
            "startup_warm_status": "succeeded",
            "restart_warm_completed_at": "2026-06-05T10:00:00+00:00",
            "restart_first_dashboard_at": "2026-06-05T10:00:05+00:00",
            "restart_first_dashboard_cached_verification": True,
            "restart_first_dashboard_heavy_warm": False,
            "restart_first_dashboard_duration_ms": 1200.0,
        }
        self.assertEqual(evaluate_restart_survival(state), "FAIL")

    def test_record_first_dashboard_emits_log_and_pass(self) -> None:
        now = datetime.now(timezone.utc)
        warm_at = (now - timedelta(seconds=30)).isoformat()
        record_restart_survival_snapshot(
            {
                "startup_warm_status": "succeeded",
                "startup_warm_duration_ms": 9800.0,
                "restart_startup_at": (now - timedelta(seconds=40)).isoformat(),
                "restart_warm_completed_at": warm_at,
                "restart_survival_result": "pending",
            }
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            record_first_dashboard_request(
                duration_ms=373.0,
                cached_verification=True,
                heavy_warm_in_request=False,
            )
        text = buf.getvalue()
        self.assertIn("[RESTART SURVIVAL]", text)
        self.assertIn("result=PASS", text)
        section = build_admin_db_ready_health_section_readonly()
        self.assertEqual(section["restart_survival"]["verification_result"], "PASS")
        self.assertIsNone(build_restart_survival_admin_alert())

    def test_evaluate_fail_before_warm_complete(self) -> None:
        now = datetime.now(timezone.utc)
        state = {
            "startup_warm_status": "succeeded",
            "restart_warm_completed_at": (now + timedelta(seconds=60)).isoformat(),
            "restart_first_dashboard_at": now.isoformat(),
            "restart_first_dashboard_cached_verification": True,
            "restart_first_dashboard_heavy_warm": False,
            "restart_first_dashboard_duration_ms": 200.0,
        }
        self.assertEqual(evaluate_restart_survival(state), "FAIL")

    def test_fail_alert_when_survival_failed(self) -> None:
        record_restart_survival_snapshot(
            {
                "startup_warm_status": "failed",
                "restart_startup_at": "2026-06-05T10:00:00+00:00",
                "restart_warm_completed_at": "2026-06-05T10:00:09+00:00",
                "restart_survival_result": "FAIL",
            }
        )
        alert = build_restart_survival_admin_alert()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.get("kind"), "dashboard_restart_survival_failed")

    def test_restart_cycle_begin_resets_pending(self) -> None:
        record_restart_cycle_begin()
        section = build_admin_db_ready_health_section_readonly()
        self.assertEqual(section["restart_survival"]["verification_result"], "PENDING")


if __name__ == "__main__":
    unittest.main()
