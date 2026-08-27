# -*- coding: utf-8 -*-
"""Admin-only, rate-limited Scheduler DB diagnostic. Not a Railway healthcheck."""
from __future__ import annotations

import os
import time
from typing import Any

_MIN_INTERVAL_S = 60.0
_last_ok_at = 0.0


class SchedulerDeepHealthDenied(RuntimeError):
    """Not authorized or rate-limited."""


def _admin_ok(key: str) -> bool:
    expected = (os.getenv("CARTFLOW_ADMIN_PASSWORD") or "").strip()
    if expected and (key or "").strip() == expected:
        return True
    token = (os.getenv("CARTFLOW_SCHEDULER_DEEP_HEALTH_TOKEN") or "").strip()
    return bool(token) and (key or "").strip() == token


def assert_deep_health_allowed(key: str) -> None:
    global _last_ok_at
    if not _admin_ok(key):
        raise SchedulerDeepHealthDenied("forbidden")
    now = time.monotonic()
    if _last_ok_at and (now - _last_ok_at) < _MIN_INTERVAL_S:
        raise SchedulerDeepHealthDenied("rate_limited")
    _last_ok_at = now


def reset_deep_health_rate_limit_for_tests() -> None:
    global _last_ok_at
    _last_ok_at = 0.0


def build_scheduler_deep_health_snapshot() -> dict[str, Any]:
    """Optional DB counts. Never calls create_all()."""
    from datetime import datetime, timedelta, timezone  # noqa: PLC0415

    from sqlalchemy import func  # noqa: PLC0415
    from sqlalchemy.exc import SQLAlchemyError  # noqa: PLC0415

    from extensions import db  # noqa: PLC0415
    from models import RecoverySchedule  # noqa: PLC0415
    from services.recovery_process_role_v1 import evaluate_scheduler_ownership_policy  # noqa: PLC0415

    policy = evaluate_scheduler_ownership_policy(force=False)
    out: dict[str, Any] = {
        "ok": True,
        "deep": True,
        "role": policy.get("role"),
        "overdue_scheduled_count": 0,
        "running_stale_count": 0,
    }
    try:
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff_naive = (datetime.now(timezone.utc) - timedelta(seconds=600)).replace(
            tzinfo=None
        )
        out["overdue_scheduled_count"] = int(
            db.session.query(func.count(RecoverySchedule.id))
            .filter(
                RecoverySchedule.status == "scheduled",
                RecoverySchedule.due_at <= now_naive,
            )
            .scalar()
            or 0
        )
        out["running_stale_count"] = int(
            db.session.query(func.count(RecoverySchedule.id))
            .filter(
                RecoverySchedule.status == "running",
                RecoverySchedule.updated_at < cutoff_naive,
            )
            .scalar()
            or 0
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["ok"] = False
        out["database_error"] = type(exc).__name__
    return out


__all__ = [
    "SchedulerDeepHealthDenied",
    "assert_deep_health_allowed",
    "build_scheduler_deep_health_snapshot",
    "reset_deep_health_rate_limit_for_tests",
]
