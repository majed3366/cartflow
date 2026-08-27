# -*- coding: utf-8 -*-
"""Role-based conservative SQLAlchemy pool bounds. Fail closed on excess."""
from __future__ import annotations

import os
from typing import Any

ENV_POOL_SIZE = "CARTFLOW_DB_POOL_SIZE"
ENV_POOL_OVERFLOW = "CARTFLOW_DB_POOL_MAX_OVERFLOW"
ENV_POOL_TIMEOUT = "CARTFLOW_DB_POOL_TIMEOUT"

API_DEFAULT_SIZE = 5
API_DEFAULT_OVERFLOW = 5
SCHEDULER_DEFAULT_SIZE = 2
SCHEDULER_DEFAULT_OVERFLOW = 2
DEFAULT_TIMEOUT = 5

API_MAX_SIZE = 10
API_MAX_OVERFLOW = 10
SCHEDULER_MAX_SIZE = 5
SCHEDULER_MAX_OVERFLOW = 5
MAX_TIMEOUT = 30


class PoolBoundsError(ValueError):
    """Pool size/overflow/timeout is invalid or exceeds the role cap."""


def _role() -> str:
    return (os.getenv("CARTFLOW_PROCESS_ROLE") or "").strip().lower()


def _parse_int(name: str) -> int | None:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise PoolBoundsError(f"{name} is not an integer") from exc


def resolve_pool_bounds() -> dict[str, Any]:
    role = _role()
    if role == "scheduler":
        default_size, default_overflow = SCHEDULER_DEFAULT_SIZE, SCHEDULER_DEFAULT_OVERFLOW
        max_size, max_overflow = SCHEDULER_MAX_SIZE, SCHEDULER_MAX_OVERFLOW
    else:
        default_size, default_overflow = API_DEFAULT_SIZE, API_DEFAULT_OVERFLOW
        max_size, max_overflow = API_MAX_SIZE, API_MAX_OVERFLOW

    size = _parse_int(ENV_POOL_SIZE)
    overflow = _parse_int(ENV_POOL_OVERFLOW)
    timeout = _parse_int(ENV_POOL_TIMEOUT)

    if size is None:
        size = default_size
    if overflow is None:
        overflow = default_overflow
    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    if size < 1 or overflow < 0 or timeout < 1:
        raise PoolBoundsError("pool bounds must be positive")
    if size > max_size:
        raise PoolBoundsError(f"pool_size exceeds role cap ({max_size})")
    if overflow > max_overflow:
        raise PoolBoundsError(f"pool_max_overflow exceeds role cap ({max_overflow})")
    if timeout > MAX_TIMEOUT:
        raise PoolBoundsError(f"pool_timeout exceeds cap ({MAX_TIMEOUT})")

    return {
        "role": role or "api",
        "pool_size": size,
        "max_overflow": overflow,
        "pool_timeout": timeout,
        "pool_recycle": 300,
    }


__all__ = [
    "API_DEFAULT_OVERFLOW",
    "API_DEFAULT_SIZE",
    "API_MAX_OVERFLOW",
    "API_MAX_SIZE",
    "DEFAULT_TIMEOUT",
    "ENV_POOL_OVERFLOW",
    "ENV_POOL_SIZE",
    "ENV_POOL_TIMEOUT",
    "PoolBoundsError",
    "SCHEDULER_DEFAULT_OVERFLOW",
    "SCHEDULER_DEFAULT_SIZE",
    "SCHEDULER_MAX_OVERFLOW",
    "SCHEDULER_MAX_SIZE",
    "resolve_pool_bounds",
]
