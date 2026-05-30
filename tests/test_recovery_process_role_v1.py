# -*- coding: utf-8 -*-
"""Process role (api vs scheduler) for recovery scheduling ownership."""
from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from extensions import db
from services.recovery_delay_dispatcher import spawn_recovery_schedule_dispatch
from services.recovery_process_role_v1 import (
    build_scheduler_health_snapshot,
    log_scheduler_owner_at_startup,
    process_role_effective_due_scanner_enabled,
    process_role_effective_resume_enabled,
    process_role_may_spawn_delay_dispatch,
    resolve_process_role,
)
from services.recovery_restart_survival import run_recovery_resume_scan_async


class RecoveryProcessRoleTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        db.create_all()
        os.environ.pop("CARTFLOW_PROCESS_ROLE", None)
        os.environ.pop("CARTFLOW_RECOVERY_RESUME_ON_STARTUP", None)
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)

    def tearDown(self) -> None:
        os.environ.pop("CARTFLOW_PROCESS_ROLE", None)
        os.environ.pop("CARTFLOW_RECOVERY_RESUME_ON_STARTUP", None)
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)
        db.session.rollback()

    def test_unset_role_legacy_resume_default(self) -> None:
        self.assertEqual(resolve_process_role(), "unset")
        self.assertTrue(process_role_effective_resume_enabled())
        self.assertTrue(process_role_may_spawn_delay_dispatch())
        self.assertFalse(process_role_effective_due_scanner_enabled())

    def test_api_role_disables_resume_scanner_spawn(self) -> None:
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        self.assertFalse(process_role_effective_resume_enabled())
        self.assertFalse(process_role_effective_due_scanner_enabled())
        self.assertFalse(process_role_may_spawn_delay_dispatch())

    def test_scheduler_role_respects_env(self) -> None:
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        self.assertTrue(process_role_effective_resume_enabled())
        self.assertTrue(process_role_effective_due_scanner_enabled())
        self.assertTrue(process_role_may_spawn_delay_dispatch())

    def test_api_role_startup_resume_scan_disabled(self) -> None:
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        out = asyncio.run(run_recovery_resume_scan_async(max_dispatch=5, dry_run=True))
        self.assertFalse(out.get("enabled", True))

    def test_scheduler_role_startup_resume_scan_enabled(self) -> None:
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
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
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        with patch("asyncio.create_task") as mock_task:
            spawn_recovery_schedule_dispatch(99, 0.0, "test_api_role")
        mock_task.assert_not_called()

    def test_unset_role_spawn_dispatch_allowed(self) -> None:
        with patch("asyncio.create_task") as mock_task:
            spawn_recovery_schedule_dispatch(99, 0.0, "test_unset_role")
        mock_task.assert_called_once()

    def test_health_scheduler_snapshot_fields(self) -> None:
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        snap = build_scheduler_health_snapshot()
        for key in (
            "role",
            "resume_enabled",
            "due_scanner_enabled",
            "due_scanner_limit",
            "overdue_scheduled_count",
            "running_stale_count",
        ):
            self.assertIn(key, snap)

    def test_health_scheduler_overdue_count(self) -> None:
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
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        snap = log_scheduler_owner_at_startup()
        self.assertEqual(snap.get("role"), "api")
        self.assertFalse(snap.get("resume_enabled"))
        self.assertFalse(snap.get("due_scanner_enabled"))


class HealthSchedulerRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401
        from main import app
        from fastapi.testclient import TestClient

        db.create_all()
        self.client = TestClient(app)
        os.environ.pop("CARTFLOW_PROCESS_ROLE", None)

    def tearDown(self) -> None:
        os.environ.pop("CARTFLOW_PROCESS_ROLE", None)
        db.session.rollback()

    def test_get_health_scheduler_route(self) -> None:
        r = self.client.get("/health/scheduler")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("role", body)
        self.assertIn("overdue_scheduled_count", body)


if __name__ == "__main__":
    unittest.main()
