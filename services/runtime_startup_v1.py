# -*- coding: utf-8 -*-
"""
Application startup orchestration — Production Reliability Hardening v2.

Centralizes role-gated background loop startup with explicit structured logs.
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("cartflow")


def _print_line(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass


def log_runtime_startup_banner() -> dict[str, Any]:
    """
    Emit ``[RUNTIME STARTUP]`` lines showing role and which background loops run.

    Called once per process before any scheduler driver starts.
    """
    from services.recovery_process_role_v1 import (
        due_scanner_limit_for_health,
        evaluate_scheduler_ownership_policy,
        log_scheduler_owner_at_startup,
    )
    from services.recovery_db_due_scanner_loop import (
        db_due_scanner_loop_interval_seconds,
        is_db_due_scanner_loop_enabled,
    )
    from services.recovery_scheduler_guardrails import (
        resolve_recovery_resume_on_startup_config,
    )

    policy = evaluate_scheduler_ownership_policy(force=False)
    role = str(policy.get("role") or "unset")
    resume_cfg = resolve_recovery_resume_on_startup_config()
    resume_env = bool(resume_cfg.get("enabled"))
    scanner_env = bool(is_db_due_scanner_loop_enabled())

    may_resume = bool(policy.get("may_resume"))
    may_scan = bool(policy.get("may_due_scan"))
    may_delay = bool(policy.get("may_delay_dispatch"))

    snap: dict[str, Any] = {
        "role": role,
        "resume_env": resume_env,
        "scanner_env": scanner_env,
        "may_resume": may_resume,
        "may_due_scan": may_scan,
        "may_delay_dispatch": may_delay,
        "compliance": policy.get("compliance"),
        "block_reason": policy.get("block_reason"),
        "production_like": policy.get("production_like"),
    }

    _print_line("[RUNTIME STARTUP]")
    _print_line(f"process_role={role}")
    _print_line(
        f"resume_scan={'enabled' if may_resume else 'disabled'} "
        f"(env={('true' if resume_env else 'false')})"
    )
    _print_line(
        f"db_due_scanner_loop={'enabled' if may_scan else 'disabled'} "
        f"(env={('true' if scanner_env else 'false')} "
        f"interval_s={db_due_scanner_loop_interval_seconds()} "
        f"limit={due_scanner_limit_for_health()})"
    )
    _print_line(
        f"delay_dispatch={'enabled' if may_delay else 'disabled'}"
    )
    try:
        from services.dashboard_snapshot_builder_v1 import dashboard_snapshot_builder_enabled  # noqa: PLC0415
        from services.dashboard_snapshot_loop_v1 import dashboard_snapshot_loop_interval_seconds  # noqa: PLC0415

        builder_on = dashboard_snapshot_builder_enabled()
        _print_line(
            f"dashboard_snapshot_loop={'enabled' if builder_on else 'disabled'} "
            f"interval_s={dashboard_snapshot_loop_interval_seconds()}"
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from services.dashboard_snapshot_archive_v1 import (  # noqa: PLC0415
            dashboard_snapshot_archive_enabled,
        )
        from services.dashboard_snapshot_archive_loop_v1 import (  # noqa: PLC0415
            dashboard_snapshot_archive_loop_interval_seconds,
        )

        archive_on = dashboard_snapshot_archive_enabled()
        _print_line(
            f"dashboard_snapshot_archive_loop={'enabled' if archive_on else 'disabled'} "
            f"interval_s={dashboard_snapshot_archive_loop_interval_seconds()}"
        )
    except Exception:  # noqa: BLE001
        pass
    if policy.get("block_reason"):
        _print_line(f"ownership_block_reason={policy.get('block_reason')}")
    if policy.get("compliance") == "misconfigured":
        _print_line("compliance=misconfigured scheduler_drivers_blocked=true")

    log_scheduler_owner_at_startup()
    return snap


async def run_scheduler_drivers_at_startup() -> dict[str, Any]:
    """
    Role-gated startup drivers: resume scan + DB due scanner loop.

    API role: both skipped (policy fail-closed). Scheduler role: env-controlled.
    """
    from services.recovery_process_role_v1 import (
        evaluate_scheduler_ownership_policy,
        process_role_effective_resume_enabled,
    )

    policy = evaluate_scheduler_ownership_policy(force=False)
    out: dict[str, Any] = {
        "resume_scan_ran": False,
        "resume_scan_result": None,
        "scanner_loop_started": False,
        "snapshot_loop_started": False,
        "archive_loop_started": False,
    }

    if process_role_effective_resume_enabled():
        try:
            from services.recovery_restart_survival import run_recovery_resume_scan_async

            resume_out = await run_recovery_resume_scan_async(max_dispatch=25)
            out["resume_scan_ran"] = True
            out["resume_scan_result"] = resume_out
            if resume_out.get("dispatched"):
                _print_line(
                    f"[RUNTIME STARTUP] resume_scan_dispatched={resume_out.get('dispatched')}"
                )
                log.info(
                    "[RUNTIME STARTUP] resume_scan dispatched=%s",
                    resume_out.get("dispatched"),
                )
        except Exception as exc:  # noqa: BLE001
            _print_line(f"[RUNTIME STARTUP] resume_scan_error={str(exc)[:120]}")
            log.warning("startup recovery resume scan skipped: %s", exc)
            out["resume_scan_error"] = str(exc)[:200]
    else:
        reason = str(policy.get("block_reason") or "ownership_blocked")
        _print_line(f"[RUNTIME STARTUP] resume_scan_skipped reason={reason}")
        log.info("[RUNTIME STARTUP] resume_scan_skipped reason=%s", reason)

    if policy.get("may_due_scan"):
        try:
            from services.recovery_db_due_scanner_loop import (
                start_db_due_recovery_scanner_loop,
            )
            from services.db_due_scanner_health import (
                refresh_db_due_scanner_health_observability,
            )

            start_db_due_recovery_scanner_loop()
            refresh_db_due_scanner_health_observability()
            out["scanner_loop_started"] = True
            _print_line("[RUNTIME STARTUP] db_due_scanner_loop_started=true")
        except Exception as exc:  # noqa: BLE001
            _print_line(f"[RUNTIME STARTUP] db_due_scanner_loop_error={str(exc)[:120]}")
            log.warning("startup db due scanner loop skipped: %s", exc)
            out["scanner_loop_error"] = str(exc)[:200]
    else:
        reason = str(policy.get("block_reason") or "ownership_blocked")
        _print_line(f"[RUNTIME STARTUP] db_due_scanner_loop_skipped reason={reason}")
        log.info("[RUNTIME STARTUP] db_due_scanner_loop_skipped reason=%s", reason)

    try:
        from services.dashboard_snapshot_builder_v1 import dashboard_snapshot_builder_enabled  # noqa: PLC0415
        from services.dashboard_snapshot_loop_v1 import start_dashboard_snapshot_builder_loop  # noqa: PLC0415

        if dashboard_snapshot_builder_enabled():
            start_dashboard_snapshot_builder_loop()
            out["snapshot_loop_started"] = True
            _print_line("[RUNTIME STARTUP] dashboard_snapshot_loop_started=true")
        else:
            reason = str(policy.get("block_reason") or "builder_disabled")
            _print_line(f"[RUNTIME STARTUP] dashboard_snapshot_loop_skipped reason={reason}")
    except Exception as exc:  # noqa: BLE001
        _print_line(f"[RUNTIME STARTUP] dashboard_snapshot_loop_error={str(exc)[:120]}")
        log.warning("startup dashboard snapshot loop skipped: %s", exc)
        out["snapshot_loop_error"] = str(exc)[:200]

    try:
        from services.dashboard_snapshot_archive_v1 import (  # noqa: PLC0415
            dashboard_snapshot_archive_enabled,
        )
        from services.dashboard_snapshot_archive_loop_v1 import (  # noqa: PLC0415
            start_dashboard_snapshot_archive_loop,
        )

        if dashboard_snapshot_archive_enabled():
            start_dashboard_snapshot_archive_loop()
            out["archive_loop_started"] = True
            _print_line("[RUNTIME STARTUP] dashboard_snapshot_archive_loop_started=true")
        else:
            _print_line("[RUNTIME STARTUP] dashboard_snapshot_archive_loop_skipped reason=archive_disabled")
    except Exception as exc:  # noqa: BLE001
        _print_line(f"[RUNTIME STARTUP] dashboard_snapshot_archive_loop_error={str(exc)[:120]}")
        log.warning("startup dashboard snapshot archive loop skipped: %s", exc)
        out["archive_loop_error"] = str(exc)[:200]

    return out


__all__ = [
    "log_runtime_startup_banner",
    "run_scheduler_drivers_at_startup",
]
