# -*- coding: utf-8 -*-
"""Low-cardinality Product Exposure counters. No product_id / session_id / store_slug labels."""
from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_counters: dict[str, int] = {
    "exposure_requests_total": 0,
    "exposure_persisted_total": 0,
    "exposure_idempotent_replay_total": 0,
    "exposure_commercial_dedupe_total": 0,
    "exposure_rejected_total": 0,
    "exposure_db_failures_total": 0,
    "retention_run_total": 0,
    "retention_failure_total": 0,
    "retention_rows_deleted_total": 0,
    "retention_fact_rows_deleted_total": 0,
    "fact_seal_success_total": 0,
    "fact_seal_failure_total": 0,
}
_gauges: dict[str, int] = {
    "unsealed_days_past_retention_total": 0,
    "retention_oldest_raw_age_days": 0,
}


def reset_exposure_metrics_for_tests() -> None:
    with _lock:
        for k in _counters:
            _counters[k] = 0
        for k in _gauges:
            _gauges[k] = 0


def incr_exposure_metric(name: str, n: int = 1) -> None:
    if n <= 0:
        return
    with _lock:
        if name in _counters:
            _counters[name] += int(n)


def set_exposure_gauge(name: str, value: int) -> None:
    with _lock:
        if name in _gauges:
            _gauges[name] = int(value)


def exposure_metrics_snapshot() -> dict[str, Any]:
    with _lock:
        out = dict(_counters)
        out.update(_gauges)
        return out
