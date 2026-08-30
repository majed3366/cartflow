# -*- coding: utf-8 -*-
"""Compatibility wrapper over request_owner (single context)."""
from __future__ import annotations

from typing import Any, Optional

import time

from services.db_lifecycle_v1.request_owner import LONG_HOLD_WARN_MS, current_owner

__all__ = [
    "LONG_HOLD_WARN_MS",
    "current_request_context",
    "elapsed_ms",
    "request_context_snapshot",
]


def current_request_context() -> Optional[dict[str, Any]]:
    return current_owner()


def elapsed_ms() -> float:
    rec = current_owner()
    if not rec:
        return 0.0
    try:
        return round((time.perf_counter() - float(rec["t0"])) * 1000.0, 1)
    except Exception:  # noqa: BLE001
        return 0.0


def request_context_snapshot() -> dict[str, Any]:
    cur = current_owner()
    return dict(cur) if cur else {}
