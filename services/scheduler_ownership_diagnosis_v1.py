# -*- coding: utf-8 -*-
"""
Scheduler ownership diagnosis v1 — read-only operational visibility.

Derives compact diagnosis codes from existing scheduler health fields.
No scheduling behavior changes.
"""
from __future__ import annotations

from typing import Any

from services.recovery_process_role_v1 import COMPLIANCE_MISCONFIGURED, COMPLIANCE_OK

DIAG_OWNERSHIP_OK = "ownership_ok"
DIAG_SCHEDULER_ROLE_API_BLOCKED = "scheduler_role_api_blocked"
DIAG_SCHEDULER_ROLE_MISCONFIGURED = "scheduler_role_misconfigured"
DIAG_SCHEDULER_OWNERSHIP_ABSENT = "scheduler_ownership_absent"
DIAG_ZOMBIE_RUNNING_ROWS = "zombie_running_rows"
DIAG_EXECUTION_BACKLOG = "execution_backlog"
DIAG_STALE_RUNNING_ROWS = "stale_running_rows"
DIAG_DUE_SCANNER_DISABLED = "due_scanner_disabled"
DIAG_RESUME_DISABLED = "resume_disabled"
DIAG_POLICY_ERROR = "policy_error"

SEVERITY_OK = "ok"
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

_SUMMARY_BY_CODE = {
    DIAG_POLICY_ERROR: "Scheduler ownership policy evaluation failed.",
    DIAG_SCHEDULER_ROLE_MISCONFIGURED: "Process role is unset or unknown in production-like runtime.",
    DIAG_SCHEDULER_ROLE_API_BLOCKED: "API role correctly blocks scheduler drivers on this process.",
    DIAG_OWNERSHIP_OK: "This process owns scheduler drivers as configured.",
    DIAG_RESUME_DISABLED: "Resume scan disabled by env or policy on this process.",
    DIAG_DUE_SCANNER_DISABLED: "DB due scanner loop is not enabled on this process.",
    DIAG_ZOMBIE_RUNNING_ROWS: "Stale running schedule rows detected (likely dead task ownership).",
    DIAG_STALE_RUNNING_ROWS: "Running rows exceed stale threshold without fresh execution.",
    DIAG_SCHEDULER_OWNERSHIP_ABSENT: "Due work exists but no scheduler driver is active here.",
    DIAG_EXECUTION_BACKLOG: "Due schedules waiting for scheduler drain.",
}


