# -*- coding: utf-8 -*-
"""
Process role for recovery scheduling ownership (api vs scheduler).

Separates HTTP API serving from RecoverySchedule resume/due-scanner/delay dispatch
without Redis/Celery. Production-like runtimes require an explicit role; development
may use legacy unset single-process behavior.
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

ProcessRole = Literal["unset", "api", "scheduler", "unknown"]

_VALID_ROLES = frozenset({"api", "scheduler"})

COMPLIANCE_OK = "ok"
COMPLIANCE_MISCONFIGURED = "misconfigured"


def _resolve_role_label() -> str:
    raw = (os.getenv(ENV_PROCESS_ROLE) or "").strip().lower()
    if not raw:
        return "unset"
    if raw in _VALID_ROLES:
        return raw  # type: ignore[return-value]
    log.warning(
        "[SCHEDULER OWNER] unknown %s=%r — scheduler drivers blocked",
        ENV_PROCESS_ROLE,
        raw,
    )
    return "unknown"


def resolve_process_role() -> ProcessRole:
    return _resolve_role_label()  # type: ignore[return-value]


def is_api_process_role() -> bool:
    return resolve_process_role() == "api"


def is_scheduler_process_role() -> bool:
    return resolve_process_role() == "scheduler"


def evaluate_scheduler_ownership_policy(*, force: bool = False) -> dict[str, Any]:
    """
    Single source of truth for scheduler driver ownership.

    Fail closed on policy evaluation errors and on unset/unknown role in production-like
    runtimes.
    """
    production_like = False
    try:
        from services.recovery_scheduler_guardrails import (  # noqa: PLC0415
            is_production_like_runtime,
            resolve_recovery_resume_on_startup_config,
        )

        production_like = is_production_like_runtime()
        role = _resolve_role_label()

        if force:
            return {
                "role": role,
                "may_resume": True,
                "may_due_scan": True,
                "may_delay_dispatch": True,
                "compliance": COMPLIANCE_OK,
                "block_reason": None,
                "fail_closed": production_like,
                "production_like": production_like,
                "policy_error": None,
            }

        resume_cfg = resolve_recovery_resume_on_startup_config()
        resume_env_enabled = bool(resume_cfg["enabled"])

        due_scan_env_enabled = False
        try:
            from services.recovery_db_due_scanner_loop import (  # noqa: PLC0415
                is_db_due_scanner_loop_enabled,
            )

            due_scan_env_enabled = bool(is_db_due_scanner_loop_enabled())
        except Exception:  # noqa: BLE001
            due_scan_env_enabled = False

        if production_like:
            if role == "scheduler":
                block_reason = None
                if not resume_env_enabled:
                    block_reason = "resume_on_startup_disabled"
                return {
                    "role": role,
                    "may_resume": resume_env_enabled,
                    "may_due_scan": due_scan_env_enabled,
                    "may_delay_dispatch": True,
                    "compliance": COMPLIANCE_OK,
                    "block_reason": block_reason,
                    "fail_closed": True,
                    "production_like": True,
                    "policy_error": None,
                }
            if role == "api":
                return {
                    "role": role,
                    "may_resume": False,
                    "may_due_scan": False,
                    "may_delay_dispatch": False,
                    "compliance": COMPLIANCE_OK,
                    "block_reason": "role_api",
                    "fail_closed": True,
                    "production_like": True,
                    "policy_error": None,
                }
            block_reason = (
                "role_unknown_production"
                if role == "unknown"
                else "role_unset_production"
            )
            return {
                "role": role,
                "may_resume": False,
                "may_due_scan": False,
                "may_delay_dispatch": False,
                "compliance": COMPLIANCE_MISCONFIGURED,
                "block_reason": block_reason,
                "fail_closed": True,
                "production_like": True,
                "policy_error": None,
            }

        if role == "api":
            return {
                "role": role,
                "may_resume": False,
                "may_due_scan": False,
                "may_delay_dispatch": False,
                "compliance": COMPLIANCE_OK,
                "block_reason": "role_api",
                "fail_closed": False,
                "production_like": False,
                "policy_error": None,
            }
        if role == "scheduler":
            block_reason = None
            if not resume_env_enabled:
                block_reason = "resume_on_startup_disabled"
            return {
                "role": role,
                "may_resume": resume_env_enabled,
                "may_due_scan": due_scan_env_enabled,
                "may_delay_dispatch": True,
                "compliance": COMPLIANCE_OK,
                "block_reason": block_reason,
                "fail_closed": False,
                "production_like": False,
                "policy_error": None,
            }
        if role == "unknown":
            return {
                "role": role,
                "may_resume": False,
                "may_due_scan": False,
                "may_delay_dispatch": False,
                "compliance": COMPLIANCE_MISCONFIGURED,
                "block_reason": "role_unknown",
                "fail_closed": False,
                "production_like": False,
                "policy_error": None,
            }
        block_reason = None
        if not resume_env_enabled:
            block_reason = "resume_on_startup_disabled"
        return {
            "role": "unset",
            "may_resume": resume_env_enabled,
            "may_due_scan": due_scan_env_enabled,
            "may_delay_dispatch": True,
            "compliance": COMPLIANCE_OK,
            "block_reason": block_reason,
            "fail_closed": False,
            "production_like": False,
            "policy_error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "role": "unknown",
            "may_resume": False,
            "may_due_scan": False,
            "may_delay_dispatch": False,
            "compliance": COMPLIANCE_MISCONFIGURED,
            "block_reason": "policy_error",
            "fail_closed": True,
            "production_like": production_like,
            "policy_error": str(exc)[:200],
        }


def process_role_effective_resume_enabled(*, force: bool = False) -> bool:
    """Whether this process may run startup resume scan."""
    return bool(
        evaluate_scheduler_ownership_policy(force=force).get("may_resume", False)
    )


def process_role_effective_due_scanner_enabled() -> bool:
    """Whether this process may run the DB due scanner loop."""
    return bool(
        evaluate_scheduler_ownership_policy(force=False).get("may_due_scan", False)
    )


def process_role_may_spawn_delay_dispatch() -> bool:
    """Whether this process may spawn in-process delay dispatch tasks."""
    return bool(
        evaluate_scheduler_ownership_policy(force=False).get("may_delay_dispatch", False)
    )


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
      role=unset resume_enabled=true due_scanner=false  (legacy dev)
    """
    policy = evaluate_scheduler_ownership_policy(force=False)
    role_label = str(policy.get("role") or "unset")
    resume_on = bool(policy.get("may_resume"))
    scanner_on = bool(policy.get("may_due_scan"))
    spawn_on = bool(policy.get("may_delay_dispatch"))

    snap = {
        "role": role_label,
        "resume_enabled": resume_on,
        "due_scanner_enabled": scanner_on,
        "delay_dispatch_enabled": spawn_on,
        "due_scanner_limit": due_scanner_limit_for_health(),
        "compliance": policy.get("compliance"),
        "block_reason": policy.get("block_reason"),
    }

    _print_line("[SCHEDULER OWNER]")
    _print_line(
        f"role={role_label} "
        f"resume_enabled={'true' if resume_on else 'false'} "
        f"due_scanner={'true' if scanner_on else 'false'} "
        f"compliance={policy.get('compliance')}"
    )
    if policy.get("block_reason"):
        _print_line(f"block_reason={policy.get('block_reason')}")

    try:
        log.info(
            "[SCHEDULER OWNER] role=%s resume_enabled=%s due_scanner=%s "
            "delay_dispatch=%s compliance=%s block_reason=%s",
            role_label,
            resume_on,
            scanner_on,
            spawn_on,
            policy.get("compliance"),
            policy.get("block_reason"),
        )
    except Exception:  # noqa: BLE001
        pass

    return snap


