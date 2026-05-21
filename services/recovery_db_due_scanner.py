# -*- coding: utf-8 -*-
"""
Manual DB due scanner for RecoverySchedule rows (queue/worker readiness v1).

Finds durable rows with status=scheduled and due_at <= now, then dispatches each
through execute_recovery_schedule. Manual: ``scripts/db_due_scanner_verify.py``.
Optional automatic loop: ``services/recovery_db_due_scanner_loop.py`` when
``CARTFLOW_DB_DUE_SCANNER_ENABLED=true``.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule
from services.recovery_restart_survival import (
    STATUS_SCHEDULED,
    STATUS_SKIPPED_RESUME,
    _utc_now,
    evaluate_resume_safety,
    finalize_recovery_schedule_durable,
    repair_stale_running_recovery_schedules,
)

_log = logging.getLogger(__name__)

DEFAULT_SOURCE = "db_due_scanner"


def _log_scanner(tag: str, **fields: Any) -> None:
    parts = [f"{k}={fields[k]}" for k in sorted(fields) if fields[k] is not None]
    suffix = f" {' '.join(parts)}" if parts else ""
    print(f"[DB DUE SCANNER {tag}]{suffix}", flush=True)


async def scan_due_recovery_schedules(
    *,
    limit: int = 25,
    source: str = DEFAULT_SOURCE,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Scan for due scheduled recovery rows and dispatch through the execution boundary.

    Does not replace asyncio delay dispatch or startup resume scan.
    """
    src = (source or DEFAULT_SOURCE).strip()[:64]
    lim = max(1, int(limit))
    _log_scanner("START", source=src, limit=lim, dry_run=dry_run)

    out: Dict[str, Any] = {
        "source": src,
        "limit": lim,
        "dry_run": dry_run,
        "found": 0,
        "dispatched": 0,
        "skipped": 0,
        "outcomes": [],
    }

    try:
        db.create_all()
        stale_repair = repair_stale_running_recovery_schedules()
        out["stale_running_repair"] = stale_repair

        now = _utc_now()
        due_rows: List[RecoverySchedule] = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.status == STATUS_SCHEDULED,
                RecoverySchedule.due_at <= now,
            )
            .order_by(RecoverySchedule.due_at.asc())
            .limit(lim)
            .all()
        )
        out["found"] = len(due_rows)
        _log_scanner("FOUND", count=len(due_rows), source=src)

        from services.recovery_execution_boundary import execute_recovery_schedule

        for row in due_rows:
            rk = row.recovery_key
            sid = int(row.id)
            ok, reason = evaluate_resume_safety(row)
            if not ok:
                out["skipped"] += 1
                _log_scanner(
                    "SKIPPED",
                    schedule_id=sid,
                    recovery_key=rk,
                    reason=reason,
                    source=src,
                )
                if not dry_run:
                    finalize_recovery_schedule_durable(
                        rk,
                        status=STATUS_SKIPPED_RESUME,
                        multi_slot_index=row.multi_slot_index
                        if row.multi_slot_index >= 0
                        else None,
                        sequential_attempt_index=row.sequential_attempt_index,
                        detail=f"db_due_scanner:{reason}",
                    )
                out["outcomes"].append(
                    {
                        "schedule_id": sid,
                        "recovery_key": rk,
                        "dispatched": False,
                        "reason": reason,
                    }
                )
                continue

            if dry_run:
                out["skipped"] += 1
                _log_scanner(
                    "SKIPPED",
                    schedule_id=sid,
                    recovery_key=rk,
                    reason="dry_run",
                    source=src,
                )
                out["outcomes"].append(
                    {
                        "schedule_id": sid,
                        "recovery_key": rk,
                        "dispatched": False,
                        "reason": "dry_run",
                    }
                )
                continue

            _log_scanner(
                "DISPATCH",
                schedule_id=sid,
                recovery_key=rk,
                due_at=row.due_at.isoformat() if row.due_at else None,
                source=src,
            )
            exec_out = await execute_recovery_schedule(schedule_id=sid, source=src)
            dispatched = bool(exec_out.get("ok"))
            if dispatched:
                out["dispatched"] += 1
            else:
                out["skipped"] += 1
                _log_scanner(
                    "SKIPPED",
                    schedule_id=sid,
                    recovery_key=rk,
                    reason=exec_out.get("reason") or "not_dispatched",
                    source=src,
                )
            out["outcomes"].append(
                {
                    "schedule_id": sid,
                    "recovery_key": rk,
                    "dispatched": dispatched,
                    "reason": exec_out.get("reason"),
                    "execute_out": exec_out,
                }
            )

        _log_scanner(
            "DONE",
            source=src,
            found=out["found"],
            dispatched=out["dispatched"],
            skipped=out["skipped"],
        )
        return out
    except SQLAlchemyError as exc:
        db.session.rollback()
        _log.warning("db due scanner failed: %s", exc)
        out["error"] = str(exc)
        _log_scanner("DONE", source=src, error=str(exc)[:200])
        return out


def scan_due_recovery_schedules_sync(
    *,
    limit: int = 25,
    source: str = DEFAULT_SOURCE,
    dry_run: bool = False,
) -> Dict[str, Any]:
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return {
                "source": source,
                "error": "event_loop_running",
                "found": 0,
                "dispatched": 0,
            }
        return loop.run_until_complete(
            scan_due_recovery_schedules(limit=limit, source=source, dry_run=dry_run)
        )
    except RuntimeError:
        return asyncio.run(
            scan_due_recovery_schedules(limit=limit, source=source, dry_run=dry_run)
        )
