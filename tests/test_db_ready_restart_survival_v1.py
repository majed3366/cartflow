# -*- coding: utf-8 -*-
"""Restart survival verification (Step 4B.4 / 4B.5)."""
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
    TIMING_BEFORE_WARM_SAFE,
    TIMING_DURING_WARM,
    TIMING_WARM_BEFORE_REQUEST,
    assess_restart_survival,
    clear_restart_survival_for_tests,
    classify_restart_survival_timing,
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

    def test_a_warm_completed_before_request_pass(self) -> None:
        state = {
            "startup_warm_status": "succeeded",
            "restart_warm_completed_at": "2026-06-05T10:00:00+00:00",
            "restart_first_dashboard_at": "2026-06-05T10:00:05+00:00",
            "restart_first_dashboard_cached_verification": True,
            "restart_first_dashboard_used_safe_path": True,
            "restart_first_dashboard_heavy_warm": False,
            "restart_first_dashboard_duration_ms": 373.0,
        }
        self.assertEqual(evaluate_restart_survival(state), "PASS")
        assessment = assess_restart_survival(state)
        self.assertEqual(assessment["timing"], TIMING_WARM_BEFORE_REQUEST)
        self.assertTrue(assessment["protected"])

    def test_b_request_before_warm_completed_protected_pass(self) -> None:
        """Production false FAIL case — warm snapshot timestamp after request."""
        now = datetime.now(timezone.utc)
        state = {
            "startup_warm_status": "succeeded",
            "restart_warm_completed_at": (now + timedelta(seconds=60)).isoformat(),
            "restart_first_dashboard_at": now.isoformat(),
            "restart_first_dashboard_cached_verification": True,
            "restart_first_dashboard_used_safe_path": True,
            "restart_first_dashboard_heavy_warm": False,
            "restart_first_dashboard_duration_ms": 366.9,
        }
        self.assertEqual(evaluate_restart_survival(state), "PASS")
        timing = classify_restart_survival_timing(state, protected=True)
        self.assertEqual(timing, TIMING_BEFORE_WARM_SAFE)

    def test_c_heavy_warm_before_warm_complete_fail(self) -> None:
        now = datetime.now(timezone.utc)
        state = {
            "startup_warm_status": "succeeded",
            "restart_warm_completed_at": (now + timedelta(seconds=60)).isoformat(),
            "restart_first_dashboard_at": now.isoformat(),
            "restart_first_dashboard_cached_verification": False,
            "restart_first_dashboard_used_safe_path": False,
            "restart_first_dashboard_heavy_warm": True,
            "restart_first_dashboard_duration_ms": 500.0,
        }
        self.assertEqual(evaluate_restart_survival(state), "FAIL")
        self.assertEqual(assess_restart_survival(state)["reason"], "heavy_warm_in_request")

    def test_d_safe_path_without_cached_at_entry_pass(self) -> None:
        state = {
            "startup_warm_status": "running",
            "restart_warm_completed_at": None,
            "restart_first_dashboard_at": "2026-06-05T10:00:01+00:00",
            "restart_first_dashboard_cached_verification": False,
            "restart_first_dashboard_used_safe_path": True,
            "restart_first_dashboard_heavy_warm": False,
            "restart_first_dashboard_duration_ms": 420.0,
        }
        self.assertEqual(evaluate_restart_survival(state), "PASS")
        self.assertEqual(
            classify_restart_survival_timing(state, protected=True),
            TIMING_DURING_WARM,
        )

    def test_e_startup_warm_failed(self) -> None:
        state = {
            "startup_warm_status": "failed",
            "restart_first_dashboard_at": "2026-06-05T10:00:01+00:00",
            "restart_first_dashboard_cached_verification": True,
            "restart_first_dashboard_heavy_warm": False,
            "restart_first_dashboard_duration_ms": 300.0,
        }
        self.assertEqual(evaluate_restart_survival(state), "FAIL")

    def test_f_slow_first_request_fail(self) -> None:
        state = {
            "startup_warm_status": "succeeded",
            "restart_warm_completed_at": "2026-06-05T10:00:00+00:00",
            "restart_first_dashboard_at": "2026-06-05T10:00:05+00:00",
            "restart_first_dashboard_cached_verification": True,
            "restart_first_dashboard_heavy_warm": False,
            "restart_first_dashboard_duration_ms": 1200.0,
        }
        self.assertEqual(evaluate_restart_survival(state), "FAIL")

    def test_record_first_dashboard_emits_new_log_format(self) -> None:
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
                used_safe_path=True,
                heavy_warm_in_request=False,
            )
        text = buf.getvalue()
        self.assertIn("[RESTART SURVIVAL]", text)
        self.assertIn("timing=", text)
        self.assertIn("protected=true", text)
        self.assertIn("result=PASS", text)
        self.assertIn("reason=fast_protected_request", text)

    def test_production_case_pass_in_admin(self) -> None:
        now = datetime.now(timezone.utc)
        record_restart_survival_snapshot(
            {
                "startup_warm_status": "succeeded",
                "restart_warm_completed_at": (now + timedelta(seconds=30)).isoformat(),
                "restart_first_dashboard_at": now.isoformat(),
                "restart_first_dashboard_duration_ms": 414.5,
                "restart_first_dashboard_cached_verification": True,
                "restart_first_dashboard_used_safe_path": True,
                "restart_first_dashboard_heavy_warm": False,
                "restart_survival_result": "PASS",
                "restart_survival_timing": TIMING_BEFORE_WARM_SAFE,
                "restart_survival_protected": True,
                "restart_survival_reason": "fast_protected_request",
            }
        )
        section = build_admin_db_ready_health_section_readonly()
        rs = section["restart_survival"]
        self.assertEqual(rs["verification_result"], "PASS")
        self.assertIn("تمت حماية", rs.get("pass_headline_ar") or "")
        self.assertIsNone(build_restart_survival_admin_alert())

    def test_fail_alert_when_survival_failed(self) -> None:
        record_restart_survival_snapshot(
            {
                "startup_warm_status": "failed",
                "restart_startup_at": "2026-06-05T10:00:00+00:00",
                "restart_warm_completed_at": "2026-06-05T10:00:09+00:00",
                "restart_first_dashboard_at": "2026-06-05T10:00:10+00:00",
                "restart_first_dashboard_duration_ms": 500.0,
                "restart_first_dashboard_heavy_warm": True,
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
