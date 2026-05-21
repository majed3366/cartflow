# -*- coding: utf-8 -*-
"""Tests for manual DB due recovery scanner."""
from __future__ import annotations

import asyncio
import io
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import main  # noqa: F401

from extensions import db
from models import RecoverySchedule
from services.recovery_db_due_scanner import scan_due_recovery_schedules
from services.recovery_restart_survival import (
    STATUS_SCHEDULED,
    _TERMINAL,
    persist_recovery_schedule_durable,
)


def _persist_due_row(tag: str) -> RecoverySchedule:
    rk = f"demo:scanner-{tag}-{uuid.uuid4().hex[:6]}"
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=f"sess-{tag}",
        cart_id=f"cart-{tag}",
        reason_tag="other",
        abandon_event_phone="+966501112233",
        delay_seconds_scheduled=0.0,
        schedule_timing={
            "effective_delay_seconds": 0.0,
            "source": "reason_templates.messages",
        },
        recovery_context={"recovery_key": rk, "store_slug": "demo"},
    )
    assert row is not None
    row.due_at = datetime.now(timezone.utc) - timedelta(seconds=2)
    db.session.commit()
    return row


def test_scan_due_dispatches_once_then_idempotent():
    db.create_all()
    row = _persist_due_row("t1")
    sid = int(row.id)
    buf = io.StringIO()

    with redirect_stdout(buf):
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ):
            out1 = asyncio.run(
                scan_due_recovery_schedules(limit=10, source="db_due_scanner")
            )

    db.session.expire_all()
    row1 = db.session.get(RecoverySchedule, sid)
    logs1 = buf.getvalue()
    assert "[DB DUE SCANNER START]" in logs1
    assert "[DB DUE SCANNER FOUND]" in logs1
    assert "[DB DUE SCANNER DISPATCH]" in logs1
    assert "[DB DUE SCANNER DONE]" in logs1
    assert out1.get("dispatched", 0) >= 1
    assert row1 is not None
    assert row1.status in _TERMINAL

    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ):
            out2 = asyncio.run(
                scan_due_recovery_schedules(limit=10, source="db_due_scanner")
            )

    db.session.expire_all()
    row2 = db.session.get(RecoverySchedule, sid)
    assert out2.get("dispatched", 0) == 0
    assert row2 is not None
    assert row2.status == row1.status
    assert row2.status in _TERMINAL


def test_scan_skips_non_due_scheduled():
    db.create_all()
    row = _persist_due_row("future")
    row.due_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()

    out = asyncio.run(scan_due_recovery_schedules(limit=10))
    db.session.expire_all()
    row_f = db.session.get(RecoverySchedule, int(row.id))
    assert out.get("found", 0) == 0
    assert row_f is not None
    assert row_f.status == STATUS_SCHEDULED
