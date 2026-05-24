# -*- coding: utf-8 -*-
"""
Recovery scheduler ownership guardrails v1 — env + startup logs only.

Does not change delay, claim, or send paths. Use ``CARTFLOW_RECOVERY_RESUME_ON_STARTUP``
so only one process runs startup resume scan until a real queue/lease exists.
"""
from __future__ import annotations

import logging
import os
from typing import Any, TypedDict

log = logging.getLogger("cartflow")

ENV_RECOVERY_RESUME_ON_STARTUP = "CARTFLOW_RECOVERY_RESUME_ON_STARTUP"

# Current production default: single process / one owner runs resume on boot.
_DEFAULT_RESUME_ON_STARTUP_ENABLED = True

_DISABLED_VALUES = frozenset({"0", "false", "no", "off"})


class RecoverySchedulerOwnershipConfig(TypedDict):
    enabled: bool
    reason: str
    env_set: bool
    env_raw: str


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


def is_recovery_resume_on_startup_enabled(*, force: bool = False) -> bool:
    """Whether this process may run startup recovery resume scan."""
    if force:
        return True
    return bool(resolve_recovery_resume_on_startup_config()["enabled"])


def _print_startup_line(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass


def log_recovery_scheduler_ownership_at_startup() -> RecoverySchedulerOwnershipConfig:
    """
    Emit ownership mode once per process startup.

    Logs:
      [RECOVERY SCHEDULER OWNER] enabled=… reason=…
      [RECOVERY WORKER MODE] (warning only when enabled)
    """
    cfg = resolve_recovery_resume_on_startup_config()
    enabled = cfg["enabled"]
    _print_startup_line("[RECOVERY SCHEDULER OWNER]")
    _print_startup_line(f"enabled={'true' if enabled else 'false'}")
    _print_startup_line(f"reason={cfg['reason']}")
    if cfg["env_set"]:
        _print_startup_line(f"{ENV_RECOVERY_RESUME_ON_STARTUP}={cfg['env_raw'][:64]}")
    else:
        _print_startup_line(f"{ENV_RECOVERY_RESUME_ON_STARTUP}=(unset)")

    if enabled:
        _print_startup_line("[RECOVERY WORKER MODE]")
        _print_startup_line("mode=single_scheduler_expected")
        _print_startup_line(
            "warning=do_not_enable_on_multiple_api_workers"
        )

    try:
        log.info(
            "[RECOVERY SCHEDULER OWNER] enabled=%s reason=%s env_set=%s",
            enabled,
            cfg["reason"],
            cfg["env_set"],
        )
    except Exception:  # noqa: BLE001
        pass

    return cfg


__all__ = [
    "ENV_RECOVERY_RESUME_ON_STARTUP",
    "is_recovery_resume_on_startup_enabled",
    "log_recovery_scheduler_ownership_at_startup",
    "resolve_recovery_resume_on_startup_config",
]
