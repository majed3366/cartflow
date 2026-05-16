# -*- coding: utf-8 -*-
"""
Per-function query + wall deltas for GET /api/dashboard/normal-carts only.

Uses services.db_request_audit global request bucket (cursor counter) when enabled.
Produces [NORMAL CARTS SUBPROFILE] and [NORMAL CARTS TOP] lines — logging only.

Does not alter SQL or recovery behavior.
"""
from __future__ import annotations

import contextvars
import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, DefaultDict, Dict, Iterator, List, Optional

log = logging.getLogger("cartflow")

_active: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "nc_query_prof_active", default=False
)
_stack: contextvars.ContextVar[Optional[List[Dict[str, Any]]]] = contextvars.ContextVar(
    "nc_query_prof_stack", default=None
)


@dataclass
class _SpanStats:
    inclusive_queries: int = 0
    exclusive_queries: int = 0
    inclusive_wall_ms: float = 0.0
    exclusive_wall_ms: float = 0.0
    calls: int = 0


_stats: DefaultDict[str, _SpanStats] = defaultdict(_SpanStats)


def normal_carts_query_profiling_active() -> bool:
    return bool(_active.get())


def normal_carts_profile_begin() -> None:
    _active.set(False)
    _stack.set(None)
    try:
        from services.cartflow_observability_mode import (
            observability_normal_carts_subprofiler_enabled,
        )

        ok = observability_normal_carts_subprofiler_enabled()
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        return
    _active.set(True)
    _stack.set([])
    _stats.clear()


def normal_carts_profile_end() -> None:
    try:
        if normal_carts_query_profiling_active():
            _emit_normal_carts_profile_reports()
    finally:
        _active.set(False)
        _stack.set(None)


def _peek_query_count() -> Optional[int]:
    try:
        from services.db_request_audit import peek_request_audit_bucket_for_profile
    except ImportError:
        return None
    b = peek_request_audit_bucket_for_profile()
    if b is None:
        return None
    return int(b.get("queries") or 0)


def _stack_get() -> List[Dict[str, Any]]:
    s = _stack.get()
    if s is None:
        s = []
        _stack.set(s)
    return s


@contextmanager
def normal_carts_profile_span(fn: str) -> Iterator[None]:
    """
    Stack-based exclusive attribution: child inclusive query/wall time is subtracted
    from the parent span; parent also accumulates child inclusive into nested_*.
    """
    if not normal_carts_query_profiling_active():
        yield
        return

    q0 = _peek_query_count()
    t0 = time.perf_counter()
    frame: Dict[str, Any] = {
        "q0": q0,
        "t0": t0,
        "nested_inc_q": 0,
        "nested_wall_ms": 0.0,
    }
    stk = _stack_get()
    stk.append(frame)
    try:
        yield
    finally:
        popped = stk.pop()
        if popped is not frame:
            try:
                log.warning(
                    "[NORMAL CARTS PROFILER] stack mismatch fn=%s", (fn or "")[:120]
                )
            except OSError:
                pass
        q1 = _peek_query_count()
        if q0 is None or q1 is None:
            inc_q = 0
        else:
            inc_q = max(0, q1 - int(q0))
        wall_ms = (time.perf_counter() - float(t0)) * 1000.0
        exc_q = max(0, inc_q - int(frame.get("nested_inc_q") or 0))
        exc_wall = max(0.0, wall_ms - float(frame.get("nested_wall_ms") or 0.0))

        st = _stats[fn]
        st.calls += 1
        st.inclusive_queries += inc_q
        st.exclusive_queries += exc_q
        st.inclusive_wall_ms += wall_ms
        st.exclusive_wall_ms += exc_wall

        parent = stk[-1] if stk else None
        if parent is not None:
            parent["nested_inc_q"] = int(parent.get("nested_inc_q") or 0) + inc_q
            parent["nested_wall_ms"] = float(parent.get("nested_wall_ms") or 0.0) + wall_ms


def _emit_normal_carts_profile_reports() -> None:
    if not _stats:
        return

    rows: list[tuple[str, _SpanStats]] = sorted(
        _stats.items(),
        key=lambda kv: (-kv[1].inclusive_queries, -kv[1].calls, kv[0]),
    )

    for fn, st in rows:
        if st.calls < 1:
            continue
        avg_q = (
            round(float(st.inclusive_queries) / float(st.calls), 4)
            if st.calls
            else 0.0
        )
        line = (
            f"[NORMAL CARTS SUBPROFILE] fn={fn} "
            f"queries={int(st.inclusive_queries)} "
            f"queries_exclusive={int(st.exclusive_queries)} "
            f"calls={int(st.calls)} "
            f"avg_queries_per_call={avg_q} "
            f"duration_ms={round(st.inclusive_wall_ms, 1)} "
            f"duration_exclusive_ms={round(st.exclusive_wall_ms, 1)}"
        )
        try:
            log.info("%s", line)
        except Exception:  # noqa: BLE001
            pass

    top_n = min(25, len(rows))
    for rank, (fn, st) in enumerate(rows[:top_n], start=1):
        if st.calls < 1:
            continue
        avg_q = (
            round(float(st.inclusive_queries) / float(st.calls), 4)
            if st.calls
            else 0.0
        )
        line = (
            f"[NORMAL CARTS TOP] rank={rank} fn={fn} "
            f"queries={int(st.inclusive_queries)} "
            f"queries_exclusive={int(st.exclusive_queries)} "
            f"calls={int(st.calls)} "
            f"avg_queries_per_call={avg_q} "
            f"total_ms={round(st.inclusive_wall_ms, 1)} "
            f"total_exclusive_ms={round(st.exclusive_wall_ms, 1)}"
        )
        try:
            log.info("%s", line)
        except Exception:  # noqa: BLE001
            pass
