# -*- coding: utf-8 -*-
"""
Verify manual DB due scanner for recovery schedules.

Run: python scripts/db_due_scanner_verify.py

Creates a due test row (or reuses an existing due scheduled row), runs the scanner
twice, and prints PASS/FAIL with before/after DB snapshots.
"""
from __future__ import annotations

import asyncio
import io
import os
import sys
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import main  # noqa: E402, F401

from extensions import db  # noqa: E402
from models import RecoverySchedule  # noqa: E402
from services.recovery_db_due_scanner import scan_due_recovery_schedules  # noqa: E402
from services.recovery_restart_survival import (  # noqa: E402
    STATUS_SCHEDULED,
    persist_recovery_schedule_durable,
)
from services.recovery_restart_survival import _TERMINAL  # noqa: E402


def _row_snapshot(row: Optional[RecoverySchedule]) -> Dict[str, Any]:
    if row is None:
        return {}
    return {
        "id": int(row.id),
        "recovery_key": row.recovery_key,
        "status": row.status,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _find_logs(buf: str, tags: List[str]) -> Dict[str, bool]:
    return {t: (f"[{t}]" in buf or t in buf) for t in tags}


def _utc_now_cmp() -> datetime:
    return datetime.now(timezone.utc)


def _is_due(due_at: Optional[datetime]) -> bool:
    if due_at is None:
        return False
    now = _utc_now_cmp()
    if due_at.tzinfo is None:
        return due_at <= now.replace(tzinfo=None)
    return due_at <= now


def _locate_or_create_due_row() -> RecoverySchedule:
    now = _utc_now_cmp()
    existing = (
        db.session.query(RecoverySchedule)
        .filter(
            RecoverySchedule.status == STATUS_SCHEDULED,
            RecoverySchedule.due_at <= now,
        )
        .order_by(RecoverySchedule.due_at.asc())
        .first()
    )
    if existing is not None:
        print(f"[VERIFY] Reusing existing due row id={existing.id}", flush=True)
        return existing

    rk = f"demo:db-scanner-{uuid.uuid4().hex[:8]}"
    row = persist_recovery_schedule_durable(
        recovery_key=rk,
        store_slug="demo",
        session_id=f"sess-{uuid.uuid4().hex[:6]}",
        cart_id=f"cart-{uuid.uuid4().hex[:6]}",
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
    row.due_at = now - timedelta(seconds=5)
    db.session.commit()
    print(f"[VERIFY] Created due test row id={row.id}", flush=True)
    return row


def _run_scanner_once() -> tuple[Dict[str, Any], str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ):
            out = asyncio.run(
                scan_due_recovery_schedules(limit=25, source="db_due_scanner")
            )
    return out, buf.getvalue()


def main() -> int:
    db.create_all()
    row = _locate_or_create_due_row()
    schedule_id = int(row.id)

    db.session.expire_all()
    before = db.session.get(RecoverySchedule, schedule_id)
    before_snap = _row_snapshot(before)
    print("[VERIFY] BEFORE (run 1):", before_snap, flush=True)

    if before is None or before.status != STATUS_SCHEDULED:
        print("FAIL: expected scheduled row before first scan", flush=True)
        return 1
    if not _is_due(before.due_at):
        print("FAIL: expected due_at in the past before first scan", flush=True)
        return 1

    out1, logs1 = _run_scanner_once()
    db.session.expire_all()
    after1 = db.session.get(RecoverySchedule, schedule_id)
    after1_snap = _row_snapshot(after1)
    print("[VERIFY] SCAN 1 OUT:", out1, flush=True)
    print("[VERIFY] AFTER (run 1):", after1_snap, flush=True)

    run1_log_tags = [
        "DB DUE SCANNER START",
        "DB DUE SCANNER FOUND",
        "DB DUE SCANNER DISPATCH",
        "RECOVERY EXECUTION ENTRY",
        "RECOVERY CLAIM ATTEMPT",
        "RECOVERY CLAIMED",
        "RECOVERY TERMINAL UPDATE",
        "DB DUE SCANNER DONE",
    ]
    found1 = _find_logs(logs1, run1_log_tags)

    run1_ok = (
        out1.get("found", 0) >= 1
        and out1.get("dispatched", 0) >= 1
        and after1 is not None
        and after1.status in _TERMINAL
        and all(found1.get(t) for t in run1_log_tags)
    )

    out2, logs2 = _run_scanner_once()
    db.session.expire_all()
    after2 = db.session.get(RecoverySchedule, schedule_id)
    after2_snap = _row_snapshot(after2)
    print("[VERIFY] SCAN 2 OUT:", out2, flush=True)
    print("[VERIFY] AFTER (run 2):", after2_snap, flush=True)

    status_unchanged = after1 is not None and after2 is not None and after2.status == after1.status
    no_redispatch = (
        out2.get("dispatched", 0) == 0
        and (out2.get("found", 0) == 0 or status_unchanged)
    )
    run2_ok = no_redispatch and after2 is not None and after2.status in _TERMINAL

    print("[VERIFY] RUN1 logs:", found1, flush=True)
    print("[VERIFY] RUN2 no duplicate dispatch:", no_redispatch, flush=True)

    if run1_ok and run2_ok:
        print("PASS", flush=True)
        return 0
    print("FAIL", flush=True)
    if not run1_ok:
        print("  - first scan did not meet expectations", flush=True)
    if not run2_ok:
        print("  - second scan was not idempotent-safe", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
