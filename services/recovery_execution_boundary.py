# -*- coding: utf-8 -*-
"""
Queue-ready recovery execution boundary — single entry for durable schedule execution.

Future workers call ``execute_recovery_schedule`` with only DB identifiers (no in-memory state).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule
from services.recovery_restart_survival import (
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    _TERMINAL,
    _is_running_schedule_stale,
    _running_stale_seconds,
    _schedule_row_lookup,
    _utc_now,
    claim_recovery_schedule_execution,
    classify_stale_running_schedule_repair,
    finalize_recovery_schedule_durable,
    load_context,
    release_claimed_schedule_execution_terminal,
)

_log = logging.getLogger("cartflow")


def _log_execution(
    tag: str,
    *,
    recovery_key: str,
    schedule_id: Optional[int],
    source: str,
    detail: str = "",
    terminal_status: str = "",
) -> None:
    try:
        print(f"[RECOVERY EXECUTION {tag}]", flush=True)
        print(f"recovery_key={(recovery_key or '-')[:120]}", flush=True)
        if schedule_id is not None:
            print(f"schedule_id={schedule_id}", flush=True)
        print(f"source={(source or '-')[:64]}", flush=True)
        if detail:
            print(f"detail={detail[:96]}", flush=True)
        if terminal_status:
            print(f"terminal_status={terminal_status[:64]}", flush=True)
    except OSError:
        pass


def resolve_recovery_schedule_row(
    *,
    schedule_id: Optional[int] = None,
    recovery_key: Optional[str] = None,
    multi_slot_index: Optional[int] = None,
    sequential_attempt_index: Optional[int] = None,
) -> Optional[RecoverySchedule]:
    """Load durable row by primary key or natural key (recovery_key + step + slot)."""
    try:
        db.create_all()
        return _schedule_row_lookup(
            recovery_key=recovery_key or "",
            multi_slot_index=multi_slot_index,
            sequential_attempt_index=sequential_attempt_index,
            row_id=schedule_id,
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def _build_recovery_context_from_schedule_row(
    row: RecoverySchedule,
    *,
    source: str,
) -> Dict[str, Any]:
    ctx = load_context(row)
    rc = dict(ctx.get("recovery_context") or {})
    rc["recovery_key"] = row.recovery_key
    rc["store_slug"] = row.store_slug
    rc["recovery_post_delay_only"] = True
    rc["execution_boundary_source"] = (source or "unknown")[:64]
    rc["durable_schedule_row_id"] = int(row.id)
    rc["schedule_execution_claimed"] = True
    if ctx.get("schedule_timing") is not None:
        rc["schedule_timing"] = ctx.get("schedule_timing")
    if source == "resume_scan":
        rc["resume_from_durable_schedule"] = True
    return rc


def _repair_stale_running_at_entry(row: RecoverySchedule) -> Optional[str]:
    """If row is stale ``running`` with log evidence, finalize in place. Returns skip reason."""
    age = _running_stale_seconds()
    cutoff = _utc_now() - timedelta(seconds=age)
    if row.status != STATUS_RUNNING or not _is_running_schedule_stale(row, cutoff):
        return None
    _action, terminal_status, detail = classify_stale_running_schedule_repair(
        row, stale_threshold_seconds=age
    )
    msi = row.multi_slot_index if row.multi_slot_index >= 0 else None
    finalize_recovery_schedule_durable(
        row.recovery_key,
        status=terminal_status,
        multi_slot_index=msi,
        sequential_attempt_index=row.sequential_attempt_index,
        detail=detail,
    )
    return f"stale_running_repaired:{terminal_status}"


async def execute_recovery_schedule(
    *,
    schedule_id: Optional[int] = None,
    recovery_key: Optional[str] = None,
    multi_slot_index: Optional[int] = None,
    sequential_attempt_index: Optional[int] = None,
    source: str = "unknown",
) -> Dict[str, Any]:
    """
    Single queue-ready execution entry: claim → run recovery (delay already elapsed) → finalize.

    Safe to call twice: second call hits terminal / already_running / claim_race_lost.
    """
    from services.db_session_lifecycle import release_scoped_db_session, scoped_db_session_begin

    scoped_db_session_begin()
    src = (source or "unknown").strip()[:64]
    out: Dict[str, Any] = {
        "ok": False,
        "source": src,
        "schedule_id": schedule_id,
        "recovery_key": recovery_key,
        "reason": "",
    }
    exc_detail = ""
    row: Optional[RecoverySchedule] = None
    recovery_context: Dict[str, Any] = {}

    try:
        row = resolve_recovery_schedule_row(
            schedule_id=schedule_id,
            recovery_key=recovery_key,
            multi_slot_index=multi_slot_index,
            sequential_attempt_index=sequential_attempt_index,
        )
        if row is None:
            out["reason"] = "schedule_row_missing"
            _log_execution(
                "SKIPPED",
                recovery_key=recovery_key or "",
                schedule_id=schedule_id,
                source=src,
                detail=out["reason"],
            )
            return out

        rk = row.recovery_key
        out["schedule_id"] = int(row.id)
        out["recovery_key"] = rk
        _log_execution(
            "ENTRY",
            recovery_key=rk,
            schedule_id=int(row.id),
            source=src,
        )

        if row.status in _TERMINAL:
            out["reason"] = f"already_terminal:{row.status}"
            _log_execution(
                "SKIPPED",
                recovery_key=rk,
                schedule_id=int(row.id),
                source=src,
                detail=out["reason"],
                terminal_status=str(row.status),
            )
            return out

        stale_skip = _repair_stale_running_at_entry(row)
        if stale_skip:
            out["reason"] = stale_skip
            _log_execution(
                "SKIPPED",
                recovery_key=rk,
                schedule_id=int(row.id),
                source=src,
                detail=stale_skip,
            )
            return out

        accept_running = row.status == STATUS_RUNNING and src == "resume_scan"
        claimed, claim_reason, claimed_row = claim_recovery_schedule_execution(
            recovery_key=rk,
            multi_slot_index=row.multi_slot_index if row.multi_slot_index >= 0 else None,
            sequential_attempt_index=row.sequential_attempt_index,
            row_id=int(row.id),
            path=f"execution_boundary_{src}",
            accept_already_running=accept_running,
        )
        if not claimed:
            out["reason"] = claim_reason
            _log_execution(
                "SKIPPED",
                recovery_key=rk,
                schedule_id=int(row.id),
                source=src,
                detail=claim_reason,
            )
            return out

        row = claimed_row or row
        _log_execution(
            "CLAIMED",
            recovery_key=rk,
            schedule_id=int(row.id),
            source=src,
            detail=claim_reason,
        )

        ctx = load_context(row)
        abandon_phone = ctx.get("abandon_event_phone") or row.customer_phone
        multi_text = ctx.get("multi_message_text")
        msi = row.multi_slot_index if row.multi_slot_index >= 0 else None
        recovery_context = _build_recovery_context_from_schedule_row(row, source=src)

        from main import _run_recovery_sequence_after_cart_abandoned  # noqa: PLC0415

        await _run_recovery_sequence_after_cart_abandoned(
            rk,
            0.0,
            row.store_slug,
            row.session_id,
            row.cart_id,
            abandon_phone,
            multi_slot_index=msi,
            multi_message_text=multi_text,
            sequential_attempt_index=row.sequential_attempt_index,
            recovery_context=recovery_context,
        )
        out["ok"] = True
        out["reason"] = "finished"
        _log_execution(
            "FINISHED",
            recovery_key=rk,
            schedule_id=int(row.id),
            source=src,
        )
        try:
            from services.recovery_health_v1 import record_execution_finished

            record_execution_finished(
                recovery_key=rk,
                schedule_id=int(row.id),
                source=src,
                ok=True,
                reason=out["reason"],
            )
        except Exception:  # noqa: BLE001
            pass
        return out
    except Exception as exc:  # noqa: BLE001
        import asyncio

        if isinstance(exc, asyncio.CancelledError):
            exc_detail = "cancelled"
            raise
        exc_detail = str(exc)[:512]
        out["reason"] = "failed"
        out["error"] = exc_detail
        rk = (recovery_key or (row.recovery_key if row else "")) or ""
        _log_execution(
            "FAILED",
            recovery_key=rk,
            schedule_id=int(row.id) if row else schedule_id,
            source=src,
            detail=exc_detail,
        )
        return out
    finally:
        try:
            release_claimed_schedule_execution_terminal(
                recovery_context, exc_detail=exc_detail
            )
        except SQLAlchemyError as exc:
            db.session.rollback()
            _log.warning("execution boundary finalize failed: %s", exc)
        release_scoped_db_session()