def build_ownership_diagnosis(
    *,
    scheduler_ownership: dict[str, Any],
    overdue_scheduled_count: int = 0,
    running_stale_count: int = 0,
    resume_enabled: bool = False,
    due_scanner_enabled: bool = False,
    delay_dispatch_enabled: bool = False,
) -> dict[str, Any]:
    """
    Build additive ownership diagnosis from existing health snapshot fields.

    Uses only inputs already available on ``GET /health/scheduler``.
    """
    role = str(scheduler_ownership.get("role") or "unset")
    compliance = str(scheduler_ownership.get("compliance") or "")
    block_reason = str(scheduler_ownership.get("block_reason") or "")
    may_resume = bool(scheduler_ownership.get("may_resume"))
    production_like = bool(scheduler_ownership.get("production_like"))
    policy_error = scheduler_ownership.get("policy_error")

    codes: list[str] = []
    severity = SEVERITY_INFO

    if policy_error:
        codes.append(DIAG_POLICY_ERROR)
        severity = SEVERITY_CRITICAL

    if compliance == COMPLIANCE_MISCONFIGURED:
        codes.append(DIAG_SCHEDULER_ROLE_MISCONFIGURED)
        severity = SEVERITY_CRITICAL
    elif role == "api" and compliance == COMPLIANCE_OK:
        codes.append(DIAG_SCHEDULER_ROLE_API_BLOCKED)
        severity = SEVERITY_OK
    elif (
        compliance == COMPLIANCE_OK
        and role == "scheduler"
        and may_resume
        and delay_dispatch_enabled
    ):
        codes.append(DIAG_OWNERSHIP_OK)
        severity = SEVERITY_OK

    if block_reason == "resume_on_startup_disabled" or (
        role == "scheduler" and compliance == COMPLIANCE_OK and not may_resume
    ):
        if DIAG_RESUME_DISABLED not in codes:
            codes.append(DIAG_RESUME_DISABLED)
        if severity == SEVERITY_INFO:
            severity = SEVERITY_WARNING

    if role == "scheduler" and compliance == COMPLIANCE_OK and not due_scanner_enabled:
        codes.append(DIAG_DUE_SCANNER_DISABLED)

    if running_stale_count > 0:
        if DIAG_ZOMBIE_RUNNING_ROWS not in codes:
            codes.append(DIAG_ZOMBIE_RUNNING_ROWS)
        if DIAG_STALE_RUNNING_ROWS not in codes:
            codes.append(DIAG_STALE_RUNNING_ROWS)
        if severity in (SEVERITY_INFO, SEVERITY_OK):
            severity = SEVERITY_WARNING

    overdue = max(0, int(overdue_scheduled_count or 0))
    if overdue > 0:
        drivers_active = may_resume or delay_dispatch_enabled
        if compliance == COMPLIANCE_MISCONFIGURED or (
            role == "api" and not drivers_active
        ):
            if DIAG_SCHEDULER_OWNERSHIP_ABSENT not in codes:
                codes.append(DIAG_SCHEDULER_OWNERSHIP_ABSENT)
            severity = SEVERITY_CRITICAL
        elif role == "scheduler" and drivers_active:
            if DIAG_EXECUTION_BACKLOG not in codes:
                codes.append(DIAG_EXECUTION_BACKLOG)
            if severity in (SEVERITY_INFO, SEVERITY_OK):
                severity = SEVERITY_WARNING
        elif not drivers_active and production_like:
            if DIAG_SCHEDULER_OWNERSHIP_ABSENT not in codes:
                codes.append(DIAG_SCHEDULER_OWNERSHIP_ABSENT)
            severity = SEVERITY_CRITICAL

    if not codes:
        codes.append(DIAG_OWNERSHIP_OK if may_resume else DIAG_RESUME_DISABLED)
        if severity == SEVERITY_INFO and not may_resume:
            severity = SEVERITY_WARNING

    primary = codes[0]
    summary = _SUMMARY_BY_CODE.get(primary, "Scheduler ownership state requires review.")
    if len(codes) > 1:
        summary = f"{summary} Also: {', '.join(codes[1:3])}."

    return {
        "codes": codes,
        "severity": severity,
        "summary": summary,
        "role": role,
        "compliance": compliance,
        "block_reason": block_reason or None,
        "overdue_scheduled_count": overdue,
        "running_stale_count": max(0, int(running_stale_count or 0)),
        "resume_enabled": bool(resume_enabled),
        "due_scanner_enabled": bool(due_scanner_enabled),
        "delay_dispatch_enabled": bool(delay_dispatch_enabled),
    }


__all__ = [
    "DIAG_DUE_SCANNER_DISABLED",
    "DIAG_EXECUTION_BACKLOG",
    "DIAG_OWNERSHIP_OK",
    "DIAG_POLICY_ERROR",
    "DIAG_RESUME_DISABLED",
    "DIAG_SCHEDULER_OWNERSHIP_ABSENT",
    "DIAG_SCHEDULER_ROLE_API_BLOCKED",
    "DIAG_SCHEDULER_ROLE_MISCONFIGURED",
    "DIAG_STALE_RUNNING_ROWS",
    "DIAG_ZOMBIE_RUNNING_ROWS",
    "SEVERITY_CRITICAL",
    "SEVERITY_INFO",
    "SEVERITY_OK",
    "SEVERITY_WARNING",
    "build_ownership_diagnosis",
]
