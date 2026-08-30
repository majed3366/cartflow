# -*- coding: utf-8 -*-
"""Binding V1 DB connection-hold budget. Governed, not a suggestion."""
from __future__ import annotations

FAST_MS = 250.0
NORMAL_MS = 1000.0
HEAVY_MS = 3000.0

CLASS_FAST = "FAST"
CLASS_NORMAL = "NORMAL"
CLASS_HEAVY = "HEAVY"
CLASS_UNSAFE = "UNSAFE"
CLASS_CRITICAL = "CRITICAL"

WITHIN_BUDGET = "WITHIN_BUDGET"
JUSTIFIED_HEAVY = "JUSTIFIED_HEAVY"
VIOLATION = "VIOLATION"
UNKNOWN = "UNKNOWN"

# Heavy routes that may hold 1–3s when snapshot/cache miss. Must stay explicit.
JUSTIFIED_HEAVY_ROUTES = frozenset(
    {
        "/api/cart-workspace/v1/projection",
        "/api/dashboard/normal-carts",
        "/api/dashboard/messages",
        "/api/cart-event",
    }
)


def classify_hold_ms(hold_ms: float, *, network_while_held: bool = False) -> str:
    if network_while_held:
        return CLASS_CRITICAL
    ms = float(hold_ms or 0.0)
    if ms < FAST_MS:
        return CLASS_FAST
    if ms < NORMAL_MS:
        return CLASS_NORMAL
    if ms <= HEAVY_MS:
        return CLASS_HEAVY
    return CLASS_UNSAFE


def verdict_for_route(
    path: str,
    hold_ms: float,
    *,
    network_while_held: bool = False,
) -> str:
    cls = classify_hold_ms(hold_ms, network_while_held=network_while_held)
    if cls == CLASS_CRITICAL:
        return VIOLATION
    if cls == CLASS_UNSAFE:
        return VIOLATION
    if cls == CLASS_HEAVY:
        p = (path or "").split("?", 1)[0]
        if p in JUSTIFIED_HEAVY_ROUTES:
            return JUSTIFIED_HEAVY
        return VIOLATION
    return WITHIN_BUDGET


__all__ = [
    "CLASS_CRITICAL",
    "CLASS_FAST",
    "CLASS_HEAVY",
    "CLASS_NORMAL",
    "CLASS_UNSAFE",
    "FAST_MS",
    "HEAVY_MS",
    "JUSTIFIED_HEAVY",
    "JUSTIFIED_HEAVY_ROUTES",
    "NORMAL_MS",
    "UNKNOWN",
    "VIOLATION",
    "WITHIN_BUDGET",
    "classify_hold_ms",
    "verdict_for_route",
]
