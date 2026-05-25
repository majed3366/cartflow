# -*- coding: utf-8 -*-
"""
Recovery scheduler ownership guardrails v1 — env + startup logs only.

Does not change delay, claim, or send paths. Use ``CARTFLOW_RECOVERY_RESUME_ON_STARTUP``
so only one process runs startup resume scan until a real queue/lease exists.
"""
from __future__ import annotations

import logging
import os
import socket
from typing import Any, TypedDict

log = logging.getLogger("cartflow")

ENV_RECOVERY_RESUME_ON_STARTUP = "CARTFLOW_RECOVERY_RESUME_ON_STARTUP"

# Current production default: single process / one owner runs resume on boot.
_DEFAULT_RESUME_ON_STARTUP_ENABLED = True

_DISABLED_VALUES = frozenset({"0", "false", "no", "off"})

_MULTI_WORKER_ENV_KEYS = (
    "WEB_CONCURRENCY",
    "UVICORN_WORKERS",
    "CARTFLOW_UVICORN_WORKERS",
    "WORKERS",
)


class RecoverySchedulerOwnershipConfig(TypedDict):
    enabled: bool
    reason: str
    env_set: bool
    env_raw: str


class SchedulerProcessIdentity(TypedDict):
    process_id: str
    instance: str


def _env_raw() -> str:
    return (os.getenv(ENV_RECOVERY_RESUME_ON_STARTUP) or "").strip()


def resolve_recovery_resume_on_startup_config() -> RecoverySchedulerOwnershipConfig:
    """
    Interpret ``CARTFLOW_RECOVERY_RESUME_ON_STARTUP``.

    - Unset → enabled (``reason=default``) — matches legacy single-worker production.
    - ``0`` / ``false`` / ``no`` / ``off`` → disabled (``reason=env``).
    - Any other non-empty value → enabled (``reason=env``).
    """
    raw = _env_raw()
    if not raw:
        return {
            "enabled": _DEFAULT_RESUME_ON_STARTUP_ENABLED,
            "reason": "default",
            "env_set": False,
            "env_raw": "",
        }
    enabled = raw.lower() not in _DISABLED_VALUES
    return {
        "enabled": enabled,
        "reason": "env",
        "env_set": True,
        "env_raw": raw,
    }


def resolve_scheduler_process_identity() -> SchedulerProcessIdentity:
    """Stable process/instance labels for ownership logs and health."""
    instance = (
        (os.getenv("CARTFLOW_INSTANCE_ID") or "").strip()
        or (os.getenv("RENDER_INSTANCE_ID") or "").strip()
        or (os.getenv("HOSTNAME") or "").strip()
        or (os.getenv("COMPUTERNAME") or "").strip()
        or socket.gethostname()
        or "unknown"
    )
    return {
        "process_id": str(os.getpid()),
        "instance": instance[:128],
    }


def _parse_worker_count_env(name: str) -> int | None:
    raw = (os.getenv(name) or "").strip()
    if raw.isdigit():
        return int(raw)
    return None


def is_production_like_runtime() -> bool:
    """True when not explicit development (matches main production default)."""
    env = (os.getenv("ENV") or "").strip().lower()
    if env == "development":
        return False
    if env in ("production", "prod", "staging", "preview"):
        return True
    return not env or env != "development"


def detect_multi_worker_startup_risk() -> tuple[bool, str]:
    """
    Heuristic: common process-manager worker counts > 1.

    Returns (risk_detected, detail_for_logs).
    """
    for name in _MULTI_WORKER_ENV_KEYS:
        n = _parse_worker_count_env(name)
        if n is not None and n > 1:
            return True, f"{name}={n}"
    return False, ""


def should_emit_scheduler_multi_worker_risk(*, enabled: bool) -> tuple[bool, str]:
    """Whether to log ``[RECOVERY SCHEDULER RISK]`` (warn only, never blocks)."""
    if not enabled:
        return False, ""
    multi, detail = detect_multi_worker_startup_risk()
    if multi:
        return True, detail
    if is_production_like_runtime():
        for name in _MULTI_WORKER_ENV_KEYS:
            if (os.getenv(name) or "").strip():
                n = _parse_worker_count_env(name)
                if n == 1:
                    return True, f"{name}=1_production_fleet_check_replicas"
    return False, ""


def is_recovery_resume_on_startup_enabled(*, force: bool = False) -> bool:
    """Whether this process may run startup recovery resume scan."""
    if force:
        return True
    return bool(resolve_recovery_resume_on_startup_config()["enabled"])


