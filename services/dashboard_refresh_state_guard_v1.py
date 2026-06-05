# -*- coding: utf-8 -*-
"""
Wall-clock guard + stage diagnostics for GET /api/dashboard/refresh-state.

Returns a safe minimal refresh token payload on deadline instead of hanging.
Does not change cart classification, recovery, or widget behavior.
"""
from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from typing import Any, Optional

from services.request_hang_diag_v1 import (
    begin_hang_trace,
    emit_hang_stage_line,
    hang_elapsed_ms,
    hang_stage_elapsed_ms,
    hang_trace_id,
)

log = logging.getLogger("cartflow")

_PREFIX = "[REFRESH STATE STAGE]"
_DEADLINE_PREFIX = "[REFRESH STATE DEADLINE EXCEEDED]"

_DEFAULT_WALL_BUDGET_S = 4.5


def _resolve_wall_budget_s() -> float:
    raw = (
        os.environ.get("CARTFLOW_REFRESH_STATE_WALL_BUDGET_S")
        or os.environ.get("CARTFLOW_NORMAL_CARTS_WALL_BUDGET_S")
        or ""
    ).strip()
    if not raw:
        return _DEFAULT_WALL_BUDGET_S
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_WALL_BUDGET_S
    return max(1.0, min(30.0, val))

_request_t0: ContextVar[float] = ContextVar("refresh_state_guard_t0", default=0.0)
_deadline_mono: ContextVar[Optional[float]] = ContextVar(
    "refresh_state_guard_deadline", default=None
)
_partial: ContextVar[bool] = ContextVar("refresh_state_guard_partial", default=False)
_timeout_stage: ContextVar[str] = ContextVar("refresh_state_timeout_stage", default="")


def refresh_state_wall_budget_s() -> float:
    return _resolve_wall_budget_s()


def refresh_state_guard_begin(request: Any = None) -> str:
    """Start wall guard + trace; returns trace_id."""
    tid = begin_hang_trace(request) if request is not None else begin_hang_trace(_MinimalRequest())
    t0 = time.perf_counter()
    _request_t0.set(t0)
    _deadline_mono.set(t0 + _resolve_wall_budget_s())
    _partial.set(False)
    _timeout_stage.set("")
    return tid


class _MinimalRequest:
    method = "GET"
    url = type("U", (), {"path": "/api/dashboard/refresh-state"})()


def refresh_state_guard_request_t0() -> float:
    return float(_request_t0.get() or 0.0)


def refresh_state_deadline_exceeded() -> bool:
    dl = _deadline_mono.get()
    if dl is None:
        return False
    return time.perf_counter() >= dl


def refresh_state_mark_partial(stage: str) -> None:
    st = (stage or "unknown").strip()[:64]
    _partial.set(True)
    if not (_timeout_stage.get() or "").strip():
        _timeout_stage.set(st)


def refresh_state_partial_active() -> bool:
    return bool(_partial.get())


def refresh_state_timeout_stage() -> str:
    return str(_timeout_stage.get() or "").strip()


def refresh_state_log_stage(
    stage: str,
    *,
    stage_t0: Optional[float] = None,
    store_slug: Optional[str] = None,
    **extra: Any,
) -> None:
    fields = dict(extra)
    if store_slug:
        fields["store_slug"] = str(store_slug)[:64]
    if stage_t0 is not None:
        fields["stage_elapsed_ms"] = hang_stage_elapsed_ms(stage_t0)
    emit_hang_stage_line(_PREFIX, stage, **fields)


def refresh_state_log_deadline_exceeded(*, stage: str, store_slug: Optional[str] = None) -> None:
    refresh_state_mark_partial(stage)
    parts = [
        _DEADLINE_PREFIX,
        f"stage={(stage or 'unknown')[:64]}",
        f"elapsed_ms={hang_elapsed_ms()}",
    ]
    tid = hang_trace_id()
    if tid:
        parts.append(f"trace_id={tid}")
    if store_slug:
        parts.append(f"store_slug={str(store_slug)[:64]}")
    ts = refresh_state_timeout_stage()
    if ts:
        parts.append(f"timeout_stage={ts}")
    line = " ".join(parts)
    try:
        log.warning("%s", line)
    except Exception:  # noqa: BLE001
        pass
    try:
        print(line, flush=True)
    except OSError:
        pass


def refresh_state_minimal_payload(
    *,
    store_slug: Optional[str] = None,
    stage: str = "deadline",
) -> dict[str, Any]:
    """
    Safe fallback — same keys/shape as full refresh-state; token stable until real data loads.
    """
    slug = (store_slug or "").strip()[:255]
    revision_token = f"{slug}:partial:0:0:0" if slug else "partial:0:0:0"
    return {
        "merchant_dashboard_refresh_token": revision_token,
        "merchant_dashboard_refresh_last_log_id": 0,
        "merchant_dashboard_refresh_last_sent_log_id": 0,
        "merchant_dashboard_refresh_sent_total": 0,
        "refresh_state_partial": True,
        "refresh_state_timeout_stage": (stage or refresh_state_timeout_stage() or "deadline")[
            :64
        ],
        "refresh_state_wall_budget_s": round(_resolve_wall_budget_s(), 2),
    }


def clear_refresh_state_guard_for_tests() -> None:
    _request_t0.set(0.0)
    _deadline_mono.set(None)
    _partial.set(False)
    _timeout_stage.set("")
    from services.request_hang_diag_v1 import clear_hang_trace_for_tests

    clear_hang_trace_for_tests()


__all__ = [
    "clear_refresh_state_guard_for_tests",
    "refresh_state_deadline_exceeded",
    "refresh_state_guard_begin",
    "refresh_state_log_deadline_exceeded",
    "refresh_state_log_stage",
    "refresh_state_mark_partial",
    "refresh_state_minimal_payload",
    "refresh_state_partial_active",
    "refresh_state_timeout_stage",
    "refresh_state_wall_budget_s",
]
