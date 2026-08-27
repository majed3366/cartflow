# -*- coding: utf-8 -*-
"""Bounded sleep, exponential backoff, and Postgres single-instance lock."""
from __future__ import annotations

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

_MIN_SLEEP_SECONDS = 5.0
_MAX_BACKOFF_SECONDS = 300.0
_ADVISORY_LOCK_KEY = 814_229_017

_failure_streak = 0
_lock_held = False


class SchedulerInstanceLockError(RuntimeError):
    """Another Scheduler instance holds the Postgres advisory lock."""


def reset_cycle_guard_for_tests() -> None:
    global _failure_streak, _lock_held
    _failure_streak = 0
    _lock_held = False


def min_sleep_seconds() -> float:
    return _MIN_SLEEP_SECONDS


def record_cycle_ok() -> None:
    global _failure_streak
    _failure_streak = 0


def record_cycle_error() -> None:
    global _failure_streak
    _failure_streak += 1


def next_sleep_seconds(base_interval: float) -> float:
    """Never zero. Back off after consecutive failures."""
    try:
        base = float(base_interval)
    except (TypeError, ValueError):
        base = _MIN_SLEEP_SECONDS
    base = max(_MIN_SLEEP_SECONDS, base)
    if _failure_streak <= 0:
        return base
    delay = min(_MAX_BACKOFF_SECONDS, base * (2 ** min(_failure_streak, 6)))
    return max(_MIN_SLEEP_SECONDS, delay)


def try_acquire_scheduler_instance_lock() -> dict[str, Any]:
    """
    Postgres ``pg_try_advisory_lock``. SQLite / missing engine → local-only (ok).
    """
    global _lock_held
    if (os.getenv("CARTFLOW_SCHEDULER_SKIP_INSTANCE_LOCK") or "").strip() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return {"acquired": True, "backend": "skipped"}
    try:
        from extensions import db  # noqa: PLC0415

        url = str(db.engine.url)
    except Exception:  # noqa: BLE001
        return {"acquired": True, "backend": "no_engine"}
    if url.startswith("sqlite"):
        return {"acquired": True, "backend": "sqlite"}
    try:
        row = db.session.execute(
            text("SELECT pg_try_advisory_lock(:k)"),
            {"k": _ADVISORY_LOCK_KEY},
        ).scalar()
        db.session.commit()
        acquired = bool(row)
        _lock_held = acquired
        if not acquired:
            raise SchedulerInstanceLockError("scheduler instance lock not acquired")
        return {"acquired": True, "backend": "postgres"}
    except SchedulerInstanceLockError:
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        return {"acquired": True, "backend": "lock_unavailable"}


def release_scheduler_instance_lock() -> None:
    global _lock_held
    if not _lock_held:
        return
    try:
        from extensions import db  # noqa: PLC0415

        db.session.execute(
            text("SELECT pg_advisory_unlock(:k)"),
            {"k": _ADVISORY_LOCK_KEY},
        )
        db.session.commit()
    except Exception:  # noqa: BLE001
        try:
            from extensions import db  # noqa: PLC0415

            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
    finally:
        _lock_held = False


__all__ = [
    "SchedulerInstanceLockError",
    "min_sleep_seconds",
    "next_sleep_seconds",
    "record_cycle_error",
    "record_cycle_ok",
    "release_scheduler_instance_lock",
    "reset_cycle_guard_for_tests",
    "try_acquire_scheduler_instance_lock",
]