def build_scheduler_owner_health_fields() -> dict[str, Any]:
    """Read-only fields for ``GET /dev/recovery-health``."""
    cfg = resolve_recovery_resume_on_startup_config()
    ident = resolve_scheduler_process_identity()
    multi, multi_detail = detect_multi_worker_startup_risk()
    risk, risk_detail = should_emit_scheduler_multi_worker_risk(enabled=cfg["enabled"])
    return {
        "scheduler_owner_mode": "owner" if cfg["enabled"] else "api_replica",
        "resume_on_startup_enabled": bool(cfg["enabled"]),
        "resume_on_startup_reason": cfg["reason"],
        "resume_on_startup_env_set": bool(cfg["env_set"]),
        "resume_on_startup_env_raw": (cfg["env_raw"] or None),
        "process_id": ident["process_id"],
        "instance": ident["instance"],
        "production_like_runtime": is_production_like_runtime(),
        "multi_worker_signal": multi,
        "multi_worker_detail": multi_detail or None,
        "scheduler_risk_advisory": risk,
        "scheduler_risk_detail": risk_detail or None,
        "recommended_api_replicas": (
            "CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0"
            if cfg["enabled"]
            else None
        ),
    }


def _print_startup_line(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass


def log_recovery_scheduler_risk_if_needed(*, enabled: bool) -> None:
    """Emit ``[RECOVERY SCHEDULER RISK]`` when resume enabled + unsafe fleet hints."""
    risk, detail = should_emit_scheduler_multi_worker_risk(enabled=enabled)
    if not risk:
        return
    _print_startup_line("[RECOVERY SCHEDULER RISK]")
    _print_startup_line("risk=multi_worker_resume")
    _print_startup_line(
        "action=set_CARTFLOW_RECOVERY_RESUME_ON_STARTUP_0_on_api_replicas"
    )
    if detail:
        _print_startup_line(f"detail={detail[:120]}")
    try:
        log.warning(
            "[RECOVERY SCHEDULER RISK] risk=multi_worker_resume detail=%s",
            detail or "-",
        )
    except Exception:  # noqa: BLE001
        pass


def log_recovery_scheduler_ownership_at_startup() -> RecoverySchedulerOwnershipConfig:
    """
    Emit ownership mode once per process startup.

    Logs:
      [RECOVERY SCHEDULER OWNER] enabled=… reason=… process_id=… instance=…
      [RECOVERY WORKER MODE] single_scheduler_expected=true (when enabled)
      [RECOVERY SCHEDULER RISK] (when enabled + multi-worker / production hints)
    """
    cfg = resolve_recovery_resume_on_startup_config()
    ident = resolve_scheduler_process_identity()
    enabled = cfg["enabled"]

    _print_startup_line("[RECOVERY SCHEDULER OWNER]")
    _print_startup_line(f"enabled={'true' if enabled else 'false'}")
    _print_startup_line(f"reason={cfg['reason']}")
    _print_startup_line(f"process_id={ident['process_id']}")
    _print_startup_line(f"instance={ident['instance']}")
    if cfg["env_set"]:
        _print_startup_line(f"{ENV_RECOVERY_RESUME_ON_STARTUP}={cfg['env_raw'][:64]}")
    else:
        _print_startup_line(f"{ENV_RECOVERY_RESUME_ON_STARTUP}=(unset)")

    if enabled:
        _print_startup_line("[RECOVERY WORKER MODE]")
        _print_startup_line("single_scheduler_expected=true")

    log_recovery_scheduler_risk_if_needed(enabled=enabled)

    try:
        log.info(
            "[RECOVERY SCHEDULER OWNER] enabled=%s reason=%s process_id=%s instance=%s",
            enabled,
            cfg["reason"],
            ident["process_id"],
            ident["instance"],
        )
    except Exception:  # noqa: BLE001
        pass

    return cfg


__all__ = [
    "ENV_RECOVERY_RESUME_ON_STARTUP",
    "build_scheduler_owner_health_fields",
    "detect_multi_worker_startup_risk",
    "is_production_like_runtime",
    "is_recovery_resume_on_startup_enabled",
    "log_recovery_scheduler_ownership_at_startup",
    "log_recovery_scheduler_risk_if_needed",
    "resolve_recovery_resume_on_startup_config",
    "resolve_scheduler_process_identity",
    "should_emit_scheduler_multi_worker_risk",
]
