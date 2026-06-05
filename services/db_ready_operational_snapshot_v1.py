# -*- coding: utf-8 -*-
"""
Persist lightweight DB ready operational metrics — singleton snapshot (id=1).

In-process cache mirrors DB row for fast admin reads.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger(__name__)

SNAPSHOT_ROW_ID = 1

HEALTHY_MAX_MS = 3000.0
SLOW_MAX_MS = 15000.0

_cache_lock = threading.Lock()
_cache: dict[str, Any] = {
    "last_duration_ms": 0.0,
    "worst_duration_ms": 0.0,
    "avg_duration_ms": 0.0,
    "sample_count": 0,
    "last_stage": "",
    "last_trace_id": "",
    "last_lock_wait_ms": 0.0,
    "last_query_count": 0,
    "last_sql_ms": 0.0,
    "last_success": True,
    "last_failure_message": None,
    "status": "healthy",
    "last_seen_at": None,
    "last_top_substage": "",
    "last_top_substage_queries": 0,
    "last_top_substage_sql_ms": 0.0,
    "last_top_substage_elapsed_ms": 0.0,
    "top_substages": [],
    "stage_classifications": [],
    "startup_warm_status": "not_started",
    "startup_warm_duration_ms": 0.0,
    "startup_warm_error": None,
    "last_request_cached_verification": None,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def classify_db_ready_status(duration_ms: float) -> str:
    ms = float(duration_ms or 0.0)
    if ms > SLOW_MAX_MS:
        return "blocking"
    if ms > HEALTHY_MAX_MS:
        return "slow"
    return "healthy"


def status_emoji(status: str) -> str:
    key = (status or "").strip().lower()
    if key == "blocking":
        return "🔴"
    if key == "slow":
        return "🟡"
    return "🟢"


def status_label_ar(status: str) -> str:
    key = (status or "").strip().lower()
    if key == "blocking":
        return "Blocking"
    if key == "slow":
        return "Slow"
    return "Healthy"


def record_db_ready_run(payload: dict[str, Any]) -> None:
    """Update in-process cache + durable singleton row."""
    duration_ms = round(float(payload.get("duration_ms") or 0.0), 1)
    slowest = str(payload.get("slowest_stage") or payload.get("last_stage") or "").strip()[
        :64
    ]
    trace_id = str(payload.get("trace_id") or "")[:16]
    lock_wait = round(float(payload.get("lock_wait_ms") or 0.0), 1)
    query_count = int(payload.get("query_count") or 0)
    sql_ms = round(float(payload.get("total_sql_ms") or 0.0), 1)
    success = bool(payload.get("success", True))
    err = payload.get("error")
    status = classify_db_ready_status(duration_ms)
    now = _utc_now()
    top_substage = str(payload.get("top_substage") or "")[:64]
    top_q = int(payload.get("top_substage_queries") or 0)
    top_sql = round(float(payload.get("top_substage_sql_ms") or 0.0), 1)
    top_el = round(float(payload.get("top_substage_elapsed_ms") or 0.0), 1)
    top_substages = payload.get("top_substages") or []
    if not isinstance(top_substages, list):
        top_substages = []
    stage_classifications = payload.get("stage_classifications") or []
    if not isinstance(stage_classifications, list):
        stage_classifications = []

    with _cache_lock:
        n = int(_cache.get("sample_count") or 0) + 1
        prev_avg = float(_cache.get("avg_duration_ms") or 0.0)
        avg = round(((prev_avg * (n - 1)) + duration_ms) / n, 1) if n > 0 else duration_ms
        worst = max(float(_cache.get("worst_duration_ms") or 0.0), duration_ms)
        _cache.update(
            {
                "last_duration_ms": duration_ms,
                "worst_duration_ms": worst,
                "avg_duration_ms": avg,
                "sample_count": n,
                "last_stage": slowest or "unknown",
                "last_trace_id": trace_id,
                "last_lock_wait_ms": lock_wait,
                "last_query_count": query_count,
                "last_sql_ms": sql_ms,
                "last_success": success,
                "last_failure_message": (str(err)[:255] if err else None),
                "status": status,
                "last_seen_at": now.isoformat(),
                "last_top_substage": top_substage,
                "last_top_substage_queries": top_q,
                "last_top_substage_sql_ms": top_sql,
                "last_top_substage_elapsed_ms": top_el,
                "top_substages": top_substages[:15],
                "stage_classifications": stage_classifications[:10],
            }
        )
        snap = dict(_cache)

    _persist_snapshot(snap)


def record_startup_warm_snapshot(payload: dict[str, Any]) -> None:
    """Update startup warm fields in cache + durable row (does not affect run metrics)."""
    status = str(payload.get("startup_warm_status") or "not_started").strip()[:16]
    duration_ms = round(float(payload.get("startup_warm_duration_ms") or 0.0), 1)
    err = payload.get("startup_warm_error")
    cached = payload.get("last_request_cached_verification")
    with _cache_lock:
        _cache.update(
            {
                "startup_warm_status": status,
                "startup_warm_duration_ms": duration_ms,
                "startup_warm_error": (str(err)[:255] if err else None),
                "last_request_cached_verification": (
                    bool(cached) if cached is not None else None
                ),
            }
        )
        snap = dict(_cache)
    _persist_snapshot(snap, startup_warm_only=True)


def _persist_snapshot(snap: dict[str, Any], *, startup_warm_only: bool = False) -> None:
    try:
        from extensions import db
        from models import DbReadyOperationalSnapshot
        from schema_db_ready_operational import ensure_db_ready_operational_schema

        ensure_db_ready_operational_schema(db)
        row = db.session.get(DbReadyOperationalSnapshot, SNAPSHOT_ROW_ID)
        if row is None:
            row = DbReadyOperationalSnapshot(id=SNAPSHOT_ROW_ID)
            db.session.add(row)
        if not startup_warm_only:
            row.last_duration_ms = float(snap.get("last_duration_ms") or 0.0)
            row.worst_duration_ms = float(snap.get("worst_duration_ms") or 0.0)
            row.avg_duration_ms = float(snap.get("avg_duration_ms") or 0.0)
            row.sample_count = int(snap.get("sample_count") or 0)
            row.last_stage = (snap.get("last_stage") or "")[:64] or None
            row.last_trace_id = (snap.get("last_trace_id") or "")[:16] or None
            row.last_lock_wait_ms = float(snap.get("last_lock_wait_ms") or 0.0)
            row.last_query_count = int(snap.get("last_query_count") or 0)
            row.last_sql_ms = float(snap.get("last_sql_ms") or 0.0)
            row.last_success = bool(snap.get("last_success", True))
            err = snap.get("last_failure_message")
            row.last_failure_message = (str(err)[:255] if err else None)
            row.status = str(snap.get("status") or "healthy")[:16]
            row.last_top_substage = (snap.get("last_top_substage") or "")[:64] or None
            row.last_top_substage_queries = int(snap.get("last_top_substage_queries") or 0)
            row.last_top_substage_sql_ms = float(snap.get("last_top_substage_sql_ms") or 0.0)
            row.last_top_substage_elapsed_ms = float(
                snap.get("last_top_substage_elapsed_ms") or 0.0
            )
            try:
                row.top_substages_json = json.dumps(
                    snap.get("top_substages") or [],
                    ensure_ascii=False,
                )[:8000]
            except (TypeError, ValueError):
                row.top_substages_json = "[]"
            try:
                row.stage_classifications_json = json.dumps(
                    snap.get("stage_classifications") or [],
                    ensure_ascii=False,
                )[:8000]
            except (TypeError, ValueError):
                row.stage_classifications_json = "[]"
            row.last_seen_at = _utc_now()
        row.startup_warm_status = str(snap.get("startup_warm_status") or "not_started")[:16]
        row.startup_warm_duration_ms = float(snap.get("startup_warm_duration_ms") or 0.0)
        sw_err = snap.get("startup_warm_error")
        row.startup_warm_error = (str(sw_err)[:255] if sw_err else None)
        lrcv = snap.get("last_request_cached_verification")
        row.last_request_cached_verification = (
            bool(lrcv) if lrcv is not None else None
        )
        if startup_warm_only:
            row.last_seen_at = _utc_now()
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        log.warning("db ready snapshot persist failed: %s", exc)
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:  # noqa: BLE001
            pass


def load_db_ready_operational_snapshot(*, reload_db: bool = True) -> dict[str, Any]:
    """Read snapshot for admin — merges durable row into cache when available."""
    if reload_db:
        try:
            from extensions import db
            from models import DbReadyOperationalSnapshot
            from schema_db_ready_operational import ensure_db_ready_operational_schema

            ensure_db_ready_operational_schema(db)
            row = db.session.get(DbReadyOperationalSnapshot, SNAPSHOT_ROW_ID)
            if row is not None:
                top_substages: list[Any] = []
                stage_classifications: list[Any] = []
                try:
                    raw_top = json.loads(row.top_substages_json or "[]")
                    if isinstance(raw_top, list):
                        top_substages = raw_top[:15]
                except (TypeError, ValueError):
                    top_substages = []
                try:
                    raw_cls = json.loads(row.stage_classifications_json or "[]")
                    if isinstance(raw_cls, list):
                        stage_classifications = raw_cls[:10]
                except (TypeError, ValueError):
                    stage_classifications = []
                with _cache_lock:
                    _cache.update(
                        {
                            "last_duration_ms": round(float(row.last_duration_ms or 0.0), 1),
                            "worst_duration_ms": round(float(row.worst_duration_ms or 0.0), 1),
                            "avg_duration_ms": round(float(row.avg_duration_ms or 0.0), 1),
                            "sample_count": int(row.sample_count or 0),
                            "last_stage": str(row.last_stage or ""),
                            "last_trace_id": str(row.last_trace_id or ""),
                            "last_lock_wait_ms": round(float(row.last_lock_wait_ms or 0.0), 1),
                            "last_query_count": int(row.last_query_count or 0),
                            "last_sql_ms": round(float(row.last_sql_ms or 0.0), 1),
                            "last_success": bool(row.last_success),
                            "last_failure_message": row.last_failure_message,
                            "status": str(row.status or "healthy"),
                            "last_seen_at": (
                                row.last_seen_at.isoformat()
                                if row.last_seen_at
                                else None
                            ),
                            "last_top_substage": str(row.last_top_substage or ""),
                            "last_top_substage_queries": int(
                                row.last_top_substage_queries or 0
                            ),
                            "last_top_substage_sql_ms": round(
                                float(row.last_top_substage_sql_ms or 0.0), 1
                            ),
                            "last_top_substage_elapsed_ms": round(
                                float(row.last_top_substage_elapsed_ms or 0.0), 1
                            ),
                            "top_substages": top_substages,
                            "stage_classifications": stage_classifications,
                            "startup_warm_status": str(
                                getattr(row, "startup_warm_status", None) or "not_started"
                            ),
                            "startup_warm_duration_ms": round(
                                float(getattr(row, "startup_warm_duration_ms", 0.0) or 0.0),
                                1,
                            ),
                            "startup_warm_error": getattr(row, "startup_warm_error", None),
                            "last_request_cached_verification": getattr(
                                row, "last_request_cached_verification", None
                            ),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            log.warning("db ready snapshot load failed: %s", exc)

    with _cache_lock:
        return dict(_cache)


def clear_db_ready_operational_snapshot_for_tests() -> None:
    with _cache_lock:
        _cache.update(
            {
                "last_duration_ms": 0.0,
                "worst_duration_ms": 0.0,
                "avg_duration_ms": 0.0,
                "sample_count": 0,
                "last_stage": "",
                "last_trace_id": "",
                "last_lock_wait_ms": 0.0,
                "last_query_count": 0,
                "last_sql_ms": 0.0,
                "last_success": True,
                "last_failure_message": None,
                "status": "healthy",
                "last_seen_at": None,
                "last_top_substage": "",
                "last_top_substage_queries": 0,
                "last_top_substage_sql_ms": 0.0,
                "last_top_substage_elapsed_ms": 0.0,
                "top_substages": [],
                "stage_classifications": [],
                "startup_warm_status": "not_started",
                "startup_warm_duration_ms": 0.0,
                "startup_warm_error": None,
                "last_request_cached_verification": None,
            }
        )
    from schema_db_ready_operational import reset_db_ready_operational_schema_guard_for_tests

    reset_db_ready_operational_schema_guard_for_tests()


__all__ = [
    "HEALTHY_MAX_MS",
    "SLOW_MAX_MS",
    "classify_db_ready_status",
    "clear_db_ready_operational_snapshot_for_tests",
    "load_db_ready_operational_snapshot",
    "record_db_ready_run",
    "record_startup_warm_snapshot",
    "status_emoji",
    "status_label_ar",
]
