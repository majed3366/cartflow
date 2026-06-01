# -*- coding: utf-8 -*-
"""
Admin Recovery Resume Inspect / Scan v1 — read-only observability.

Does not call resume scan execution, stale repair, claims, sends, or any DB writes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule

_INSPECT_VERSION = "admin_recovery_resume_inspect_v1"
_SCAN_VERSION = "admin_recovery_resume_scan_v1"
_DEFAULT_LIMIT = 100
_MAX_LIMIT = 400

_COMPLETED_STATUSES = frozenset({"completed"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_dt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _minutes_since(dt: Optional[datetime], *, now: datetime) -> Optional[float]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 60.0)


def _stale_cutoff(now: datetime) -> datetime:
    from services.recovery_restart_survival import _running_stale_seconds

    return now - timedelta(seconds=int(_running_stale_seconds()))


def _query_schedules(
    *,
    store_slug: str = "",
    status: str = "",
    limit: int = _DEFAULT_LIMIT,
) -> list[RecoverySchedule]:
    try:
        db.create_all()
        q = db.session.query(RecoverySchedule)
        ss = (store_slug or "").strip()[:255]
        st = (status or "").strip().lower()[:64]
        if ss:
            q = q.filter(RecoverySchedule.store_slug == ss)
        if st:
            q = q.filter(RecoverySchedule.status == st)
        lim = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))
        return (
            q.order_by(RecoverySchedule.updated_at.desc())
            .limit(lim)
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []


def _is_stale_running(row: RecoverySchedule, *, cutoff: datetime) -> bool:
    from services.recovery_restart_survival import (
        STATUS_RUNNING,
        _is_running_schedule_stale,
    )

    if (row.status or "").strip() != STATUS_RUNNING:
        return False
    return bool(_is_running_schedule_stale(row, cutoff))


def _resume_eligibility(
    row: RecoverySchedule,
    *,
    now: datetime,
    force: bool = False,
) -> tuple[bool, str]:
    from services.recovery_restart_survival import (
        STATUS_SCHEDULED,
        evaluate_resume_safety,
        recovery_resume_filter_decision,
    )

    st = (row.status or "").strip()
    if st != STATUS_SCHEDULED:
        return False, f"status_{st or 'unknown'}"
    due = row.due_at
    if due is not None:
        due_utc = due.replace(tzinfo=timezone.utc) if due.tzinfo is None else due.astimezone(
            timezone.utc
        )
        if due_utc > now:
            return False, "future_due_at"
    decision, filt_reason = recovery_resume_filter_decision(row, force=force)
    if decision != "resume":
        return False, filt_reason or decision
    ok, safety_reason = evaluate_resume_safety(row, trust_durable_schedule=True)
    if not ok:
        return False, safety_reason
    return True, "scheduled_due"


def _inspect_item(
    row: RecoverySchedule,
    *,
    now: datetime,
    cutoff: datetime,
) -> dict[str, Any]:
    created = row.created_at
    updated = row.updated_at
    eligible, resume_reason = _resume_eligibility(row, now=now)
    stale = _is_stale_running(row, cutoff=cutoff)
    running_age = _minutes_since(updated if (row.status or "") == "running" else None, now=now)
    return {
        "recovery_key": (row.recovery_key or "")[:512],
        "store_slug": (row.store_slug or "")[:255],
        "status": (row.status or "")[:64],
        "due_at": _iso_dt(row.due_at),
        "created_at": _iso_dt(created),
        "age_minutes": round(_minutes_since(created, now=now) or 0.0, 1),
        "running_age_minutes": round(running_age, 1) if running_age is not None else None,
        "resume_eligible": bool(eligible),
        "resume_reason": resume_reason[:128],
        "stale_running": bool(stale),
        "schedule_id": int(row.id) if row.id is not None else None,
    }


def _aggregate_summary(rows: list[RecoverySchedule], *, now: datetime, cutoff: datetime) -> dict[str, Any]:
    from services.recovery_restart_survival import STATUS_RUNNING, STATUS_SCHEDULED

    scheduled = running = completed = resume_eligible = stale_running = scheduled_due_now = 0
    for row in rows:
        st = (row.status or "").strip().lower()
        if st == STATUS_SCHEDULED:
            scheduled += 1
            due = row.due_at
            if due is not None:
                due_utc = (
                    due.replace(tzinfo=timezone.utc)
                    if due.tzinfo is None
                    else due.astimezone(timezone.utc)
                )
                if due_utc <= now:
                    scheduled_due_now += 1
        elif st == STATUS_RUNNING:
            running += 1
        elif st in _COMPLETED_STATUSES:
            completed += 1
        if _is_stale_running(row, cutoff=cutoff):
            stale_running += 1
        ok, _ = _resume_eligibility(row, now=now)
        if ok:
            resume_eligible += 1
    return {
        "scheduled": scheduled,
        "running": running,
        "completed": completed,
        "resume_eligible": resume_eligible,
        "stale_running": stale_running,
        "scheduled_due_now": scheduled_due_now,
    }


def build_recovery_resume_health_summary_readonly(
    *,
    store_slug: str = "",
) -> dict[str, Any]:
    """Lightweight counts for Admin Operations Center card."""
    now = _utc_now()
    cutoff = _stale_cutoff(now)
    rows = _query_schedules(store_slug=store_slug, limit=_MAX_LIMIT)
    summary = _aggregate_summary(rows, now=now, cutoff=cutoff)
    return {
        "version": _INSPECT_VERSION,
        "generated_at": _iso_dt(now),
        "store_slug": (store_slug or "").strip()[:255] or None,
        **summary,
        "inspect_path": "/admin/operations/recovery-resume-inspect",
        "scan_path": "/admin/operations/recovery-resume-scan",
    }


def build_recovery_resume_inspect_readonly(
    *,
    store_slug: str = "",
    status: str = "",
    resume_only: bool = False,
    stale_only: bool = False,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    now = _utc_now()
    cutoff = _stale_cutoff(now)
    rows = _query_schedules(store_slug=store_slug, status=status, limit=limit)
    items = [_inspect_item(row, now=now, cutoff=cutoff) for row in rows]
    if resume_only:
        items = [i for i in items if i.get("resume_eligible")]
    if stale_only:
        items = [i for i in items if i.get("stale_running")]
    summary = _aggregate_summary(rows, now=now, cutoff=cutoff)
    return {
        "version": _INSPECT_VERSION,
        "generated_at": _iso_dt(now),
        "dry_run": True,
        "read_only": True,
        "filters": {
            "store_slug": (store_slug or "").strip()[:255] or None,
            "status": (status or "").strip().lower()[:64] or None,
            "resume_only": bool(resume_only),
            "stale_only": bool(stale_only),
            "limit": max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT)),
        },
        "summary": summary,
        "items": items,
        "items_returned": len(items),
    }


def _simulate_scan_action(
    row: RecoverySchedule,
    *,
    now: datetime,
) -> tuple[str, str]:
    """Map one schedule row to would_resume | would_skip | would_ignore action."""
    from services.recovery_restart_survival import (
        STATUS_RUNNING,
        STATUS_SCHEDULED,
        _TERMINAL,
        evaluate_resume_safety,
        recovery_resume_filter_decision,
    )

    st = (row.status or "").strip()
    rk = (row.recovery_key or "")[:512]

    if st in _TERMINAL or st in _COMPLETED_STATUSES:
        return "skip", st or "terminal"

    if st == STATUS_RUNNING:
        cutoff = _stale_cutoff(now)
        if _is_stale_running(row, cutoff=cutoff):
            return "skip", "stale_running"
        return "ignore", "running_in_progress"

    if st != STATUS_SCHEDULED:
        return "skip", st or "unsupported_status"

    due = row.due_at
    if due is not None:
        due_utc = (
            due.replace(tzinfo=timezone.utc)
            if due.tzinfo is None
            else due.astimezone(timezone.utc)
        )
        if due_utc > now:
            return "ignore", "future_due_at"

    decision, filt_reason = recovery_resume_filter_decision(row, force=False)
    if decision != "resume":
        return "skip", filt_reason or decision

    ok, safety_reason = evaluate_resume_safety(row, trust_durable_schedule=True)
    if not ok:
        return "skip", safety_reason

    return "resume", "scheduled_due"


def build_recovery_resume_scan_readonly(
    *,
    store_slug: str = "",
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:
    """
    Dry-run simulation of startup resume scan — no mutations, no dispatch, no repair.
    """
    now = _utc_now()
    lim = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))
    rows = _query_schedules(store_slug=store_slug, limit=lim)

    results: list[dict[str, Any]] = []
    would_resume = would_skip = would_ignore = 0

    for row in rows:
        action, reason = _simulate_scan_action(row, now=now)
        if action == "resume":
            would_resume += 1
        elif action == "skip":
            would_skip += 1
        else:
            would_ignore += 1
        results.append(
            {
                "recovery_key": (row.recovery_key or "")[:512],
                "store_slug": (row.store_slug or "")[:255],
                "status": (row.status or "")[:64],
                "action": action,
                "reason": reason[:128],
                "schedule_id": int(row.id) if row.id is not None else None,
            }
        )

    return {
        "version": _SCAN_VERSION,
        "generated_at": _iso_dt(now),
        "dry_run": True,
        "read_only": True,
        "no_db_writes": True,
        "store_slug": (store_slug or "").strip()[:255] or None,
        "would_resume": would_resume,
        "would_skip": would_skip,
        "would_ignore": would_ignore,
        "results": results,
        "results_returned": len(results),
    }
