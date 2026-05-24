# -*- coding: utf-8 -*-
"""
Recovery / worker health visibility v1 — read-only operational snapshot.

No recovery behavior changes. Aggregates DB schedule rows + in-process heartbeat
metrics recorded from existing resume / claim / execution paths.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule
from services.recovery_restart_survival import (
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FAILED_RESUME,
    STATUS_FAILED_RESUME_STALE,
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    STATUS_SKIPPED_DUPLICATE,
    STATUS_SKIPPED_NO_PHONE,
    STATUS_SKIPPED_NO_REASON,
    STATUS_SKIPPED_RESUME,
    STATUS_WHATSAPP_FAILED,
    _utc_now,
)

log = logging.getLogger("cartflow")

_DEFAULT_STUCK_RUNNING_SECONDS = 600
_DEFAULT_RESUME_STALE_SECONDS = 1800

_lock = threading.Lock()
_heartbeat: dict[str, Any] = {
    "last_resume_scan_at": None,
    "last_resume_scan": None,
    "last_schedule_claim_at": None,
    "last_schedule_claim": None,
    "last_execution_at": None,
    "last_execution": None,
}


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        raw = str(s).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _stuck_running_threshold_seconds() -> int:
    raw = (os.getenv("CARTFLOW_RECOVERY_HEALTH_STUCK_RUNNING_SECONDS") or "").strip()
    if raw.isdigit():
        return max(60, int(raw))
    return _DEFAULT_STUCK_RUNNING_SECONDS


def _resume_stale_threshold_seconds() -> int:
    raw = (os.getenv("CARTFLOW_RECOVERY_HEALTH_RESUME_STALE_SECONDS") or "").strip()
    if raw.isdigit():
        return max(120, int(raw))
    return _DEFAULT_RESUME_STALE_SECONDS


def clear_recovery_health_v1_for_tests() -> None:
    with _lock:
        _heartbeat["last_resume_scan_at"] = None
        _heartbeat["last_resume_scan"] = None
        _heartbeat["last_schedule_claim_at"] = None
        _heartbeat["last_schedule_claim"] = None
        _heartbeat["last_execution_at"] = None
        _heartbeat["last_execution"] = None


def record_resume_scan_completed(result: dict[str, Any]) -> None:
    """Called when ``run_recovery_resume_scan_async`` finishes (observe only)."""
    now = _utc_now()
    payload = {
        "at": _iso(now),
        "enabled": bool(result.get("enabled")),
        "dispatched": int(result.get("dispatched") or 0),
        "due_processed": int(result.get("due_processed") or 0),
        "future_rearmed": int(result.get("future_rearmed") or 0),
        "reason": str(result.get("reason") or ""),
        "error": str(result.get("error") or "")[:200] or None,
    }
    with _lock:
        _heartbeat["last_resume_scan_at"] = payload["at"]
        _heartbeat["last_resume_scan"] = payload


def record_schedule_claim(
    *,
    recovery_key: str,
    schedule_id: int,
    path: str,
    step: int,
) -> None:
    now = _utc_now()
    payload = {
        "at": _iso(now),
        "recovery_key": (recovery_key or "")[:120],
        "schedule_id": int(schedule_id),
        "path": (path or "")[:64],
        "step": int(step),
    }
    with _lock:
        _heartbeat["last_schedule_claim_at"] = payload["at"]
        _heartbeat["last_schedule_claim"] = payload


def record_execution_finished(
    *,
    recovery_key: str,
    schedule_id: Optional[int],
    source: str,
    ok: bool,
    reason: str,
) -> None:
    now = _utc_now()
    payload = {
        "at": _iso(now),
        "recovery_key": (recovery_key or "")[:120],
        "schedule_id": schedule_id,
        "source": (source or "")[:64],
        "ok": bool(ok),
        "reason": (reason or "")[:96],
    }
    with _lock:
        _heartbeat["last_execution_at"] = payload["at"]
        _heartbeat["last_execution"] = payload


def _heartbeat_snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "last_resume": dict(_heartbeat["last_resume_scan"] or {}),
            "last_resume_at": _heartbeat["last_resume_scan_at"],
            "last_claim": dict(_heartbeat["last_schedule_claim"] or {}),
            "last_claim_at": _heartbeat["last_schedule_claim_at"],
            "last_execution": dict(_heartbeat["last_execution"] or {}),
            "last_execution_at": _heartbeat["last_execution_at"],
        }


def _scheduler_resume_heartbeat_status(
    *,
    owner_enabled: bool,
    last_resume_at: Optional[str],
    pending_due: int,
) -> str:
    if not owner_enabled:
        return "disabled"
    if not last_resume_at:
        return "unknown" if pending_due == 0 else "warning"
    age = _utc_now() - (_parse_iso(last_resume_at) or _utc_now())
    if age.total_seconds() > _resume_stale_threshold_seconds():
        return "stale" if pending_due > 0 else "warning"
    return "healthy"


def _query_stuck_running(threshold_seconds: int) -> dict[str, Any]:
    cutoff = _utc_now() - timedelta(seconds=threshold_seconds)
    cutoff_naive = cutoff.replace(tzinfo=None)
    out: dict[str, Any] = {
        "threshold_seconds": threshold_seconds,
        "count": 0,
        "oldest_seconds": None,
        "oldest": None,
        "examples": [],
        "stuck_running_detected": False,
    }
    try:
        db.create_all()
        rows = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.status == STATUS_RUNNING,
                RecoverySchedule.updated_at < cutoff_naive,
            )
            .order_by(RecoverySchedule.updated_at.asc())
            .limit(10)
            .all()
        )
        total = (
            db.session.query(func.count(RecoverySchedule.id))
            .filter(
                RecoverySchedule.status == STATUS_RUNNING,
                RecoverySchedule.updated_at < cutoff_naive,
            )
            .scalar()
        )
        count = int(total or 0)
        out["count"] = count
        out["stuck_running_detected"] = count > 0
        if rows:
            oldest = rows[0]
            odt = oldest.updated_at
            if odt is not None:
                if odt.tzinfo is None:
                    odt = odt.replace(tzinfo=timezone.utc)
                else:
                    odt = odt.astimezone(timezone.utc)
                out["oldest"] = _iso(odt)
                out["oldest_seconds"] = int(
                    max(0, (_utc_now() - odt).total_seconds())
                )
            out["examples"] = [
                {
                    "schedule_id": int(r.id),
                    "recovery_key": (r.recovery_key or "")[:120],
                    "store_slug": (r.store_slug or "")[:64],
                    "updated_at": _iso(
                        r.updated_at.replace(tzinfo=timezone.utc)
                        if r.updated_at and r.updated_at.tzinfo is None
                        else r.updated_at
                    ),
                    "step": int(r.step),
                }
                for r in rows[:5]
            ]
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["error"] = str(exc)[:200]
    return out


def _schedule_counts() -> dict[str, Any]:
    counts: dict[str, int] = {}
    pending_due = 0
    try:
        db.create_all()
        now_naive = _utc_now().replace(tzinfo=None)
        for st, cnt in (
            db.session.query(RecoverySchedule.status, func.count(RecoverySchedule.id))
            .group_by(RecoverySchedule.status)
            .all()
        ):
            counts[str(st)] = int(cnt or 0)
        pending_due = int(
            db.session.query(func.count(RecoverySchedule.id))
            .filter(
                RecoverySchedule.status == STATUS_SCHEDULED,
                RecoverySchedule.due_at <= now_naive,
            )
            .scalar()
            or 0
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"error": str(exc)[:200], "by_status": {}, "pending_due": 0}

    failed_statuses = (
        STATUS_FAILED_RESUME,
        STATUS_FAILED_RESUME_STALE,
        STATUS_WHATSAPP_FAILED,
    )
    cancelled = int(counts.get(STATUS_CANCELLED, 0))
    failed = sum(int(counts.get(s, 0)) for s in failed_statuses)
    running = int(counts.get(STATUS_RUNNING, 0))
    scheduled = int(counts.get(STATUS_SCHEDULED, 0))
    completed = int(counts.get(STATUS_COMPLETED, 0))

    return {
        "by_status": counts,
        "scheduled": scheduled,
        "running": running,
        "cancelled": cancelled,
        "failed": failed,
        "completed": completed,
        "pending_due": pending_due,
        "skipped": sum(
            int(counts.get(s, 0))
            for s in (
                STATUS_SKIPPED_RESUME,
                STATUS_SKIPPED_DUPLICATE,
                STATUS_SKIPPED_NO_PHONE,
                STATUS_SKIPPED_NO_REASON,
            )
        ),
    }


def _protections_summary() -> dict[str, Any]:
    from services.recovery_scheduler_guardrails import (
        resolve_recovery_resume_on_startup_config,
    )

    sched = resolve_recovery_resume_on_startup_config()
    owner_enabled = bool(sched["enabled"])

    restart_survival = "enabled"
    purchase_stop = "enabled"
    session_truth = "enabled"
    duplicate_guard = "unknown"

    try:
        from services.cartflow_duplicate_guard import (
            get_duplicate_guard_diagnostics_readonly,
        )

        dup = get_duplicate_guard_diagnostics_readonly()
        duplicate_guard = "enabled" if dup else "unknown"
    except Exception:  # noqa: BLE001
        pass

    try:
        from services.recovery_db_due_scanner_loop import (
            is_db_due_scanner_loop_enabled,
        )

        db_scanner = (
            "enabled" if is_db_due_scanner_loop_enabled() else "disabled"
        )
    except Exception:  # noqa: BLE001
        db_scanner = "unknown"

    return {
        "scheduler_owner": {
            "status": "enabled" if owner_enabled else "disabled",
            "resume_on_startup": owner_enabled,
            "reason": sched.get("reason"),
        },
        "restart_survival": restart_survival,
        "purchase_stop": purchase_stop,
        "session_truth_hardening": session_truth,
        "duplicate_guard": duplicate_guard,
        "lifecycle_truth_shadow": "enabled",
        "db_due_scanner_loop": db_scanner,
    }


def _compute_overall_health(
    *,
    stuck: dict[str, Any],
    scheduler_status: str,
    pending_due: int,
) -> str:
    if stuck.get("stuck_running_detected"):
        return "warning"
    if scheduler_status == "stale":
        return "stale"
    if scheduler_status in ("warning", "unknown") and pending_due > 0:
        return "warning"
    if scheduler_status == "disabled" and pending_due > 0:
        return "warning"
    return "healthy"


def build_recovery_health_snapshot(*, emit_warn_log: bool = True) -> dict[str, Any]:
    """
    Read-only recovery health for operators and ``GET /dev/recovery-health``.
    """
    threshold = _stuck_running_threshold_seconds()
    stuck = _query_stuck_running(threshold)
    counts = _schedule_counts()
    hb = _heartbeat_snapshot()
    protections = _protections_summary()
    owner_enabled = bool(
        protections.get("scheduler_owner", {}).get("resume_on_startup")
    )

    scheduler_status = _scheduler_resume_heartbeat_status(
        owner_enabled=owner_enabled,
        last_resume_at=hb.get("last_resume_at"),
        pending_due=int(counts.get("pending_due") or 0),
    )

    health = _compute_overall_health(
        stuck=stuck,
        scheduler_status=scheduler_status,
        pending_due=int(counts.get("pending_due") or 0),
    )

    if emit_warn_log and stuck.get("stuck_running_detected"):
        try:
            print(
                "[RECOVERY HEALTH] stuck_running_detected=true "
                f"count={stuck.get('count')} "
                f"threshold_seconds={threshold}",
                flush=True,
            )
        except OSError:
            pass

    scheduler_label = (
        "owner"
        if owner_enabled
        else "api_replica_no_resume"
    )

    return {
        "ok": True,
        "health": health,
        "scheduler": scheduler_label,
        "scheduler_detail": {
            "mode": scheduler_label,
            "resume_heartbeat": scheduler_status,
            **protections.get("scheduler_owner", {}),
        },
        "stuck_running": stuck,
        "pending_due": int(counts.get("pending_due") or 0),
        "running": int(counts.get("running") or 0),
        "scheduled": int(counts.get("scheduled") or 0),
        "cancelled": int(counts.get("cancelled") or 0),
        "failed": int(counts.get("failed") or 0),
        "counts": counts,
        "last_resume": hb.get("last_resume") or None,
        "last_claim": hb.get("last_claim") or None,
        "last_execution": hb.get("last_execution") or None,
        "protections": protections,
        "generated_at": _iso(_utc_now()),
    }


__all__ = [
    "build_recovery_health_snapshot",
    "clear_recovery_health_v1_for_tests",
    "record_execution_finished",
    "record_resume_scan_completed",
    "record_schedule_claim",
]
