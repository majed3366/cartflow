# -*- coding: utf-8 -*-
"""
Operational Maturity v1 — audit matrix (read-only).

See ``docs/audit_operational_maturity_v1.md``.
"""
from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from services.admin_operational_control import (
    build_admin_operational_control_readonly,
    clear_verification_state_for_tests,
)
from services.admin_operational_health import (
    clear_operational_health_buffers_for_tests,
    record_db_pool_timeout,
)
from services.cartflow_admin_operational_summary import (
    build_admin_operational_summary_readonly,
)
from services.cartflow_production_readiness import build_cartflow_production_readiness_report
from services.cartflow_runtime_health import (
    ANOMALY_PROVIDER_SEND_FAILURE,
    build_runtime_health_snapshot,
    record_runtime_anomaly,
)


class OperationalMaturityAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        clear_operational_health_buffers_for_tests()
        clear_verification_state_for_tests()

    def tearDown(self) -> None:
        clear_operational_health_buffers_for_tests()
        clear_verification_state_for_tests()

    def test_audit_01_health_visibility_modules(self) -> None:
        p = build_admin_operational_control_readonly()
        self.assertEqual(p.get("version"), "admin_operational_control_v2")
        for key in (
            "admin_risk_summary",
            "admin_impact_layer",
            "admin_actions_layer",
            "admin_verification_layer",
            "admin_operational_timeline",
            "quick_answers",
        ):
            self.assertIn(key, p)
        snap = build_runtime_health_snapshot()
        self.assertIn("lifecycle_consistency_runtime", snap)
        self.assertIn("duplicate_protection_runtime", snap)

    def test_audit_02_detect_pool_timeout_risk(self) -> None:
        record_db_pool_timeout(detail="audit pool")
        risk = build_admin_operational_control_readonly()["admin_risk_summary"]
        self.assertTrue(risk.get("risk_detected"))

    def test_audit_03_risk_explanation_quick_answers(self) -> None:
        record_db_pool_timeout(detail="explain")
        qa = build_admin_operational_control_readonly()["quick_answers"]
        self.assertIn("is_healthy_ar", qa)
        self.assertIn("what_failing_ar", qa)
        self.assertIn("who_affected_ar", qa)

    def test_audit_04_recommended_actions_layer(self) -> None:
        record_db_pool_timeout(detail="action")
        actions = build_admin_operational_control_readonly()["admin_actions_layer"]
        self.assertTrue(actions.get("has_actions"))
        self.assertTrue(actions["items"][0].get("recommended_action_ar"))

    def test_audit_05_verify_fix_after_clear(self) -> None:
        record_db_pool_timeout(detail="v1")
        build_admin_operational_control_readonly()
        clear_operational_health_buffers_for_tests()
        verify = build_admin_operational_control_readonly()["admin_verification_layer"]
        self.assertTrue(verify.get("has_recoveries"))

    def test_audit_06_runtime_status_production_readiness(self) -> None:
        report = build_cartflow_production_readiness_report()
        self.assertIn("environment", report)
        self.assertIn("production_ready", report)
        self.assertIn("safety_gates", report)
        self.assertIn("operational", report)

    def test_audit_07_store_level_summary(self) -> None:
        summary = build_admin_operational_summary_readonly()
        self.assertIn("platform_admin_category", summary)
        self.assertIn("store_operational_rows", summary)
        self.assertIn("platform_admin_category", summary)

    def test_audit_08_historical_timeline(self) -> None:
        record_runtime_anomaly(ANOMALY_PROVIDER_SEND_FAILURE, detail="audit")
        timeline = build_admin_operational_control_readonly()["admin_operational_timeline"]
        self.assertIn("items", timeline)

    def test_audit_09_dev_recovery_verify_inspect(self) -> None:
        import main

        client = TestClient(main.app)
        r = client.get("/dev/recovery-restart-survival-verify?action=inspect")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body.get("persistence", {}).get("table"), "recovery_schedules")

    def test_audit_10_dev_operational_summary_json(self) -> None:
        import main

        prev = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            client = TestClient(main.app)
            r = client.get("/dev/admin-operational-summary")
            self.assertEqual(r.status_code, 200)
            self.assertIn("platform_admin_category", r.json())
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev


if __name__ == "__main__":
    unittest.main()
