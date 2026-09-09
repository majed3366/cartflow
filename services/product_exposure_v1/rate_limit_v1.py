# -*- coding: utf-8 -*-
"""In-process rate limits for POST /api/storefront/product-viewed. No Redis."""
from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Optional

from services.product_exposure_v1.constants_v1 import (
    RATE_ORIGIN_PER_MIN,
    RATE_SESSION_PER_MIN,
    RATE_STORE_PER_MIN,
)

_lock = threading.Lock()
_windows: dict[str, deque[float]] = {}


def exposure_rate_limit_enabled() -> bool:
    raw = (os.environ.get("CARTFLOW_EXPOSURE_RATE_LIMIT_ENABLED") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def reset_exposure_rate_limiter_for_tests() -> None:
    with _lock:
        _windows.clear()


def _allow(key: str, limit: int, now: float, window_s: float = 60.0) -> bool:
    q = _windows.setdefault(key, deque())
    while q and now - q[0] >= window_s:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


def check_exposure_rate_limits(
    *,
    origin_host: str,
    session_id: str,
    store_slug: str,
) -> bool:
    """False → 429. Fail-closed on internal errors."""
    if not exposure_rate_limit_enabled():
        return True
    try:
        now = time.monotonic()
        with _lock:
            if not _allow(f"o:{origin_host}", RATE_ORIGIN_PER_MIN, now):
                return False
            if not _allow(f"s:{session_id}", RATE_SESSION_PER_MIN, now):
                return False
            if not _allow(f"t:{store_slug}", RATE_STORE_PER_MIN, now):
                return False
        return True
    except Exception:  # noqa: BLE001
        return False


def origin_host_from_origin(origin: Optional[str]) -> str:
    o = (origin or "").strip().lower()
    if "://" in o:
        o = o.split("://", 1)[1]
    return o.split("/", 1)[0].split(":", 1)[0][:253]
