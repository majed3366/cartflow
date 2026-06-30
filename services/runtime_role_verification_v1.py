# -*- coding: utf-8 -*-
"""
Reliability Foundation V1 — Phase 0: fail-fast runtime role verification at startup.

Public API (smart-reply-ai) must run with ``CARTFLOW_PROCESS_ROLE=api`` and scheduler
drivers disabled via env. Scheduler service uses ``role=scheduler``.
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("cartflow")

ENV_ENFORCE_API_ONLY = "CARTFLOW_ENFORCE_API_ONLY"
_PREFIX_API = "[API ROLE VERIFIED]"
_PREFIX_SCHEDULER = "[SCHEDULER ROLE VERIFIED]"


class RuntimeRoleVerificationError(RuntimeError):
    """Process role or scheduler env is invalid for this deployment."""


def _env_truthy(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def enforce_api_only_service() -> bool:
    """True when this deployment must be API-only (e.g. smart-reply-ai public service)."""
    return _env_truthy(ENV_ENFORCE_API_ONLY)


def _emit(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _resume_env_enabled() -> bool:
    from services.recovery_scheduler_guardrails import (  # noqa: PLC0415
        resolve_recovery_resume_on_startup_config,
    )

    return bool(resolve_recovery_resume_on_startup_config().get("enabled"))


def _scanner_env_enabled() -> bool:
    from services.recovery_db_due_scanner_loop import (  # noqa: PLC0415
        is_db_due_scanner_loop_enabled,
    )

    return bool(is_db_due_scanner_loop_enabled())


def verify_runtime_role_at_startup() -> dict[str, Any]:
    """
    Validate role vs env for production-like runtimes.

    Raises ``RuntimeRoleVerificationError`` when configuration is unsafe.
    Development (``ENV=development``) skips verification.
    """
    from services.recovery_process_role_v1 import (  # noqa: PLC0415
        evaluate_scheduler_ownership_policy,
        resolve_process_role,
    )
    from services.recovery_scheduler_guardrails import (  # noqa: PLC0415
        is_production_like_runtime,
    )

    if not is_production_like_runtime():
        return {"verified": False, "skipped": True, "reason": "development"}

    role = resolve_process_role()
    policy = evaluate_scheduler_ownership_policy(force=False)
    errors: list[str] = []

    if enforce_api_only_service() and role != "api":
        errors.append(
            f"{ENV_ENFORCE_API_ONLY}=1 requires CARTFLOW_PROCESS_ROLE=api "
            f"(got {role!r})"
        )

    if role == "api":
        if _scanner_env_enabled():
            errors.append(
                "CARTFLOW_DB_DUE_SCANNER_ENABLED must be false on API service"
            )
        if _resume_env_enabled():
            errors.append(
                "CARTFLOW_RECOVERY_RESUME_ON_STARTUP must be 0/disabled on API service"
            )
        if bool(policy.get("may_due_scan")):
            errors.append("policy may_due_scan must be false for API role")
        if bool(policy.get("may_resume")):
            errors.append("policy may_resume must be false for API role")

    elif role == "scheduler":
        if not _scanner_env_enabled():
            errors.append(
                "CARTFLOW_DB_DUE_SCANNER_ENABLED must be true on scheduler service"
            )
        if not _resume_env_enabled():
            errors.append(
                "CARTFLOW_RECOVERY_RESUME_ON_STARTUP must be enabled on scheduler service"
            )

    elif role in ("unset", "unknown"):
        errors.append(
            f"CARTFLOW_PROCESS_ROLE must be api or scheduler in production-like runtime "
            f"(got {role!r})"
        )

    if errors:
        msg = "runtime role verification failed: " + "; ".join(errors)
        _emit(f"[RUNTIME ROLE VERIFICATION FAILED] {msg}")
        raise RuntimeRoleVerificationError(msg)

    if role == "api":
        line = (
            f"{_PREFIX_API} process_role=api "
            f"may_resume=false may_due_scan=false may_delay_dispatch=false "
            f"scanner_env=false resume_env=false "
            f"enforce_api_only={'true' if enforce_api_only_service() else 'false'}"
        )
    elif role == "scheduler":
        line = (
            f"{_PREFIX_SCHEDULER} process_role=scheduler "
            f"may_resume={str(bool(policy.get('may_resume'))).lower()} "
            f"may_due_scan={str(bool(policy.get('may_due_scan'))).lower()} "
            f"may_delay_dispatch={str(bool(policy.get('may_delay_dispatch'))).lower()} "
            f"scanner_env=true resume_env=true"
        )
    else:
        line = f"[RUNTIME ROLE VERIFIED] process_role={role}"

    _emit(line)
    return {
        "verified": True,
        "role": role,
        "policy": policy,
        "enforce_api_only": enforce_api_only_service(),
    }


__all__ = [
    "ENV_ENFORCE_API_ONLY",
    "RuntimeRoleVerificationError",
    "enforce_api_only_service",
    "verify_runtime_role_at_startup",
]
