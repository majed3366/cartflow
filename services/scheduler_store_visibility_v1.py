# -*- coding: utf-8 -*-
"""
Per-store scheduler visibility v1 — read-only backlog breakdown.

No scheduling behavior changes. Aggregates RecoverySchedule rows by store_slug.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import case, func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule
from services.recovery_restart_survival import STATUS_RUNNING, STATUS_SCHEDULED, _utc_now

_DEFAULT_STALE_RUNNING_SECONDS = 600


def _stale_running_threshold_seconds() -> int:
    raw = (os.getenv("CARTFLOW_RECOVERY_HEALTH_STUCK_RUNNING_SECONDS") or "").strip()
    if raw.isdigit():
        return max(60, int(raw))
    return _DEFAULT_STALE_RUNNING_SECONDS


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def build_scheduler_store_visibility(
    *,
    store_limit: int = 20,
    stale_seconds: Optional[int] = None,
) -> dict[str, Any]:
    """Read-only per-store scheduler backlog and pressure metrics."""
    threshold = stale_seconds if stale_seconds is not None else _stale_running_threshold_seconds()
    now = _utc_now()
    now_naive = now.replace(tzinfo=None)
    cutoff_naive = (now - timedelta(seconds=threshold)).replace(tzinfo=None)

    out: dict[str, Any] = {
        "generated_at": _iso(now),
        "stale_running_threshold_seconds": threshold,
        "stores_with_due": 0,
        "stores_with_backlog": 0,
        "stores_with_stale_running": 0,
        "total_due": 0,
        "total_scheduled_future": 0,
        "total_running": 0,
        "total_stale_running": 0,
        "dominant_store_slug": None,
        "dominant_store_due_share": 0.0,
        "stores": [],
        "error": None,
    }

    due_expr = case(
        (
            (RecoverySchedule.status == STATUS_SCHEDULED)
            & (RecoverySchedule.due_at <= now_naive),
            1,
        ),
        else_=0,
    )
    future_expr = case(
        (
            (RecoverySchedule.status == STATUS_SCHEDULED)
            & (RecoverySchedule.due_at > now_naive),
            1,
        ),
        else_=0,
    )
    running_expr = case(
        (RecoverySchedule.status == STATUS_RUNNING, 1),
        else_=0,
    )
    stale_expr = case(
        (
            (RecoverySchedule.status == STATUS_RUNNING)
            & (RecoverySchedule.updated_at < cutoff_naive),
            1,
        ),
        else_=0,
    )

    try:
        db.create_all()
        rows = (
            db.session.query(
                RecoverySchedule.store_slug,
                func.sum(due_expr).label("due_count"),
                func.sum(future_expr).label("scheduled_future_count"),
                func.sum(running_expr).label("running_count"),
                func.sum(stale_expr).label("stale_running_count"),
            )
            .filter(RecoverySchedule.store_slug.isnot(None))
            .filter(RecoverySchedule.store_slug != "")
            .group_by(RecoverySchedule.store_slug)
            .all()
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["error"] = str(exc)[:200]
        return out

    store_rows: list[dict[str, Any]] = []
    total_due = 0
    for slug, due_c, future_c, run_c, stale_c in rows:
        slug_s = str(slug or "").strip()[:255]
        if not slug_s:
            continue
        due_n = int(due_c or 0)
        future_n = int(future_c or 0)
        run_n = int(run_c or 0)
        stale_n = int(stale_c or 0)
        total_due += due_n
        store_rows.append(
            {
                "store_slug": slug_s,
                "due_count": due_n,
                "scheduled_future_count": future_n,
                "running_count": run_n,
                "stale_running_count": stale_n,
                "backlog_count": due_n + run_n,
                "has_due": due_n > 0,
                "has_backlog": (due_n + run_n) > 0,
                "has_stale_running": stale_n > 0,
            }
        )

    store_rows.sort(
        key=lambda r: (
            -int(r.get("due_count") or 0),
            -int(r.get("backlog_count") or 0),
            str(r.get("store_slug") or ""),
        )
    )
    limited = store_rows[: max(1, int(store_limit or 20))]

    total_future = sum(int(r.get("scheduled_future_count") or 0) for r in store_rows)
    total_running = sum(int(r.get("running_count") or 0) for r in store_rows)
    total_stale = sum(int(r.get("stale_running_count") or 0) for r in store_rows)

    dominant_slug = None
    dominant_share = 0.0
    if total_due > 0 and limited:
        top = limited[0]
        dominant_slug = top.get("store_slug")
        dominant_share = round(int(top.get("due_count") or 0) / total_due, 4)

    for row in limited:
        due_n = int(row.get("due_count") or 0)
        row["due_share"] = round(due_n / total_due, 4) if total_due > 0 else 0.0

    out.update(
        {
            "stores_with_due": sum(1 for r in store_rows if r.get("has_due")),
            "stores_with_backlog": sum(1 for r in store_rows if r.get("has_backlog")),
            "stores_with_stale_running": sum(
                1 for r in store_rows if r.get("has_stale_running")
            ),
            "total_due": total_due,
            "total_scheduled_future": total_future,
            "total_running": total_running,
            "total_stale_running": total_stale,
            "dominant_store_slug": dominant_slug,
            "dominant_store_due_share": dominant_share,
            "stores": limited,
            "store_count": len(store_rows),
        }
    )
    return out


__all__ = ["build_scheduler_store_visibility"]
