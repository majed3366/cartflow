# -*- coding: utf-8 -*-
"""
Queue / Worker Maturity v1 — audit matrix (read-only).

Maps the 10 reliability scenarios to automated proofs. See
``docs/audit_queue_worker_maturity_v1.md``.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from extensions import db
from models import CartRecoveryLog, RecoverySchedule
from services.recovery_execution_boundary import execute_recovery_schedule
from services.recovery_restart_survival import (
    STATUS_COMPLETED,
    STATUS_FAILED_RESUME_STALE,
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    STATUS_SKIPPED_DUPLICATE,
    claim_recovery_schedule_execution,
    persist_recovery_schedule_durable,
    reconcile_stale_running_schedules,
    repair_stale_running_recovery_schedules,
    rearm_one_future_scheduled_recovery,
    run_recovery_resume_scan_sync,
)
from services.recovery_whatsapp_idempotency import check_whatsapp_recovery_send_idempotency


def _persist(rk: str, *, delay: float = 60.0) -> RecoverySchedule:
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=rk.split(":", 1)[-1][:32],
        cart_id="cart-audit",
        reason_tag="other",
        abandon_event_phone="+966501112233",
        delay_seconds_scheduled=delay,
        schedule_timing={
            "effective_delay_seconds": delay,
            "source": "reason_templates.messages",
        },
        recovery_context={"recovery_key": rk, "store_slug": "demo"},
    )
    assert row is not None
    return row


@pytest.fixture(autouse=True)
def _clean_schedules() -> None:
    import main  # noqa: F401 — init_database for db.create_all()

    db.create_all()
    for row in db.session.query(RecoverySchedule).all():
        db.session.delete(row)
    for row in db.session.query(CartRecoveryLog).all():
        db.session.delete(row)
    db.session.commit()
    yield
    db.session.rollback()


def test_audit_01_restart_before_due_at_future_rearm() -> None:
    rk = f"demo:s-audit-1-{uuid.uuid4().hex[:6]}"
    row = _persist(rk, delay=120.0)
    row.due_at = datetime.now(timezone.utc) + timedelta(seconds=90)
    db.session.commit()
    with patch(
        "services.recovery_delay_dispatcher.spawn_recovery_schedule_dispatch"
    ) as mock_spawn:
        with patch(
            "services.recovery_restart_survival.resume_one_schedule",
            new_callable=AsyncMock,
        ) as mock_resume:
            scan = run_recovery_resume_scan_sync(max_dispatch=10, dry_run=False, force=True)
    assert scan.get("future_rearmed", 0) >= 1
    mock_resume.assert_not_called()
    mock_spawn.assert_called()
    db.session.refresh(row)
    assert row.status == STATUS_SCHEDULED


def test_audit_02_restart_after_due_at_discoverable() -> None:
    rk = f"demo:s-audit-2-{uuid.uuid4().hex[:6]}"
    row = _persist(rk)
    row.due_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.session.commit()
    scan = run_recovery_resume_scan_sync(max_dispatch=10, dry_run=True, force=True)
    keys = [o.get("recovery_key") for o in scan.get("outcomes", [])]
    assert rk in keys


def test_audit_03_duplicate_dispatch_single_task() -> None:
    import services.recovery_restart_survival as rrs

    rk = f"demo:s-audit-3-{uuid.uuid4().hex[:6]}"
    row = _persist(rk, delay=1.0)
    row.due_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    calls: list[str] = []

    def _fake_create_task(coro):  # noqa: ANN001
        calls.append("task")
        coro.close()
        return None

    with patch("asyncio.create_task", side_effect=_fake_create_task):
        asyncio.run(rrs.resume_one_schedule(row, dispatch=True))
        asyncio.run(rrs.resume_one_schedule(row, dispatch=True))
    assert len(calls) == 1


def test_audit_04_already_running_blocks_second_execute() -> None:
    rk = f"demo:s-audit-4-{uuid.uuid4().hex[:6]}"
    row = _persist(rk)
    ok, _, _ = claim_recovery_schedule_execution(
        recovery_key=rk, row_id=int(row.id), path="audit"
    )
    assert ok
    with patch(
        "main._run_recovery_sequence_after_cart_abandoned",
        new_callable=AsyncMock,
    ) as mock_run:
        out = asyncio.run(
            execute_recovery_schedule(schedule_id=int(row.id), source="audit")
        )
    assert out["ok"] is False
    assert out["reason"] == "already_running"
    mock_run.assert_not_called()


def test_audit_05_stale_running_reconciled() -> None:
    rk = f"demo:s-audit-5-{uuid.uuid4().hex[:6]}"
    row = _persist(rk)
    row.status = STATUS_RUNNING
    row.updated_at = datetime.now(timezone.utc) - timedelta(seconds=900)
    db.session.commit()
    n = reconcile_stale_running_schedules(max_age_seconds=600)
    assert n >= 1
    db.session.refresh(row)
    assert row.status == STATUS_FAILED_RESUME_STALE


def test_audit_06_resume_scan_finds_due_row() -> None:
    """RecoverySchedule resume path discovers past-due scheduled rows."""
    rk = f"demo:s-audit-6-{uuid.uuid4().hex[:6]}"
    row = _persist(rk)
    row.due_at = datetime.now(timezone.utc) - timedelta(seconds=2)
    db.session.commit()
    scan = run_recovery_resume_scan_sync(max_dispatch=5, dry_run=True, force=True)
    assert scan.get("due_processed", 0) >= 1


def test_audit_07_db_claim_atomic_second_fails() -> None:
    """Multi-worker safety at DB layer: only one scheduled→running claim."""
    rk = f"demo:s-audit-7-{uuid.uuid4().hex[:6]}"
    row = _persist(rk)
    ok1, reason1, _ = claim_recovery_schedule_execution(
        recovery_key=rk, row_id=int(row.id), path="w1"
    )
    ok2, reason2, _ = claim_recovery_schedule_execution(
        recovery_key=rk, row_id=int(row.id), path="w2"
    )
    assert ok1 is True
    assert ok2 is False
    assert reason2 == "already_running"


def test_audit_08_wa_idempotency_hit() -> None:
    rk = f"demo:s-audit-8-{uuid.uuid4().hex[:6]}"
    sid = rk.split(":", 1)[1]
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id="cart-8",
            phone="+966501112233",
            message="hi",
            status="mock_sent",
            step=1,
            sent_at=datetime.now(timezone.utc),
        )
    )
    db.session.commit()
    dup, st, _ = check_whatsapp_recovery_send_idempotency(
        recovery_key=rk,
        step=1,
        reason_tag="other",
        customer_phone="+966501112233",
        store_slug="demo",
        session_id=sid,
        cart_id="cart-8",
    )
    assert dup is True
    assert st == "mock_sent"


def test_audit_09_dead_schedule_past_due_in_scan() -> None:
    """Orphan scheduled row with past due_at is a resume candidate."""
    rk = f"demo:s-audit-9-{uuid.uuid4().hex[:6]}"
    row = _persist(rk)
    row.due_at = datetime.now(timezone.utc) - timedelta(hours=2)
    row.status = STATUS_SCHEDULED
    db.session.commit()
    scan = run_recovery_resume_scan_sync(max_dispatch=10, dry_run=True, force=True)
    assert scan.get("due_processed", 0) >= 1
    assert any(o.get("recovery_key") == rk for o in scan.get("outcomes", []))


def test_audit_10_terminal_not_re_executed() -> None:
    rk = f"demo:s-audit-10-{uuid.uuid4().hex[:6]}"
    row = _persist(rk)
    row.status = STATUS_COMPLETED
    db.session.commit()
    with patch(
        "main._run_recovery_sequence_after_cart_abandoned",
        new_callable=AsyncMock,
    ) as mock_run:
        out = asyncio.run(
            execute_recovery_schedule(schedule_id=int(row.id), source="audit")
        )
    assert out["ok"] is False
    assert "already_terminal" in out["reason"]
    mock_run.assert_not_called()


def test_audit_05b_stale_with_duplicate_log_terminal() -> None:
    rk = f"demo:s-audit-5b-{uuid.uuid4().hex[:6]}"
    sid = rk.split(":", 1)[1]
    row = _persist(rk)
    row.status = STATUS_RUNNING
    row.updated_at = datetime.now(timezone.utc) - timedelta(seconds=900)
    db.session.add(
        CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id="cart-dup",
            phone="+966501112233",
            message="dup",
            status="skipped_duplicate",
            step=1,
        )
    )
    db.session.commit()
    repair_stale_running_recovery_schedules(max_age_seconds=600)
    db.session.refresh(row)
    assert row.status == STATUS_SKIPPED_DUPLICATE
