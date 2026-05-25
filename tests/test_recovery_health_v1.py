# -*- coding: utf-8 -*-
"""Recovery health visibility v1 — read-only snapshot and /dev/recovery-health."""
from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import CartRecoveryLog, RecoverySchedule
from services.recovery_failure_explanation_v1 import explain_failure_status
from services.recovery_health_v1 import (
    build_recovery_health_snapshot,
    clear_recovery_health_v1_for_tests,
    record_resume_scan_completed,
)
from services.recovery_restart_survival import (
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    STATUS_WHATSAPP_FAILED,
)
from services.recovery_scheduler_guardrails import ENV_RECOVERY_RESUME_ON_STARTUP


@pytest.fixture(autouse=True)
def _reset_health() -> None:
    clear_recovery_health_v1_for_tests()
    try:
        db.session.query(CartRecoveryLog).delete()
        db.session.query(RecoverySchedule).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
    yield
    clear_recovery_health_v1_for_tests()
    try:
        db.session.query(CartRecoveryLog).delete()
        db.session.query(RecoverySchedule).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_healthy_snapshot_empty_db() -> None:
    db.create_all()
    snap = build_recovery_health_snapshot(emit_warn_log=False)
    assert snap["ok"] is True
    assert snap["health"] == "healthy"
    assert snap["stuck_running"]["stuck_running_detected"] is False
    assert snap["pending_due"] == 0
    assert "protections" in snap
    assert snap["protections"]["scheduler_owner"]["resume_on_startup"] is True


def test_stuck_running_detected() -> None:
    db.create_all()
    old = datetime.now(timezone.utc) - timedelta(minutes=15)
    db.session.add(
        RecoverySchedule(
            recovery_key="demo:s-stuck",
            store_slug="demo",
            session_id="s-stuck",
            scheduled_at=old,
            due_at=old,
            effective_delay_seconds=60.0,
            delay_source="test",
            status=STATUS_RUNNING,
            step=1,
            updated_at=old.replace(tzinfo=None),
        )
    )
    db.session.commit()

    buf = io.StringIO()
    with redirect_stdout(buf):
        snap = build_recovery_health_snapshot(emit_warn_log=True)
    assert snap["stuck_running"]["stuck_running_detected"] is True
    assert snap["stuck_running"]["count"] >= 1
    assert snap["health"] == "warning"
    assert len(snap["stuck_running"]["examples"]) >= 1
    assert "stuck_running_detected=true" in buf.getvalue()


def test_scheduler_owner_visible_from_env() -> None:
    db.create_all()
    os.environ[ENV_RECOVERY_RESUME_ON_STARTUP] = "0"
    try:
        snap = build_recovery_health_snapshot(emit_warn_log=False)
        assert snap["scheduler_owner_mode"] == "api_replica"
        assert snap["resume_on_startup_enabled"] is False
        assert snap["protections"]["scheduler_owner"]["status"] == "disabled"
    finally:
        os.environ.pop(ENV_RECOVERY_RESUME_ON_STARTUP, None)


def test_last_resume_heartbeat_recorded() -> None:
    record_resume_scan_completed(
        {
            "enabled": True,
            "dispatched": 2,
            "due_processed": 3,
            "future_rearmed": 1,
        }
    )
    snap = build_recovery_health_snapshot(emit_warn_log=False)
    assert snap["last_resume"]["dispatched"] == 2
    assert snap["scheduler_detail"]["resume_heartbeat"] == "healthy"


def test_whatsapp_failed_explained_in_health() -> None:
    db.create_all()
    now = datetime.now(timezone.utc)
    db.session.add(
        RecoverySchedule(
            recovery_key="demo:s-wa-fail",
            store_slug="demo",
            session_id="s-wa-fail",
            scheduled_at=now,
            due_at=now,
            effective_delay_seconds=60.0,
            delay_source="test",
            status=STATUS_WHATSAPP_FAILED,
            step=1,
            last_error="Twilio error 63016",
            updated_at=now.replace(tzinfo=None),
        )
    )
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id="s-wa-fail",
            status="whatsapp_failed",
            message="provider restriction",
            step=1,
        )
    )
    db.session.commit()

    snap = build_recovery_health_snapshot(emit_warn_log=False)
    assert snap["failed"] >= 1
    latest = snap["recent_failures"]["latest"]
    assert latest is not None
    assert latest["status"] == "whatsapp_failed"
    assert latest["reason"] == "provider_restriction_or_unavailable"
    assert "provider" in latest["explanation"].lower()
    assert latest["action_needed"] == "yes"
    assert snap["failed_detail"]["latest"]["status"] == "whatsapp_failed"
    meta = explain_failure_status("whatsapp_failed")
    assert "provider" in meta["explanation"].lower()


def test_dev_recovery_health_endpoint(client: TestClient) -> None:
    db.create_all()
    r = client.get("/dev/recovery-health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("health") in ("healthy", "warning", "stale")
    assert "scheduler" in body
    assert "stuck_running" in body
    assert "pending_due" in body
    assert "running" in body
    assert "last_resume" in body
    assert "recent_failures" in body
    assert "failed_detail" in body
