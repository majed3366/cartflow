# -*- coding: utf-8 -*-
"""DB session lifecycle hardening v1 — scheduler/resume background paths."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import main  # noqa: F401

from extensions import db
from models import RecoverySchedule
from services.recovery_db_due_scanner import scan_due_recovery_schedules
from services.recovery_restart_survival import (
    persist_recovery_schedule_durable,
    run_recovery_resume_scan_async,
)


def _persist_due_row(tag: str) -> RecoverySchedule:
    rk = f"demo:lifecycle-{tag}-{uuid.uuid4().hex[:6]}"
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


def test_scanner_releases_session_after_success() -> None:
    db.create_all()
    _persist_due_row("ok")
    with patch(
        "main._run_recovery_sequence_after_cart_abandoned",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with patch(
            "services.db_session_lifecycle.release_scoped_db_session"
        ) as mock_release:
            out = asyncio.run(scan_due_recovery_schedules(limit=5))
    assert out.get("found", 0) >= 1
    assert mock_release.call_count >= 1


def test_scanner_releases_session_after_exception() -> None:
    db.create_all()
    with patch(
        "services.recovery_db_due_scanner.db.create_all",
        side_effect=__import__("sqlalchemy.exc", fromlist=["SQLAlchemyError"]).SQLAlchemyError(
            "pool timeout"
        ),
    ):
        with patch(
            "services.db_session_lifecycle.release_scoped_db_session"
        ) as mock_release:
            out = asyncio.run(scan_due_recovery_schedules(limit=5))
    assert out.get("error")
    assert mock_release.call_count >= 1


def test_resume_scan_releases_session() -> None:
    db.create_all()
    with patch(
        "services.db_session_lifecycle.release_scoped_db_session"
    ) as mock_release:
        out = asyncio.run(run_recovery_resume_scan_async(max_dispatch=5))
    assert out.get("enabled") is not False or out.get("reason")
    assert mock_release.call_count >= 1


def test_scanner_still_dispatches_due_schedules() -> None:
    db.create_all()
    row = _persist_due_row("dispatch")
    sid = int(row.id)
    with patch(
        "main._run_recovery_sequence_after_cart_abandoned",
        new_callable=AsyncMock,
        return_value=None,
    ):
        out = asyncio.run(scan_due_recovery_schedules(limit=5, source="test_lifecycle"))
    db.session.expire_all()
    refreshed = db.session.get(RecoverySchedule, sid)
    assert out.get("dispatched", 0) >= 1
    assert refreshed is not None
    assert refreshed.status != "scheduled"
