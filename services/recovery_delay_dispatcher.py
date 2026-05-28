# -*- coding: utf-8 -*-
"""
Recovery delay dispatcher — sole owner of in-process delay waiting before execution.

Replace this module later with queue enqueue / worker scheduler / cron due scanner
without changing ``execute_recovery_schedule``.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

from sqlalchemy.exc import SQLAlchemyError

from services.recovery_execution_boundary import (
    execute_recovery_schedule,
    resolve_recovery_schedule_row,
)
from services.recovery_restart_survival import (
    STATUS_SCHEDULED,
    _TERMINAL,
    load_context,
)

_log = logging.getLogger("cartflow")

RunAt = Union[datetime, float]


def _log_dispatch(
    tag: str,
    *,
    schedule_id: int,
    source: str,
    recovery_key: str = "",
    detail: str = "",
    run_at: Optional[datetime] = None,
    wait_seconds: Optional[float] = None,
) -> None:
    try:
        print(f"[RECOVERY DISPATCH {tag}]", flush=True)
        print(f"schedule_id={schedule_id}", flush=True)
        print(f"source={(source or '-')[:64]}", flush=True)
        if recovery_key:
            print(f"recovery_key={recovery_key[:120]}", flush=True)
        if run_at is not None:
            print(f"run_at={run_at.isoformat()}", flush=True)
        if wait_seconds is not None:
            print(f"wait_seconds={wait_seconds:.3f}", flush=True)
        if detail:
            print(f"detail={detail[:96]}", flush=True)
    except OSError:
        pass


def _coerce_run_at(run_at: RunAt) -> datetime:
    if isinstance(run_at, datetime):
        dt = run_at
    else:
        dt = datetime.now(timezone.utc) + timedelta(seconds=max(0.0, float(run_at)))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _delay_sleep(seconds: float) -> None:
    """Delegate to ``main.asyncio.sleep`` so tests patching ``main.asyncio.sleep`` still apply."""
    import main  # noqa: PLC0415

    await main.asyncio.sleep(max(0.0, float(seconds)))


def spawn_recovery_schedule_dispatch(
    schedule_id: int,
    run_at: RunAt,
    source: str,
) -> None:
    """Fire-and-forget in-process delay dispatch (asyncio task)."""
    asyncio.create_task(
        dispatch_recovery_schedule(int(schedule_id), run_at, source),
        name=f"recovery_dispatch_{int(schedule_id)}",
    )


async def dispatch_recovery_schedule(
    schedule_id: int,
    run_at: RunAt,
    source: str,
) -> Dict[str, Any]:
    """
    Wait until ``run_at`` then run ``execute_recovery_schedule`` for the durable row.

    This is the only module that should ``sleep`` for live delayed recovery.
    """
    from services.db_session_lifecycle import (
        release_db_before_async_wait,
        release_scoped_db_session,
        scoped_db_session_begin,
    )
    from services.recovery_delay_unified import (
        log_recovery_delay_scheduled,
        timing_from_recovery_context,
    )

    scoped_db_session_begin()
    src = (source or "unknown").strip()[:64]
    sched_id = int(schedule_id)
    out: Dict[str, Any] = {
        "ok": False,
        "schedule_id": sched_id,
        "source": src,
        "reason": "",
    }
    exc_detail = ""
    try:
        row = resolve_recovery_schedule_row(schedule_id=sched_id)
        if row is None:
            out["reason"] = "schedule_row_missing"
            _log_dispatch(
                "SKIPPED",
                schedule_id=sched_id,
                source=src,
                detail=out["reason"],
            )
            return out

        schedule_rk_raw = (row.recovery_key or "").strip()
        ctx = load_context(row)
        rc = dict(ctx.get("recovery_context") or {})
        ctx_rk_raw = (str(rc.get("recovery_key") or "")).strip()
        from services.recovery_restart_survival import (  # noqa: PLC0415
            reconcile_schedule_row_identity,
        )

        rk, slug, sess_id = reconcile_schedule_row_identity(
            row, source_function="dispatch_recovery_schedule"
        )
        out["recovery_key"] = rk
        _log_dispatch(
            "REQUEST",
            schedule_id=sched_id,
            source=src,
            recovery_key=rk,
            run_at=_coerce_run_at(run_at) if row.due_at is None else row.due_at,
        )

        if row.status in _TERMINAL:
            out["reason"] = f"already_terminal:{row.status}"
            _log_dispatch(
                "SKIPPED",
                schedule_id=sched_id,
                source=src,
                recovery_key=rk,
                detail=out["reason"],
            )
            return out

        if row.status != STATUS_SCHEDULED:
            out["reason"] = f"not_scheduled:{row.status}"
            _log_dispatch(
                "SKIPPED",
                schedule_id=sched_id,
                source=src,
                recovery_key=rk,
                detail=out["reason"],
            )
            return out

        due_at = row.due_at if row.due_at is not None else _coerce_run_at(run_at)
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        else:
            due_at = due_at.astimezone(timezone.utc)

        now = datetime.now(timezone.utc)
        wait_seconds = max(0.0, (due_at - now).total_seconds())

        rc = dict(ctx.get("recovery_context") or {})
        sched_timing = timing_from_recovery_context(rc)
        if sched_timing is None and ctx.get("schedule_timing"):
            sched_timing = ctx.get("schedule_timing")
        if sched_timing is None:
            sched_timing = {
                "effective_delay_seconds": float(row.effective_delay_seconds or wait_seconds),
                "source": str(row.delay_source or "scheduled_task_delay"),
                "reason_tag": str(row.reason_tag or ""),
                "stage": int(row.step or 1),
            }
        log_recovery_delay_scheduled(
            sched_timing,
            recovery_key=rk,
            scheduled_delay_seconds=float(wait_seconds),
        )
        try:
            print("[DELAY STARTED]", wait_seconds / 60.0, flush=True)
            print("[DELAY STARTED SECONDS]", float(wait_seconds), flush=True)
            if sched_timing:
                print(
                    "[DELAY STARTED SOURCE]",
                    sched_timing.get("source"),
                    "reason=",
                    sched_timing.get("reason_tag"),
                    flush=True,
                )
        except OSError:
            pass

        _log_dispatch(
            "SCHEDULED",
            schedule_id=sched_id,
            source=src,
            recovery_key=rk,
            run_at=due_at,
            wait_seconds=wait_seconds,
        )

        try:
            from main import _note_recovery_delay_waiting_started  # noqa: PLC0415

            _note_recovery_delay_waiting_started(
                rk,
                dashboard_store=slug,
                schedule_recovery_key=schedule_rk_raw,
                ctx_recovery_key=ctx_rk_raw,
                derived_store_slug=slug,
                source_function="dispatch_recovery_schedule",
                store_slug=slug,
                session_id=sess_id,
                recovery_context=rc,
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning("delay_started hook: %s", exc)

        print("[DELAY WAITING]")
        await release_db_before_async_wait()
        try:
            await _delay_sleep(wait_seconds)
        except asyncio.CancelledError:
            exc_detail = "cancelled"
            raise

        print("[DELAY FINISHED]")
        _log_dispatch(
            "DUE",
            schedule_id=sched_id,
            source=src,
            recovery_key=rk,
            run_at=due_at,
        )

        exec_out = await execute_recovery_schedule(
            schedule_id=sched_id,
            source=src,
        )
        out["execution"] = exec_out
        out["ok"] = bool(exec_out.get("ok"))
        out["reason"] = str(exec_out.get("reason") or "finished")
        try:
            from services.recovery_attempt2_trace_v1 import (  # noqa: PLC0415
                _row_is_attempt2,
                trace_attempt2_for_recovery_key,
            )

            if _row_is_attempt2(row):
                trace_attempt2_for_recovery_key(
                    rk,
                    path=f"dispatch_recovery_schedule:{src}",
                    extra={
                        "dispatch_called": "true_after_execute",
                        "execute_ok": bool(exec_out.get("ok")),
                        "execute_reason": str(exec_out.get("reason") or ""),
                    },
                )
        except Exception:  # noqa: BLE001
            pass
        return out
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, asyncio.CancelledError):
            exc_detail = "cancelled"
            raise
        exc_detail = str(exc)[:512]
        out["reason"] = "failed"
        out["error"] = exc_detail
        _log_dispatch(
            "FAILED",
            schedule_id=sched_id,
            source=src,
            detail=exc_detail,
        )
        return out
    finally:
        if exc_detail == "cancelled":
            _log_dispatch(
                "FAILED",
                schedule_id=sched_id,
                source=src,
                detail=exc_detail,
            )
        release_scoped_db_session()
