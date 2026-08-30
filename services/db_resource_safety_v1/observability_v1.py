# -*- coding: utf-8 -*-
"""Hold-class counters and last-route observation. No external APM."""
from __future__ import annotations

import logging
import threading
from typing import Any

from services.db_resource_safety_v1.hold_budget_v1 import (
    classify_hold_ms,
    verdict_for_route,
)

log = logging.getLogger("cartflow")

_lock = threading.Lock()
_counts: dict[str, int] = {
    "FAST": 0,
    "NORMAL": 0,
    "HEAVY": 0,
    "UNSAFE": 0,
    "CRITICAL": 0,
    "violations": 0,
}
_max_hold_ms = 0.0
_last: dict[str, Any] = {}


def record_hold(
    *,
    path: str,
    hold_ms: float,
    checkout_wait_ms: float = 0.0,
    network_while_held: bool = False,
) -> dict[str, Any]:
    global _max_hold_ms
    cls = classify_hold_ms(hold_ms, network_while_held=network_while_held)
    verdict = verdict_for_route(path, hold_ms, network_while_held=network_while_held)
    with _lock:
        _counts[cls] = int(_counts.get(cls) or 0) + 1
        if verdict == "VIOLATION":
            _counts["violations"] = int(_counts.get("violations") or 0) + 1
        if hold_ms > _max_hold_ms:
            _max_hold_ms = float(hold_ms)
        rec = {
            "path": (path or "")[:256],
            "hold_ms": round(float(hold_ms), 1),
            "checkout_wait_ms": round(float(checkout_wait_ms), 1),
            "class": cls,
            "verdict": verdict,
            "network_while_held": bool(network_while_held),
        }
        _last.update(rec)
    if cls in ("UNSAFE", "CRITICAL") or verdict == "VIOLATION":
        log.warning(
            "[DB HOLD] path=%s hold_ms=%.1f class=%s verdict=%s wait_ms=%.1f network=%s",
            path,
            hold_ms,
            cls,
            verdict,
            checkout_wait_ms,
            network_while_held,
        )
    elif cls == "HEAVY":
        log.info(
            "[DB HOLD] path=%s hold_ms=%.1f class=%s verdict=%s",
            path,
            hold_ms,
            cls,
            verdict,
        )
    return rec


def snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "counts": dict(_counts),
            "max_hold_ms": _max_hold_ms,
            "last": dict(_last),
        }


def reset_for_tests() -> None:
    global _max_hold_ms
    with _lock:
        for k in list(_counts):
            _counts[k] = 0
        _max_hold_ms = 0.0
        _last.clear()


__all__ = ["record_hold", "reset_for_tests", "snapshot"]
