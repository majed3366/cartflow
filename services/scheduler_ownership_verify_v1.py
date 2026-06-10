# -*- coding: utf-8 -*-
"""
Scheduler ownership deploy verification v1 — read-only health validation helpers.

Used by ``scripts/scheduler_ownership_verify.py`` and tests.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from services.scheduler_ownership_diagnosis_v1 import DIAG_SCHEDULER_ROLE_MISCONFIGURED


def fetch_scheduler_health(base_url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/health/scheduler"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("health response is not a JSON object")
    return data


def evaluate_scheduler_health(
    health: dict[str, Any],
    *,
    expected_role: str,
) -> dict[str, Any]:
    """Validate one /health/scheduler payload against expected role."""
    expected = (expected_role or "").strip().lower()
    role = str(health.get("role") or "")
    own = health.get("scheduler_ownership") if isinstance(health.get("scheduler_ownership"), dict) else {}
    diagnosis = health.get("ownership_diagnosis") if isinstance(health.get("ownership_diagnosis"), dict) else {}
    compliance = str(own.get("compliance") or health.get("compliance") or "")
    block_reason = own.get("block_reason") or health.get("block_reason")
    may_resume = bool(own.get("may_resume", health.get("resume_enabled")))
    may_due_scan = bool(own.get("may_due_scan", health.get("due_scanner_enabled")))
    may_delay = bool(own.get("may_delay_dispatch", health.get("delay_dispatch_enabled")))
    ok = bool(health.get("ok"))
    codes = list(diagnosis.get("codes") or [])

    errors: list[str] = []
    warnings: list[str] = []

    if expected not in ("scheduler", "api"):
        errors.append(f"invalid expected role: {expected_role!r}")

    if compliance != "ok":
        errors.append(f"compliance={compliance!r} (expected ok)")

    if role != expected:
        errors.append(f"role={role!r} (expected {expected!r})")

    if expected == "api":
        if may_resume:
            errors.append("api process may_resume=true")
        if may_due_scan:
            errors.append("api process may_due_scan=true")
        if may_delay:
            errors.append("api process may_delay_dispatch=true")
        if DIAG_SCHEDULER_ROLE_MISCONFIGURED in codes:
            errors.append("misconfigured diagnosis on api replica")
        if ok is False and compliance == "ok":
            warnings.append("ok=false despite compliant api role (check DB errors)")

    if expected == "scheduler":
        if not may_delay:
            errors.append("scheduler process may_delay_dispatch=false")
        if not may_resume:
            warnings.append("scheduler may_resume=false (check CARTFLOW_RECOVERY_RESUME_ON_STARTUP)")
        if not ok:
            errors.append("scheduler health ok=false")
        if DIAG_SCHEDULER_ROLE_MISCONFIGURED in codes:
            errors.append("misconfigured diagnosis on scheduler")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "expected_role": expected,
        "role": role,
        "compliance": compliance,
        "block_reason": block_reason,
        "ok": ok,
        "may_resume": may_resume,
        "may_due_scan": may_due_scan,
        "may_delay_dispatch": may_delay,
        "diagnosis_codes": codes,
        "diagnosis_severity": diagnosis.get("severity"),
        "diagnosis_summary": diagnosis.get("summary"),
        "errors": errors,
        "warnings": warnings,
    }


def run_deploy_verification(
    checks: list[tuple[str, str]],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    all_pass = True

    for expected_role, base_url in checks:
        entry: dict[str, Any] = {
            "url": base_url,
            "expected_role": expected_role,
        }
        try:
            health = fetch_scheduler_health(base_url)
            entry["health_ok"] = bool(health.get("ok"))
            verdict = evaluate_scheduler_health(health, expected_role=expected_role)
            entry.update(verdict)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            entry["passed"] = False
            entry["errors"] = [str(exc)[:300]]
            all_pass = False
        else:
            if not entry.get("passed"):
                all_pass = False
        results.append(entry)

    scheduler_count = sum(1 for role, _ in checks if role == "scheduler")
    if scheduler_count != 1:
        for entry in results:
            entry.setdefault("errors", []).append(
                f"deployment check: expected exactly one scheduler URL, got {scheduler_count}"
            )
        all_pass = False

    return {
        "passed": all_pass,
        "checks": results,
        "scheduler_count": scheduler_count,
        "api_count": sum(1 for role, _ in checks if role == "api"),
    }


__all__ = [
    "evaluate_scheduler_health",
    "fetch_scheduler_health",
    "run_deploy_verification",
]