def log_delay_dispatch_blocked(
    *,
    source: str,
    schedule_id: Optional[int] = None,
    block_reason: Optional[str] = None,
) -> None:
    sid = int(schedule_id) if schedule_id is not None else None
    reason = (block_reason or "ownership_blocked").strip()[:128]
    _print_line("[SCHEDULER OWNER]")
    _print_line(
        f"delay_dispatch_blocked=true block_reason={reason} "
        f"source={(source or '-')[:64]}"
        + (f" schedule_id={sid}" if sid is not None else "")
    )
    try:
        log.info(
            "[SCHEDULER OWNER] delay_dispatch_blocked block_reason=%s source=%s schedule_id=%s",
            reason,
            (source or "-")[:64],
            sid,
        )
    except Exception:  # noqa: BLE001
        pass


def log_delay_dispatch_skipped(*, source: str, schedule_id: Optional[int] = None) -> None:
    """Backward-compatible alias for API-role skip logging."""
    log_delay_dispatch_blocked(
        source=source,
        schedule_id=schedule_id,
        block_reason="role_api",
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
    policy = evaluate_scheduler_ownership_policy(force=False)
    role_label = str(policy.get("role") or "unset")
    resume_on = bool(policy.get("may_resume"))
    scanner_on = bool(policy.get("may_due_scan"))
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

    scheduler_ownership = {
        "role": role_label,
        "compliance": policy.get("compliance"),
        "block_reason": policy.get("block_reason"),
        "may_resume": resume_on,
        "may_due_scan": scanner_on,
        "may_delay_dispatch": bool(policy.get("may_delay_dispatch")),
        "production_like": bool(policy.get("production_like")),
        "fail_closed": bool(policy.get("fail_closed")),
        "policy_error": policy.get("policy_error"),
    }

    from services.scheduler_ownership_diagnosis_v1 import build_ownership_diagnosis

    ownership_diagnosis = build_ownership_diagnosis(
        scheduler_ownership=scheduler_ownership,
        overdue_scheduled_count=overdue_scheduled_count,
        running_stale_count=running_stale_count,
        resume_enabled=resume_on,
        due_scanner_enabled=scanner_on,
        delay_dispatch_enabled=bool(policy.get("may_delay_dispatch")),
    )

    ok = db_error is None and policy.get("compliance") != COMPLIANCE_MISCONFIGURED
    if policy.get("policy_error"):
        ok = False

    out: dict[str, Any] = {
        "ok": ok,
        "role": role_label,
        "resume_enabled": resume_on,
        "due_scanner_enabled": scanner_on,
        "due_scanner_limit": limit,
        "delay_dispatch_enabled": bool(policy.get("may_delay_dispatch")),
        "overdue_scheduled_count": overdue_scheduled_count,
        "running_stale_count": running_stale_count,
        "scheduler_ownership": scheduler_ownership,
        "ownership_diagnosis": ownership_diagnosis,
    }
    if db_error:
        out["database_error"] = db_error
    try:
        from services.db_pool_diagnostics import build_db_pool_health_snapshot  # noqa: PLC0415

        out["db_pool"] = build_db_pool_health_snapshot()
    except Exception as exc:  # noqa: BLE001
        out["db_pool"] = {"available": False, "error": str(exc)[:200], "exhausted": False}
    return out


__all__ = [
    "COMPLIANCE_MISCONFIGURED",
    "COMPLIANCE_OK",
    "ENV_PROCESS_ROLE",
    "build_scheduler_health_snapshot",
    "due_scanner_limit_for_health",
    "evaluate_scheduler_ownership_policy",
    "is_api_process_role",
    "is_scheduler_process_role",
    "log_delay_dispatch_blocked",
    "log_delay_dispatch_skipped",
    "log_scheduler_owner_at_startup",
    "process_role_effective_due_scanner_enabled",
    "process_role_effective_resume_enabled",
    "process_role_may_spawn_delay_dispatch",
    "resolve_process_role",
]
