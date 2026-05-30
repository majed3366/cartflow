# -*- coding: utf-8 -*-
"""
Process role for recovery scheduling ownership (api vs scheduler).

Separates HTTP API serving from RecoverySchedule resume/due-scanner/delay dispatch
without Redis/Celery. When ``CARTFLOW_PROCESS_ROLE`` is unset, legacy behavior is
unchanged (single-process owns everything).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule

log = logging.getLogger("cartflow")

ENV_PROCESS_ROLE = "CARTFLOW_PROCESS_ROLE"

ProcessRole = Literal["unset", "api", "scheduler", "legacy"]

_VALID_ROLES = frozenset({"api", "scheduler"})


def resolve_process_role() -> ProcessRole:
    raw = (os.getenv(ENV_PROCESS_ROLE) or "").strip().lower()
    if not raw:
        return "unset"
    if raw in _VALID_ROLES:
        return raw  # type: ignore[return-value]
    log.warning("[SCHEDULER OWNER] unknown %s=%r — treating as unset", ENV_PROCESS_ROLE, raw)
    return "unset"


def is_api_process_role() -> bool:
    return resolve_process_role() == "api"


def is_scheduler_process_role() -> bool:
    return resolve_process_role() == "scheduler"


def process_role_effective_resume_enabled(*, force: bool = False) -> bool:
    """Whether this process may run startup resume scan."""
    if force:
        return True
    role = resolve_process_role()
    if role == "api":
        return False
    from services.recovery_scheduler_guardrails import (  # noqa: PLC0415
        is_recovery_resume_on_startup_enabled,
    )

    return is_recovery_resume_on_startup_enabled(force=False)


def process_role_effective_due_scanner_enabled() -> bool:
    """Whether this process may run the DB due scanner loop."""
    if is_api_process_role():
        return False
    try:
        from services.recovery_db_due_scanner_loop import (  # noqa: PLC0415
            is_db_due_scanner_loop_enabled,
        )

        return bool(is_db_due_scanner_loop_enabled())
    except Exception:  # noqa: BLE001
        return False


def process_role_may_spawn_delay_dispatch() -> bool:
    """Whether this process may spawn in-process delay dispatch tasks."""
    role = resolve_process_role()
    if role == "api":
        return False
    return True


def due_scanner_limit_for_health() -> int:
    try:
        from services.recovery_db_due_scanner_loop import (  # noqa: PLC0415
            db_due_scanner_loop_limit,
        )

        return int(db_due_scanner_loop_limit())
    except Exception:  # noqa: BLE001
        return 25


def _print_line(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass


def log_scheduler_owner_at_startup() -> dict[str, Any]:
    """
    Emit ``[SCHEDULER OWNER]`` once per process startup.

    Examples:
      role=api resume_enabled=false due_scanner=false
      role=scheduler resume_enabled=true due_scanner=true
      role=unset resume_enabled=true due_scanner=false  (legacy)
    """
    role = resolve_process_role()
    resume_on = process_role_effective_resume_enabled()
    scanner_on = process_role_effective_due_scanner_enabled()
    spawn_on = process_role_may_spawn_delay_dispatch()
    role_label = role if role != "unset" else "unset"

    snap = {
        "role": role_label,
        "resume_enabled": resume_on,
        "due_scanner_enabled": scanner_on,
        "delay_dispatch_enabled": spawn_on,
        "due_scanner_limit": due_scanner_limit_for_health(),
    }

    _print_line("[SCHEDULER OWNER]")
    _print_line(
        f"role={role_label} "
        f"resume_enabled={'true' if resume_on else 'false'} "
        f"due_scanner={'true' if scanner_on else 'false'}"
    )

    try:
        log.info(
            "[SCHEDULER OWNER] role=%s resume_enabled=%s due_scanner=%s delay_dispatch=%s",
            role_label,
            resume_on,
            scanner_on,
            spawn_on,
        )
    except Exception:  # noqa: BLE001
        pass

    return snap


def log_delay_dispatch_skipped(*, source: str, schedule_id: Optional[int] = None) -> None:
    if not is_api_process_role():
        return
    sid = int(schedule_id) if schedule_id is not None else None
    _print_line("[SCHEDULER OWNER]")
    _print_line(
        f"delay_dispatch_skipped=true role=api source={(source or '-')[:64]}"
        + (f" schedule_id={sid}" if sid is not None else "")
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _running_stale_threshold_seconds() -> int:
    try:
        from services.recovery_restart_survival import _running_stale_seconds  # noqa: PLC0415

        return int(_running_stale_seconds())
    except Exception:  # noqa: BLE001
        return 600


def build_scheduler_health_snapshot() -> dict[str, Any]:
    """Read-only fields for ``GET /health/scheduler``."""
    role = resolve_process_role()
    role_label = role if role != "unset" else "unset"
    resume_on = process_role_effective_resume_enabled()
    scanner_on = process_role_effective_due_scanner_enabled()
    limit = due_scanner_limit_for_health()

    overdue_scheduled_count = 0
    running_stale_count = 0
    db_error: Optional[str] = None

    try:
        db.create_all()
        now_naive = _utc_now().replace(tzinfo=None)
        cutoff_naive = (_utc_now() - timedelta(seconds=_running_stale_threshold_seconds())).replace(
            tzinfo=None
        )
        overdue_scheduled_count = int(
            db.session.query(func.count(RecoverySchedule.id))
            .filter(
                RecoverySchedule.status == "scheduled",
                RecoverySchedule.due_at <= now_naive,
            )
            .scalar()
            or 0
        )
        running_stale_count = int(
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
        db_error = str(exc)[:200]

    out: dict[str, Any] = {
        "ok": db_error is None,
        "role": role_label,
        "resume_enabled": resume_on,
        "due_scanner_enabled": scanner_on,
        "due_scanner_limit": limit,
        "delay_dispatch_enabled": process_role_may_spawn_delay_dispatch(),
        "overdue_scheduled_count": overdue_scheduled_count,
        "running_stale_count": running_stale_count,
    }
    if db_error:
        out["database_error"] = db_error
    return out


__all__ = [
    "ENV_PROCESS_ROLE",
    "build_scheduler_health_snapshot",
    "due_scanner_limit_for_health",
    "is_api_process_role",
    "is_scheduler_process_role",
    "log_delay_dispatch_skipped",
    "log_scheduler_owner_at_startup",
    "process_role_effective_due_scanner_enabled",
    "process_role_effective_resume_enabled",
    "process_role_may_spawn_delay_dispatch",
    "resolve_process_role",
]
