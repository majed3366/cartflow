# -*- coding: utf-8 -*-
"""Process role (api vs scheduler) for recovery scheduling ownership."""
from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from extensions import db
from services.recovery_db_due_scanner_loop import start_db_due_recovery_scanner_loop
from services.recovery_delay_dispatcher import spawn_recovery_schedule_dispatch
from services.recovery_process_role_v1 import (
    COMPLIANCE_MISCONFIGURED,
    COMPLIANCE_OK,
    ENV_PROCESS_ROLE,
    build_scheduler_health_snapshot,
    evaluate_scheduler_ownership_policy,
    log_scheduler_owner_at_startup,
    process_role_effective_due_scanner_enabled,
    process_role_effective_resume_enabled,
    process_role_may_spawn_delay_dispatch,
    resolve_process_role,
)
from services.recovery_restart_survival import run_recovery_resume_scan_async


def _clear_role_env() -> None:
    os.environ.pop(ENV_PROCESS_ROLE, None)
    os.environ.pop("CARTFLOW_RECOVERY_RESUME_ON_STARTUP", None)
    os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)
    os.environ.pop("ENV", None)


class RecoveryProcessRoleTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        db.create_all()
        _clear_role_env()

    def tearDown(self) -> None:
        _clear_role_env()
        db.session.rollback()

    def test_development_unset_role_legacy_resume_default(self) -> None:
        os.environ["ENV"] = "development"
        self.assertEqual(resolve_process_role(), "unset")
        self.assertTrue(process_role_effective_resume_enabled())
        self.assertTrue(process_role_may_spawn_delay_dispatch())
        self.assertFalse(process_role_effective_due_scanner_enabled())

    def test_production_scheduler_all_drivers_allowed(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "scheduler"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        policy = evaluate_scheduler_ownership_policy()
        self.assertEqual(policy["role"], "scheduler")
        self.assertTrue(policy["may_resume"])
        self.assertTrue(policy["may_due_scan"])
        self.assertTrue(policy["may_delay_dispatch"])
        self.assertEqual(policy["compliance"], COMPLIANCE_OK)

    def test_production_api_all_drivers_blocked(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "api"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        policy = evaluate_scheduler_ownership_policy()
        self.assertFalse(policy["may_resume"])
        self.assertFalse(policy["may_due_scan"])
        self.assertFalse(policy["may_delay_dispatch"])
        self.assertEqual(policy["compliance"], COMPLIANCE_OK)
        self.assertEqual(policy["block_reason"], "role_api")

    def test_production_unset_role_misconfigured(self) -> None:
        os.environ["ENV"] = "production"
        policy = evaluate_scheduler_ownership_policy()
        self.assertEqual(policy["role"], "unset")
        self.assertFalse(policy["may_resume"])
        self.assertFalse(policy["may_due_scan"])
        self.assertFalse(policy["may_delay_dispatch"])
        self.assertEqual(policy["compliance"], COMPLIANCE_MISCONFIGURED)
        self.assertEqual(policy["block_reason"], "role_unset_production")

    def test_production_unknown_role_misconfigured(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "worker"
        policy = evaluate_scheduler_ownership_policy()
        self.assertEqual(policy["role"], "unknown")
        self.assertFalse(policy["may_resume"])
        self.assertEqual(policy["compliance"], COMPLIANCE_MISCONFIGURED)
        self.assertEqual(policy["block_reason"], "role_unknown_production")

    def test_api_role_with_resume_env_still_blocked(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "api"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        self.assertFalse(process_role_effective_resume_enabled())

    def test_api_role_startup_resume_scan_disabled(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "api"
        out = asyncio.run(run_recovery_resume_scan_async(max_dispatch=5, dry_run=True))
        self.assertFalse(out.get("enabled", True))
        self.assertEqual(out.get("reason"), "role_api")

    def test_production_unset_resume_scan_blocked(self) -> None:
        os.environ["ENV"] = "production"
        out = asyncio.run(run_recovery_resume_scan_async(max_dispatch=5, dry_run=True))
        self.assertFalse(out.get("enabled", True))
        self.assertEqual(out.get("reason"), "role_unset_production")

    def test_scheduler_role_startup_resume_scan_enabled(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "scheduler"
        with patch(
            "services.recovery_restart_survival.repair_stale_running_recovery_schedules",
            return_value={},
        ):
            with patch(
                "services.recovery_restart_survival.ignore_sandbox_schedules_for_production_startup",
                return_value={},
            ):
                out = asyncio.run(
                    run_recovery_resume_scan_async(max_dispatch=5, dry_run=True, force=True)
                )
        self.assertTrue(out.get("enabled"))

    def test_api_role_spawn_dispatch_noop(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "api"
        with patch("asyncio.create_task") as mock_task:
            spawn_recovery_schedule_dispatch(99, 0.0, "test_api_role")
        mock_task.assert_not_called()

    def test_development_unset_role_spawn_dispatch_allowed(self) -> None:
        os.environ["ENV"] = "development"
        with patch("asyncio.create_task") as mock_task:
            spawn_recovery_schedule_dispatch(99, 0.0, "test_unset_role")
        mock_task.assert_called_once()

    def test_api_role_db_scanner_does_not_start(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "api"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        with patch("services.recovery_db_due_scanner_loop._log_loop") as mock_log:
            start_db_due_recovery_scanner_loop()
        mock_log.assert_called_once()
        self.assertEqual(mock_log.call_args[0][0], "SKIPPED")

    def test_health_scheduler_ownership_fields(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "scheduler"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        snap = build_scheduler_health_snapshot()
        self.assertIn("scheduler_ownership", snap)
        self.assertIn("ownership_diagnosis", snap)
        own = snap["scheduler_ownership"]
        diag = snap["ownership_diagnosis"]
        for key in (
            "role",
            "compliance",
            "block_reason",
            "may_resume",
            "may_due_scan",
            "may_delay_dispatch",
            "production_like",
            "fail_closed",
        ):
            self.assertIn(key, own)
        for key in ("codes", "severity", "summary"):
            self.assertIn(key, diag)
        self.assertTrue(snap["ok"])

    def test_health_scheduler_misconfigured_ok_false(self) -> None:
        os.environ["ENV"] = "production"
        snap = build_scheduler_health_snapshot()
        self.assertFalse(snap["ok"])
        self.assertEqual(snap["scheduler_ownership"]["compliance"], COMPLIANCE_MISCONFIGURED)
        self.assertEqual(
            snap["scheduler_ownership"]["block_reason"],
            "role_unset_production",
        )

    def test_health_scheduler_overdue_count(self) -> None:
        os.environ["ENV"] = "development"
        from services.recovery_restart_survival import persist_recovery_schedule_durable

        persist_recovery_schedule_durable(
            recovery_key="demo:s-health",
            store_slug="demo",
            session_id="s-health",
            cart_id="c1",
            reason_tag="other",
            abandon_event_phone="+966501112233",
            delay_seconds_scheduled=0.0,
            schedule_timing={"effective_delay_seconds": 0.0, "source": "test"},
            recovery_context={"recovery_key": "demo:s-health"},
        )
        snap = build_scheduler_health_snapshot()
        self.assertGreaterEqual(int(snap.get("overdue_scheduled_count") or 0), 1)

    def test_log_scheduler_owner_startup_shape(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "api"
        snap = log_scheduler_owner_at_startup()
        self.assertEqual(snap.get("role"), "api")
        self.assertFalse(snap.get("resume_enabled"))
        self.assertFalse(snap.get("due_scanner_enabled"))
        self.assertEqual(snap.get("compliance"), COMPLIANCE_OK)

    def test_policy_error_fail_closed(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "scheduler"
        with patch(
            "services.recovery_scheduler_guardrails.resolve_recovery_resume_on_startup_config",
            side_effect=RuntimeError("policy boom"),
        ):
            policy = evaluate_scheduler_ownership_policy()
        self.assertFalse(policy["may_resume"])
        self.assertFalse(policy["may_due_scan"])
        self.assertFalse(policy["may_delay_dispatch"])
        self.assertEqual(policy["compliance"], COMPLIANCE_MISCONFIGURED)
        self.assertEqual(policy["block_reason"], "policy_error")


class HealthSchedulerRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401
        from main import app
        from fastapi.testclient import TestClient

        db.create_all()
        self.client = TestClient(app)
        _clear_role_env()

    def tearDown(self) -> None:
        _clear_role_env()
        db.session.rollback()

    def test_get_health_scheduler_route(self) -> None:
        os.environ["ENV"] = "development"
        r = self.client.get("/health/scheduler")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("role", body)
        self.assertIn("scheduler_ownership", body)
        self.assertIn("ownership_diagnosis", body)
        self.assertIn("overdue_scheduled_count", body)

    def test_get_health_scheduler_misconfigured_503(self) -> None:
        os.environ["ENV"] = "production"
        r = self.client.get("/health/scheduler")
        self.assertEqual(r.status_code, 503)
        body = r.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["scheduler_ownership"]["compliance"], COMPLIANCE_MISCONFIGURED)


if __name__ == "__main__":
    unittest.main()
