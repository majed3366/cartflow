# -*- coding: utf-8 -*-
"""Always-on wall/query profiling for GET /api/dashboard/normal-carts (logging only)."""
from __future__ import annotations

import contextvars
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, Optional

log = logging.getLogger("cartflow")

_active: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "dashboard_nc_perf_active", default=False
)


@dataclass
class _PerfState:
    wall_start: float = 0.0
    abandoned_cart_count_loaded: int = 0
    recovery_schedule_rows_loaded: int = 0
    recovery_log_rows_loaded: int = 0
    lifecycle_attach_ms: float = 0.0
    followup_clarity_ms: float = 0.0
    render_payload_ms: float = 0.0
    stage_ms: dict[str, float] = field(default_factory=dict)
    slow_stage: str = "-"


_state: contextvars.ContextVar[Optional[_PerfState]] = contextvars.ContextVar(
    "dashboard_nc_perf_state", default=None
)


def dashboard_normal_carts_perf_active() -> bool:
    return bool(_active.get())


def dashboard_normal_carts_perf_begin() -> None:
    _active.set(True)
    _state.set(
        _PerfState(
            wall_start=time.perf_counter(),
            stage_ms={},
            slow_stage="-",
        )
    )


def _get_state() -> Optional[_PerfState]:
    return _state.get()


def _record_stage_ms(name: str, ms: float) -> None:
    st = _get_state()
    if st is None or not name:
        return
    prev = float(st.stage_ms.get(name) or 0.0)
    st.stage_ms[name] = prev + max(0.0, float(ms))


def _maybe_slowest_stage(name: str, ms: float) -> None:
    st = _get_state()
    if st is None or not name:
        return
    cur_name, cur_ms = "-", 0.0
    if st.slow_stage and st.slow_stage != "-":
        parts = st.slow_stage.rsplit("(", 1)
        cur_name = parts[0]
        if len(parts) > 1 and parts[1].endswith("ms)"):
            try:
                cur_ms = float(parts[1][:-4])
            except ValueError:
                cur_ms = 0.0
    if ms > cur_ms:
        st.slow_stage = f"{name}({round(ms, 1)}ms)"


@contextmanager
def dashboard_normal_carts_perf_stage(name: str) -> Iterator[None]:
    if not dashboard_normal_carts_perf_active():
        yield
        return
    t0 = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - t0) * 1000.0
        _record_stage_ms(name, ms)
        _maybe_slowest_stage(name, ms)


def dashboard_normal_carts_perf_record_loads(
    *,
    abandoned_carts: int = 0,
    recovery_log_rows: int = 0,
    recovery_schedule_rows: int = 0,
) -> None:
    st = _get_state()
    if st is None:
        return
    if abandoned_carts:
        st.abandoned_cart_count_loaded = int(abandoned_carts)
    if recovery_log_rows:
        st.recovery_log_rows_loaded = int(recovery_log_rows)
    if recovery_schedule_rows:
        st.recovery_schedule_rows_loaded = int(recovery_schedule_rows)


def dashboard_normal_carts_perf_add_lifecycle_ms(ms: float) -> None:
    st = _get_state()
    if st is None:
        return
    st.lifecycle_attach_ms += max(0.0, float(ms))
    _maybe_slowest_stage("lifecycle_attach", st.lifecycle_attach_ms)


def dashboard_normal_carts_perf_add_clarity_ms(ms: float) -> None:
    st = _get_state()
    if st is None:
        return
    st.followup_clarity_ms += max(0.0, float(ms))
    _maybe_slowest_stage("followup_clarity", st.followup_clarity_ms)


def dashboard_normal_carts_perf_add_render_payload_ms(ms: float) -> None:
    st = _get_state()
    if st is None:
        return
    st.render_payload_ms += max(0.0, float(ms))
    _maybe_slowest_stage("render_payload", st.render_payload_ms)


def _peek_db_query_count() -> str:
    try:
        from services.db_request_audit import (  # noqa: PLC0415
            audit_enabled,
            peek_request_audit_bucket_for_profile,
        )

        if not audit_enabled():
            return "n/a"
        peek = peek_request_audit_bucket_for_profile()
        if peek is None:
            return "?"
        return str(int(peek.get("queries") or 0))
    except Exception:  # noqa: BLE001
        return "?"


def _resolve_slow_stage(st: _PerfState) -> str:
    candidates: list[tuple[str, float]] = [
        ("lifecycle_attach", st.lifecycle_attach_ms),
        ("followup_clarity", st.followup_clarity_ms),
        ("render_payload", st.render_payload_ms),
    ]
    for name, ms in st.stage_ms.items():
        candidates.append((name, ms))
    try:
        from services.normal_carts_query_profiler import (  # noqa: PLC0415
            top_exclusive_wall_span,
        )

        fn, sub_ms = top_exclusive_wall_span()
        if fn and sub_ms > 0:
            candidates.append((fn, sub_ms))
    except Exception:  # noqa: BLE001
        pass
    if not candidates:
        return st.slow_stage or "-"
    best_name, best_ms = max(candidates, key=lambda x: x[1])
    if best_ms <= 0:
        return st.slow_stage or "-"
    return f"{best_name}({round(best_ms, 1)}ms)"


def dashboard_normal_carts_perf_emit(*, wall_perf_start: float) -> None:
    """Emit one [DASHBOARD PERF] line — always when perf was begun for this request."""
    st = _get_state()
    try:
        if st is None:
            return
        total_ms = round((time.perf_counter() - float(wall_perf_start)) * 1000.0, 1)
        slow = _resolve_slow_stage(st)
        line = (
            "[DASHBOARD PERF] "
            f"total_ms={total_ms} "
            f"queries={_peek_db_query_count()} "
            f"carts={int(st.abandoned_cart_count_loaded)} "
            f"schedules={int(st.recovery_schedule_rows_loaded)} "
            f"logs={int(st.recovery_log_rows_loaded)} "
            f"lifecycle_ms={round(st.lifecycle_attach_ms, 1)} "
            f"clarity_ms={round(st.followup_clarity_ms, 1)} "
            f"payload_ms={round(st.render_payload_ms, 1)} "
            f"slow_stage={slow}"
        )
        try:
            log.info("%s", line)
        except Exception:  # noqa: BLE001
            pass
        try:
            print(line, flush=True)
        except OSError:
            pass
    finally:
        _active.set(False)
        _state.set(None)


__all__ = [
    "dashboard_normal_carts_perf_active",
    "dashboard_normal_carts_perf_add_clarity_ms",
    "dashboard_normal_carts_perf_add_lifecycle_ms",
    "dashboard_normal_carts_perf_add_render_payload_ms",
    "dashboard_normal_carts_perf_begin",
    "dashboard_normal_carts_perf_emit",
    "dashboard_normal_carts_perf_record_loads",
    "dashboard_normal_carts_perf_stage",
]
