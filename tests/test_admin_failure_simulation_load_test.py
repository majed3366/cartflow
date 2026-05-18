# -*- coding: utf-8 -*-
"""Admin failure-scenario load test harness."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_failure_simulation_load_test import (
    FAILURE_SIMULATION_DISPLAY_UNAVAILABLE_AR,
    clear_failure_simulation_state_for_tests,
    get_latest_failure_simulation_display_ar,
    run_failure_scenarios_load_test,
    stash_latest_failure_simulation_result_for_tests,
)


class AdminFailureSimulationLoadTestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        clear_failure_simulation_state_for_tests()

    def tearDown(self) -> None:
        clear_failure_simulation_state_for_tests()
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def test_all_scenarios_handled_no_crashes(self) -> None:
        summary = run_failure_scenarios_load_test(dry_run_whatsapp=True)
        self.assertEqual(summary["scenarios_total"], 10)
        self.assertEqual(summary["unexpected_crash_count"], 0)
        self.assertEqual(summary["contamination_errors"], 0)
        self.assertEqual(summary["lifecycle_errors"], 0)
        self.assertEqual(summary["failure_handled_count"], 10)
        self.assertEqual(summary["queuepool_timeout_count"], 0)
        results = summary.get("scenario_results") or []
        self.assertEqual(len(results), 10)
        ids = {r["scenario_id"] for r in results}
        self.assertIn("missing_phone", ids)
        self.assertIn("whatsapp_provider_failure", ids)
        self.assertIn("session_conflict", ids)

    def test_endpoint_requires_admin(self) -> None:
        os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.post("/admin/ops/load-test/failure-scenarios", json={})
        self.assertEqual(r.status_code, 503)

    def test_endpoint_with_session(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "fail-sim-admin-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "fail-sim-admin-pass"},
        )
        r = client.post(
            "/admin/ops/load-test/failure-scenarios",
            json={"dry_run_whatsapp": True},
        )
        self.assertEqual(r.status_code, 200, r.text[:400])
        data = r.json()
        self.assertEqual(data.get("scenarios_total"), 10)
        self.assertEqual(data.get("unexpected_crash_count"), 0)

    def test_health_renders_failure_line(self) -> None:
        stash_latest_failure_simulation_result_for_tests(
            {
                "scenarios_total": 10,
                "failure_handled_count": 10,
                "unexpected_crash_count": 0,
                "contamination_errors": 0,
                "lifecycle_errors": 0,
                "avg_duration_ms": 120.0,
            }
        )
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "fail-sim-admin-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "fail-sim-admin-pass"},
        )
        r = client.get("/admin/operational-health")
        self.assertEqual(r.status_code, 200)
        self.assertIn("آخر محاكاة أعطال", r.text)

    def test_health_survives_corrupt_failure_result(self) -> None:
        stash_latest_failure_simulation_result_for_tests(
            {"scenarios_total": None, "failure_handled_count": "x"}
        )
        line = get_latest_failure_simulation_display_ar()
        self.assertEqual(line, FAILURE_SIMULATION_DISPLAY_UNAVAILABLE_AR)
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "fail-sim-admin-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "fail-sim-admin-pass"},
        )
        self.assertEqual(client.get("/admin/operational-health").status_code, 200)
