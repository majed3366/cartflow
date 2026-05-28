# -*- coding: utf-8 -*-
"""
Cooperative wall-clock guard for GET /api/dashboard/normal-carts.

Logging-only stage markers + deadline checks; returns partial payloads instead of hanging.
Does not change recovery, WhatsApp, scheduling, or lifecycle classification rules.
"""
from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from typing import Any, Optional

log = logging.getLogger("cartflow")

_DEFAULT_WALL_BUDGET_S = 4.5
_WALL_BUDGET_S = max(
    1.0,
    min(
        30.0,
        float(os.environ.get("CARTFLOW_NORMAL_CARTS_WALL_BUDGET_S", _DEFAULT_WALL_BUDGET_S)),
    ),
)

_request_t0: ContextVar[float] = ContextVar("dash_nc_guard_request_t0", default=0.0)
_deadline_mono: ContextVar[Optional[float]] = ContextVar(
    "dash_nc_guard_deadline_mono", default=None
)
_partial: ContextVar[bool] = ContextVar("dash_nc_guard_partial", default=False)
_timeout_stage: ContextVar[str] = ContextVar("dash_nc_guard_timeout_stage", default="")


def dashboard_normal_carts_wall_budget_s() -> float:
    return float(_WALL_BUDGET_S)


def dashboard_nc_guard_begin() -> float:
    """Start request guard; returns monotonic t0."""
    t0 = time.perf_counter()
    _request_t0.set(t0)
    _deadline_mono.set(t0 + _WALL_BUDGET_S)
    _partial.set(False)
    _timeout_stage.set("")
    dashboard_nc_log_stage("request_start", budget_s=_WALL_BUDGET_S)
    return t0


def dashboard_nc_guard_request_t0() -> float:
    return float(_request_t0.get() or 0.0)


def dashboard_nc_deadline_exceeded() -> bool:
    dl = _deadline_mono.get()
    if dl is None:
        return False
    return time.perf_counter() >= dl


def dashboard_nc_remaining_ms() -> float:
    dl = _deadline_mono.get()
    if dl is None:
        return _WALL_BUDGET_S * 1000.0
    return max(0.0, (dl - time.perf_counter()) * 1000.0)


def dashboard_nc_mark_partial(stage: str) -> None:
    if not stage:
        stage = "unknown"
    _partial.set(True)
    if not (_timeout_stage.get() or "").strip():
        _timeout_stage.set(stage.strip()[:64])
    dashboard_nc_log_stage(
        "deadline_partial",
        partial_at=stage,
        remaining_ms=round(dashboard_nc_remaining_ms(), 1),
    )


def dashboard_nc_partial_active() -> bool:
    return bool(_partial.get())


def dashboard_nc_timeout_stage() -> str:
    return str(_timeout_stage.get() or "").strip()


def dashboard_nc_skip_optional_db() -> bool:
    """Skip non-essential DB under wall budget (stale queued probe, refresh counts)."""
    return dashboard_nc_deadline_exceeded() or dashboard_nc_partial_active()


def dashboard_nc_log_stage(stage: str, **extra: Any) -> None:
    """Always-on stage line (flush) — survives hangs before [DASHBOARD PERF]."""
    st = (stage or "unknown").strip()[:64]
    t0 = dashboard_nc_guard_request_t0()
    if t0 <= 0:
        t0 = time.perf_counter()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    parts = [
        f"[DASHBOARD STAGE] stage={st}",
        f"elapsed_ms={elapsed_ms}",
    ]
    if dashboard_nc_deadline_exceeded():
        parts.append("deadline_exceeded=1")
    if dashboard_nc_partial_active():
        parts.append("partial=1")
    ts = dashboard_nc_timeout_stage()
    if ts:
        parts.append(f"timeout_stage={ts}")
    for k, v in extra.items():
        if v is None:
            continue
        parts.append(f"{k}={v}")
    line = " ".join(parts)
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass
    try:
        print(line, flush=True)
    except OSError:
        pass


def dashboard_nc_guard_payload() -> dict[str, Any]:
    return {
        "dashboard_wall_budget_s": round(_WALL_BUDGET_S, 2),
        "dashboard_partial": dashboard_nc_partial_active(),
        "dashboard_timeout": dashboard_nc_partial_active(),
        "dashboard_timeout_stage": dashboard_nc_timeout_stage() or None,
    }


__all__ = [
    "dashboard_nc_deadline_exceeded",
    "dashboard_nc_guard_begin",
    "dashboard_nc_guard_payload",
    "dashboard_nc_guard_request_t0",
    "dashboard_nc_log_stage",
    "dashboard_nc_mark_partial",
    "dashboard_nc_partial_active",
    "dashboard_nc_remaining_ms",
    "dashboard_nc_skip_optional_db",
    "dashboard_nc_timeout_stage",
    "dashboard_normal_carts_wall_budget_s",
]
