# -*- coding: utf-8 -*-
"""
Real QueuePool counters (INV-DB-12).

Must not treat pool.status() string as the only truth.
Must not invent checked_out from overflow/max_overflow confusion.
"""
from __future__ import annotations

import threading
from typing import Any, Optional

_lock = threading.Lock()
_peak_checked_out = 0
_timeout_count = 0


def _call_int(obj: Any, name: str) -> Optional[int]:
    fn = getattr(obj, name, None)
    if not callable(fn):
        return None
    try:
        return int(fn())
    except Exception:  # noqa: BLE001
        return None


def note_checked_out(n: int) -> None:
    global _peak_checked_out
    with _lock:
        if n > _peak_checked_out:
            _peak_checked_out = n


def note_timeout() -> None:
    global _timeout_count
    with _lock:
        _timeout_count += 1


def reset_for_tests() -> None:
    global _peak_checked_out, _timeout_count
    with _lock:
        _peak_checked_out = 0
        _timeout_count = 0


def pool_truth_from_pool(pool: Any) -> dict[str, Any]:
    """Read live pool object. Safe for NullPool (metrics may be None)."""
    if pool is None:
        return {"available": False, "pool_impl": "none"}
    impl = type(pool).__name__
    size = _call_int(pool, "size")
    checked_out = _call_int(pool, "checkedout")
    checked_in = _call_int(pool, "checkedin")
    overflow = _call_int(pool, "overflow")
    if checked_out is not None:
        note_checked_out(checked_out)
    with _lock:
        peak = _peak_checked_out
        timeouts = _timeout_count
    configured_size: Optional[int] = size
    configured_overflow: Optional[int] = None
    try:
        from services.db_pool_bounds_v1 import resolve_pool_bounds

        bounds = resolve_pool_bounds()
        configured_size = int(bounds["pool_size"])
        configured_overflow = int(bounds["max_overflow"])
    except Exception:  # noqa: BLE001
        pass
    max_conn: Optional[int] = None
    if configured_size is not None and configured_overflow is not None:
        max_conn = int(configured_size) + int(configured_overflow)
    elif size is not None:
        max_conn = int(size) + max(0, int(overflow or 0))
    available_slots: Optional[int] = None
    if max_conn is not None and checked_out is not None:
        available_slots = max(0, int(max_conn) - int(checked_out))
    return {
        "available": True,
        "pool_impl": impl,
        "size": size,
        "checked_out": checked_out,
        "checked_in": checked_in,
        "overflow": overflow,
        "max_connections": max_conn,
        "available_slots": available_slots,
        "peak_checked_out": peak,
        "timeout_count": timeouts,
        "configured_pool_size": configured_size,
        "configured_max_overflow": configured_overflow,
    }


def pool_truth_snapshot() -> dict[str, Any]:
    try:
        from extensions import db

        pool = getattr(getattr(db, "engine", None), "pool", None)
        return pool_truth_from_pool(pool)
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "pool_impl": "unknown", "error": str(exc)[:120]}
