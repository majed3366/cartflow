# -*- coding: utf-8 -*-
"""
Lightweight request hang diagnostics — trace id + elapsed timing (observability only).
"""
from __future__ import annotations

import hashlib
import logging
import time
from contextvars import ContextVar
from typing import Any, Optional

log = logging.getLogger("cartflow")

_trace_id: ContextVar[str] = ContextVar("request_hang_trace_id", default="")
_request_t0: ContextVar[float] = ContextVar("request_hang_request_t0", default=0.0)


def begin_hang_trace(request: Any) -> str:
    """Bind a short trace id for stage logs on this request (route entry only)."""
    try:
        path = getattr(getattr(request, "url", None), "path", "") or ""
        method = getattr(request, "method", "") or "GET"
    except Exception:  # noqa: BLE001
        path, method = "", "GET"
    seed = f"{method}:{path}:{time.time_ns()}"
    tid = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    _trace_id.set(tid)
    _request_t0.set(time.perf_counter())
    return tid


def hang_trace_id() -> str:
    return str(_trace_id.get() or "").strip()


def hang_request_t0() -> float:
    return float(_request_t0.get() or 0.0)


def hang_elapsed_ms(*, since_t0: Optional[float] = None) -> float:
    base = since_t0 if since_t0 is not None else hang_request_t0()
    if base <= 0:
        base = time.perf_counter()
    return round((time.perf_counter() - base) * 1000.0, 1)


def hang_stage_elapsed_ms(stage_t0: float) -> float:
    return round((time.perf_counter() - float(stage_t0)) * 1000.0, 1)


def emit_hang_stage_line(prefix: str, stage: str, **extra: Any) -> None:
    """Always-on stage line with flush — prefix e.g. [DEMO STORE STAGE]."""
    st = (stage or "unknown").strip()[:64]
    parts = [
        prefix,
        f"stage={st}",
        f"elapsed_ms={hang_elapsed_ms()}",
    ]
    tid = hang_trace_id()
    if tid:
        parts.append(f"trace_id={tid}")
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


def clear_hang_trace_for_tests() -> None:
    _trace_id.set("")
    _request_t0.set(0.0)


__all__ = [
    "begin_hang_trace",
    "clear_hang_trace_for_tests",
    "emit_hang_stage_line",
    "hang_elapsed_ms",
    "hang_request_t0",
    "hang_stage_elapsed_ms",
    "hang_trace_id",
]
