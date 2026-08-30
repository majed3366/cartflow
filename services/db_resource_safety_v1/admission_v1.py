# -*- coding: utf-8 -*-
"""
Per-route concurrency admission so one heavy surface cannot consume the whole pool.

Pool is 5+5=10. Reserve slots for health/auth/light reads.
Heavy merchant reads share a small semaphore.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Iterator

log = logging.getLogger("cartflow")

# Shared cap across heavy merchant reads. Leaves room for health/auth/light.
HEAVY_GLOBAL_LIMIT = 4
HEAVY_PER_ROUTE_LIMIT = 2

_lock = threading.Lock()
_global_in_use = 0
_route_in_use: dict[str, int] = {}
_rejected = 0
_peak_global = 0


def snapshot() -> dict[str, int]:
    with _lock:
        return {
            "global_in_use": _global_in_use,
            "peak_global": _peak_global,
            "rejected": _rejected,
            "route_in_use": dict(_route_in_use),
        }


def reset_for_tests() -> None:
    global _global_in_use, _rejected, _peak_global
    with _lock:
        _global_in_use = 0
        _rejected = 0
        _peak_global = 0
        _route_in_use.clear()


def try_acquire(route: str) -> bool:
    global _global_in_use, _rejected, _peak_global
    key = (route or "unknown")[:128]
    with _lock:
        route_n = int(_route_in_use.get(key) or 0)
        if _global_in_use >= HEAVY_GLOBAL_LIMIT or route_n >= HEAVY_PER_ROUTE_LIMIT:
            _rejected += 1
            return False
        _global_in_use += 1
        _route_in_use[key] = route_n + 1
        if _global_in_use > _peak_global:
            _peak_global = _global_in_use
        return True


def release(route: str) -> None:
    global _global_in_use
    key = (route or "unknown")[:128]
    with _lock:
        route_n = int(_route_in_use.get(key) or 0)
        if route_n > 0:
            _route_in_use[key] = route_n - 1
        if _global_in_use > 0:
            _global_in_use -= 1


@contextmanager
def admit_heavy_route(route: str) -> Iterator[bool]:
    """Yields True if admitted. Caller must degrade itself when False."""
    ok = try_acquire(route)
    if not ok:
        log.warning("[DB RESOURCE SAFETY] heavy route rejected route=%s", route)
    try:
        yield ok
    finally:
        if ok:
            release(route)


__all__ = [
    "HEAVY_GLOBAL_LIMIT",
    "HEAVY_PER_ROUTE_LIMIT",
    "admit_heavy_route",
    "release",
    "reset_for_tests",
    "snapshot",
    "try_acquire",
]
