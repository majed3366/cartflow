# -*- coding: utf-8 -*-
"""
Product Foundation query cost v1 — lightweight read timing visibility.

Reusable helper for Product Foundation read paths. Diagnostic only — no
external monitoring integration and no instrumentation of every query yet.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

log = logging.getLogger("cartflow")

QUERY_COST_OK = "ok"
QUERY_COST_SLOW = "slow"
QUERY_COST_FAILED = "failed"

QUERY_COST_STATUS_VALUES = frozenset(
    {QUERY_COST_OK, QUERY_COST_SLOW, QUERY_COST_FAILED}
)

DEFAULT_SLOW_QUERY_MS = 500.0

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class QueryCostRecord:
    query_name: str
    duration_ms: float
    row_count: Optional[int] = None
    status: str = QUERY_COST_OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_name": self.query_name,
            "duration_ms": round(self.duration_ms, 2),
            "row_count": self.row_count,
            "status": self.status,
        }


def _status_for_duration(duration_ms: float, *, slow_threshold_ms: float) -> str:
    if duration_ms >= slow_threshold_ms:
        return QUERY_COST_SLOW
    return QUERY_COST_OK


def run_timed_read(
    query_name: str,
    fn: Callable[[], T],
    *,
    slow_threshold_ms: float = DEFAULT_SLOW_QUERY_MS,
    row_count_from: Callable[[T], Optional[int]] | None = None,
) -> tuple[Optional[T], QueryCostRecord]:
    """
    Execute a read callable and capture lightweight timing metadata.

    Never raises — failures return ``(None, QueryCostRecord(status=failed))``.
    """
    name = (query_name or "").strip() or "unnamed_read"
    start = time.perf_counter()
    try:
        result = fn()
        duration_ms = (time.perf_counter() - start) * 1000.0
        row_count: Optional[int] = None
        if row_count_from is not None:
            try:
                row_count = row_count_from(result)
            except Exception:  # noqa: BLE001
                row_count = None
        status = _status_for_duration(duration_ms, slow_threshold_ms=slow_threshold_ms)
        return result, QueryCostRecord(
            query_name=name,
            duration_ms=duration_ms,
            row_count=row_count,
            status=status,
        )
    except Exception as exc:  # noqa: BLE001
        duration_ms = (time.perf_counter() - start) * 1000.0
        log.debug("product foundation read failed (%s): %s", name, exc)
        return None, QueryCostRecord(
            query_name=name,
            duration_ms=duration_ms,
            row_count=None,
            status=QUERY_COST_FAILED,
        )


__all__ = [
    "DEFAULT_SLOW_QUERY_MS",
    "QUERY_COST_FAILED",
    "QUERY_COST_OK",
    "QUERY_COST_SLOW",
    "QUERY_COST_STATUS_VALUES",
    "QueryCostRecord",
    "run_timed_read",
]
