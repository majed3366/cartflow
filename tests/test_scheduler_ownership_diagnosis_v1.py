# -*- coding: utf-8 -*-
"""Scheduler ownership diagnosis v1 — visibility tests."""
from __future__ import annotations

import os
import unittest

from extensions import db
from models import RecoverySchedule
from services.recovery_process_role_v1 import (
    COMPLIANCE_MISCONFIGURED,
    COMPLIANCE_OK,
    ENV_PROCESS_ROLE,
    build_scheduler_health_snapshot,
    evaluate_scheduler_ownership_policy,
)
from services.recovery_health_v1 import build_recovery_health_snapshot
from services.scheduler_ownership_diagnosis_v1 import (
    DIAG_EXECUTION_BACKLOG,
    DIAG_OWNERSHIP_OK,
    DIAG_SCHEDULER_OWNERSHIP_ABSENT,
    DIAG_SCHEDULER_ROLE_API_BLOCKED,
    DIAG_SCHEDULER_ROLE_MISCONFIGURED,
    DIAG_STALE_RUNNING_ROWS,
    DIAG_ZOMBIE_RUNNING_ROWS,
    SEVERITY_OK,
    build_ownership_diagnosis,
)
from services.scheduler_ownership_verify_v1 import evaluate_scheduler_health


def _clear_env() -> None:
    os.environ.pop(ENV_PROCESS_ROLE, None)
    os.environ.pop("CARTFLOW_RECOVERY_RESUME_ON_STARTUP", None)
    os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)
    os.environ.pop("ENV", None)


class SchedulerOwnershipDiagnosisTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        db.create_all()
        _clear_env()

    def tearDown(self) -> None:
        _clear_env()
        try:
            db.session.query(RecoverySchedule).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_scheduler_role_ownership_ok(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "scheduler"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        policy = evaluate_scheduler_ownership_policy()
        diag = build_ownership_diagnosis(
            scheduler_ownership={
                "role": policy["role"],
                "compliance": policy["compliance"],
                "block_reason": policy["block_reason"],
                "may_resume": policy["may_resume"],
                "production_like": policy["production_like"],
                "policy_error": policy["policy_error"],
            },
            overdue_scheduled_count=0,
            running_stale_count=0,
            resume_enabled=policy["may_resume"],
            due_scanner_enabled=policy["may_due_scan"],
            delay_dispatch_enabled=policy["may_delay_dispatch"],
        )
        self.assertIn(DIAG_OWNERSHIP_OK, diag["codes"])
        self.assertEqual(diag["severity"], SEVERITY_OK)

    def test_api_role_blocked_compliant(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "api"
        snap = build_scheduler_health_snapshot()
        diag = snap["ownership_diagnosis"]
        self.assertIn(DIAG_SCHEDULER_ROLE_API_BLOCKED, diag["codes"])
        self.assertEqual(snap["scheduler_ownership"]["compliance"], COMPLIANCE_OK)
        self.assertFalse(snap["scheduler_ownership"]["may_resume"])

    def test_unset_production_misconfigured(self) -> None:
        os.environ["ENV"] = "production"
        snap = build_scheduler_health_snapshot()
        diag = snap["ownership_diagnosis"]
        self.assertIn(DIAG_SCHEDULER_ROLE_MISCONFIGURED, diag["codes"])
        self.assertFalse(snap["ok"])
        self.assertEqual(snap["scheduler_ownership"]["compliance"], COMPLIANCE_MISCONFIGURED)

    def test_stale_running_diagnosis(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "scheduler"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        from datetime import datetime, timedelta, timezone

        old = datetime.now(timezone.utc) - timedelta(minutes=20)
        db.session.add(
            RecoverySchedule(
                recovery_key="demo:s-stale-diag",
                store_slug="demo",
                session_id="s-stale-diag",
                scheduled_at=old,
                due_at=old,
                effective_delay_seconds=60.0,
                delay_source="test",
                status="running",
                step=1,
                updated_at=old.replace(tzinfo=None),
            )
        )
        db.session.commit()
        snap = build_scheduler_health_snapshot()
        diag = snap["ownership_diagnosis"]
        self.assertGreater(snap["running_stale_count"], 0)
        self.assertIn(DIAG_ZOMBIE_RUNNING_ROWS, diag["codes"])
        self.assertIn(DIAG_STALE_RUNNING_ROWS, diag["codes"])

    def test_overdue_api_produces_ownership_absent(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "api"
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.add(
            RecoverySchedule(
                recovery_key="demo:s-overdue",
                store_slug="demo",
                session_id="s-overdue",
                scheduled_at=now,
                due_at=now,
                effective_delay_seconds=0.0,
                delay_source="test",
                status="scheduled",
                step=1,
            )
        )
        db.session.commit()
        snap = build_scheduler_health_snapshot()
        diag = snap["ownership_diagnosis"]
        self.assertIn(DIAG_SCHEDULER_OWNERSHIP_ABSENT, diag["codes"])

    def test_overdue_scheduler_produces_backlog(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "scheduler"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.add(
            RecoverySchedule(
                recovery_key="demo:s-backlog",
                store_slug="demo",
                session_id="s-backlog",
                scheduled_at=now,
                due_at=now,
                effective_delay_seconds=0.0,
                delay_source="test",
                status="scheduled",
                step=1,
            )
        )
        db.session.commit()
        snap = build_scheduler_health_snapshot()
        diag = snap["ownership_diagnosis"]
        self.assertIn(DIAG_EXECUTION_BACKLOG, diag["codes"])

    def test_recovery_health_includes_ownership_diagnosis(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_PROCESS_ROLE] = "scheduler"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        snap = build_recovery_health_snapshot(emit_warn_log=False)
        self.assertIn("ownership_diagnosis", snap)
        self.assertIn("scheduler_ownership", snap)
        self.assertIn("codes", snap["ownership_diagnosis"])


class SchedulerOwnershipVerifyScriptTests(unittest.TestCase):
    def test_verify_scheduler_fixture_passes(self) -> None:
        health = {
            "ok": True,
            "role": "scheduler",
            "resume_enabled": True,
            "due_scanner_enabled": True,
            "delay_dispatch_enabled": True,
            "scheduler_ownership": {
                "role": "scheduler",
                "compliance": COMPLIANCE_OK,
                "may_resume": True,
                "may_due_scan": True,
                "may_delay_dispatch": True,
            },
            "ownership_diagnosis": {
                "codes": [DIAG_OWNERSHIP_OK],
                "severity": SEVERITY_OK,
            },
        }
        verdict = evaluate_scheduler_health(health, expected_role="scheduler")
        self.assertTrue(verdict["passed"])

    def test_verify_api_fixture_passes(self) -> None:
        health = {
            "ok": True,
            "role": "api",
            "resume_enabled": False,
            "due_scanner_enabled": False,
            "delay_dispatch_enabled": False,
            "scheduler_ownership": {
                "role": "api",
                "compliance": COMPLIANCE_OK,
                "may_resume": False,
                "may_due_scan": False,
                "may_delay_dispatch": False,
            },
            "ownership_diagnosis": {
                "codes": [DIAG_SCHEDULER_ROLE_API_BLOCKED],
                "severity": SEVERITY_OK,
            },
        }
        verdict = evaluate_scheduler_health(health, expected_role="api")
        self.assertTrue(verdict["passed"])

    def test_verify_misconfigured_fails(self) -> None:
        health = {
            "ok": False,
            "role": "unset",
            "scheduler_ownership": {
                "role": "unset",
                "compliance": COMPLIANCE_MISCONFIGURED,
                "may_resume": False,
                "may_due_scan": False,
                "may_delay_dispatch": False,
            },
            "ownership_diagnosis": {
                "codes": [DIAG_SCHEDULER_ROLE_MISCONFIGURED],
                "severity": "critical",
            },
        }
        verdict = evaluate_scheduler_health(health, expected_role="scheduler")
        self.assertFalse(verdict["passed"])

    def test_verify_wrong_role_fails(self) -> None:
        health = {
            "ok": True,
            "role": "api",
            "scheduler_ownership": {
                "role": "api",
                "compliance": COMPLIANCE_OK,
                "may_resume": False,
                "may_due_scan": False,
                "may_delay_dispatch": False,
            },
            "ownership_diagnosis": {"codes": [DIAG_SCHEDULER_ROLE_API_BLOCKED]},
        }
        verdict = evaluate_scheduler_health(health, expected_role="scheduler")
        self.assertFalse(verdict["passed"])


if __name__ == "__main__":
    unittest.main()
