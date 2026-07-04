# -*- coding: utf-8 -*-
"""
Dashboard Read Model Observability v1 — per-request read-path measurement.

Dashboard Read Model Governance V1 §7/§8 (observability + metrics contracts) and
Implementation Plan V1 items I1 (real production latency), I2 (read-path
distribution) and I5 (hot-slice degrade metrics).

This module is a read-only, in-process observation layer. It records what the
production read path already computed (route/snapshot/hot-slice timings and the
branch each request took) into bounded in-memory buffers, and exposes an
aggregated read model. It NEVER changes serving behavior:

* the single production hook (``record_dashboard_read_sample``) is invoked from
  ``dashboard_snapshot_read_v1.enforce_route_budget`` inside a ``try/except`` so
  observability can never break a dashboard response;
* no PII is stored (only endpoint name, read-path class, branch class, timings);
* buffers are bounded (``deque(maxlen=...)``), so memory is constant.

It also forwards the raw timings to the legacy
``operational_metrics_v1.record_dashboard_timing_sample`` pipe so the existing
``dashboard_status`` classifier reacts to *real* production latency (closing the
audit "dead latency metrics" blind spot, R2) without a second call site.
"""
from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any, Optional

# --- Read-path classes (I2) -------------------------------------------------
READ_PATH_SNAPSHOT = "snapshot"          # single indexed snapshot read (O(1))
READ_PATH_BOUNDED_LIVE = "bounded_live"  # snapshot + bounded hot-slice merge
READ_PATH_LIVE_ONLY = "live_only"        # reserved; no enforced endpoint uses it today
READ_PATHS = (READ_PATH_SNAPSHOT, READ_PATH_BOUNDED_LIVE, READ_PATH_LIVE_ONLY)

# --- Read-path branch classes (I2) -----------------------------------------
BRANCH_HIT = "hit"
BRANCH_STALE = "stale"
BRANCH_NO_SNAPSHOT = "no_snapshot"
BRANCH_MISSING_STORE_SLUG = "missing_store_slug"
BRANCH_DEGRADED = "degraded"
BRANCH_ROUTE_BUDGET_EXCEEDED = "route_budget_exceeded"
BRANCH_SNAPSHOT_READ_ERROR = "snapshot_read_error"
BRANCHES = (
    BRANCH_HIT,
    BRANCH_STALE,
    BRANCH_NO_SNAPSHOT,
    BRANCH_MISSING_STORE_SLUG,
    BRANCH_DEGRADED,
    BRANCH_ROUTE_BUDGET_EXCEEDED,
    BRANCH_SNAPSHOT_READ_ERROR,
)

# Enforced dashboard endpoints (stable set for per-endpoint decomposition).
DASHBOARD_ENDPOINTS = (
    "summary",
    "normal-carts",
    "widget-panel",
    "refresh-state",
    "store-connection",
)

_LAT_WINDOW = 256
_HOT_QUERIES_WINDOW = 256

ROUTE_WARNING_MS = 200.0
ROUTE_CRITICAL_MS = 500.0

_lock = Lock()

_route_ms_all: deque[float] = deque(maxlen=_LAT_WINDOW)
_route_ms_by_endpoint: dict[str, deque[float]] = {}
_snapshot_read_ms_all: deque[float] = deque(maxlen=_LAT_WINDOW)
_hot_slice_ms_all: deque[float] = deque(maxlen=_LAT_WINDOW)

_read_path_counts: dict[str, int] = {p: 0 for p in READ_PATHS}
_branch_counts: dict[str, int] = {b: 0 for b in BRANCHES}
_endpoint_stats: dict[str, dict[str, int]] = {}

_hot_reads = 0
_hot_merged = 0
_hot_snapshot_only = 0
_hot_degraded = 0
_hot_timeout = 0
_hot_limit_hit = 0
_hot_queries_samples: deque[int] = deque(maxlen=_HOT_QUERIES_WINDOW)

_total_requests = 0


def classify_read_path(endpoint: str) -> str:
    """normal-carts merges a bounded hot slice; everything else is pure snapshot."""
    return READ_PATH_BOUNDED_LIVE if (endpoint or "") == "normal-carts" else READ_PATH_SNAPSHOT


def classify_read_branch(snapshot_meta: dict[str, Any]) -> str:
    """Map the ``_snapshot`` decision metadata to one branch class (no inference)."""
    meta = snapshot_meta if isinstance(snapshot_meta, dict) else {}
    reason = str(meta.get("reason") or "")
    status = str(meta.get("status") or "")
    if meta.get("budget_exceeded") or reason == "route_budget_exceeded":
        return BRANCH_ROUTE_BUDGET_EXCEEDED
    if reason == "missing_store_slug":
        return BRANCH_MISSING_STORE_SLUG
    if reason == "no_snapshot" or status == "miss":
        return BRANCH_NO_SNAPSHOT
    if meta.get("stale") or reason == "stale_snapshot":
        return BRANCH_STALE
    if meta.get("degraded"):
        return BRANCH_DEGRADED
    return BRANCH_HIT


def _hot_slice_flags(*, degraded: bool, reason: str) -> tuple[bool, bool, bool]:
    """Derive (degraded, timeout, limit_hit) from hot-slice meta already computed."""
    r = str(reason or "")
    limit_hit = r.startswith("query_budget_exceeded")
    timeout = r.startswith("slow_")
    return bool(degraded), timeout, limit_hit


def record_dashboard_read_sample(
    *,
    endpoint: str,
    route_ms: Optional[float] = None,
    snapshot_read_ms: Optional[float] = None,
    read_path: Optional[str] = None,
    branch: str = BRANCH_HIT,
    hot_slice_ms: Optional[float] = None,
    hot_slice_queries: Optional[int] = None,
    hot_slice_degraded: bool = False,
    hot_slice_reason: str = "",
    data_freshness: Optional[str] = None,
) -> None:
    """
    Record one production read-path observation (I1 + I2 + I5).

    Called from the real serving path. Must never raise to the caller — the caller
    already wraps this defensively, and we keep the body cheap and lock-guarded.
    """
    global _total_requests, _hot_reads, _hot_merged, _hot_snapshot_only
    global _hot_degraded, _hot_timeout, _hot_limit_hit

    ep = (endpoint or "unknown")[:64]
    path = read_path or classify_read_path(ep)
    if path not in _read_path_counts:
        path = READ_PATH_SNAPSHOT
    br = branch if branch in _branch_counts else BRANCH_HIT

    with _lock:
        _total_requests += 1
        _read_path_counts[path] += 1
        _branch_counts[br] += 1

        stats = _endpoint_stats.setdefault(ep, {"total": 0})
        stats["total"] += 1
        stats[br] = stats.get(br, 0) + 1

        if route_ms is not None:
            val = max(0.0, float(route_ms))
            _route_ms_all.append(val)
            buf = _route_ms_by_endpoint.get(ep)
            if buf is None:
                buf = deque(maxlen=_LAT_WINDOW)
                _route_ms_by_endpoint[ep] = buf
            buf.append(val)
        if snapshot_read_ms is not None:
            _snapshot_read_ms_all.append(max(0.0, float(snapshot_read_ms)))

        if hot_slice_ms is not None or hot_slice_queries is not None or data_freshness is not None:
            _hot_reads += 1
            if data_freshness == "hot_merged":
                _hot_merged += 1
            elif data_freshness == "snapshot_only":
                _hot_snapshot_only += 1
            if hot_slice_ms is not None:
                _hot_slice_ms_all.append(max(0.0, float(hot_slice_ms)))
            if hot_slice_queries is not None:
                _hot_queries_samples.append(max(0, int(hot_slice_queries)))
            deg, timeout, limit_hit = _hot_slice_flags(
                degraded=hot_slice_degraded, reason=hot_slice_reason
            )
            if deg:
                _hot_degraded += 1
            if timeout:
                _hot_timeout += 1
            if limit_hit:
                _hot_limit_hit += 1

    # Feed the legacy timing pipe so classify_dashboard_status() reacts to real
    # production latency. Isolated so an import problem never affects serving.
    try:
        from services.operational_metrics_v1 import record_dashboard_timing_sample

        record_dashboard_timing_sample(
            route_ms=route_ms,
            snapshot_read_ms=snapshot_read_ms,
            hot_slice_ms=hot_slice_ms,
        )
    except Exception:  # noqa: BLE001
        pass


def _percentile(values: list[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[idx], 1)


def _latency_summary(samples: deque[float]) -> dict[str, Any]:
    vals = list(samples)
    if not vals:
        return {
            "sample_count": 0,
            "source": "no_samples",
            "last_ms": None,
            "p50_ms": None,
            "p90_ms": None,
            "p99_ms": None,
        }
    return {
        "sample_count": len(vals),
        "source": "production_read_path",
        "last_ms": round(vals[-1], 1),
        "p50_ms": _percentile(vals, 50),
        "p90_ms": _percentile(vals, 90),
        "p99_ms": _percentile(vals, 99),
    }


def _rate_pct(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return round(100.0 * numerator / denominator, 1)


def build_dashboard_read_observability_report() -> dict[str, Any]:
    """Aggregated read model: latency (I1) + read-path distribution (I2) + hot slice (I5)."""
    from services.dashboard_hot_slice_v1 import HOT_SLICE_MAX_QUERIES, HOT_SLICE_MAX_ROWS

    with _lock:
        route_all = _latency_summary(_route_ms_all)
        route_by_ep = {
            ep: _latency_summary(buf) for ep, buf in sorted(_route_ms_by_endpoint.items())
        }
        snap_read = _latency_summary(_snapshot_read_ms_all)
        hot_ms = _latency_summary(_hot_slice_ms_all)

        total = _total_requests
        read_path_dist = {
            p: {"count": _read_path_counts[p], "pct": _rate_pct(_read_path_counts[p], total)}
            for p in READ_PATHS
        }
        branch_dist = {
            b: {"count": _branch_counts[b], "pct": _rate_pct(_branch_counts[b], total)}
            for b in BRANCHES
        }
        endpoint_dist: dict[str, Any] = {}
        for ep, stats in sorted(_endpoint_stats.items()):
            ep_total = int(stats.get("total") or 0)
            endpoint_dist[ep] = {
                "total": ep_total,
                "hit_pct": _rate_pct(int(stats.get(BRANCH_HIT) or 0), ep_total),
                "stale_pct": _rate_pct(int(stats.get(BRANCH_STALE) or 0), ep_total),
                "no_snapshot_pct": _rate_pct(int(stats.get(BRANCH_NO_SNAPSHOT) or 0), ep_total),
                "degraded_pct": _rate_pct(
                    int(stats.get(BRANCH_DEGRADED) or 0)
                    + int(stats.get(BRANCH_ROUTE_BUDGET_EXCEEDED) or 0)
                    + int(stats.get(BRANCH_SNAPSHOT_READ_ERROR) or 0),
                    ep_total,
                ),
            }

        hot_reads = _hot_reads
        hot_queries = list(_hot_queries_samples)
        hot_block = {
            "reads": hot_reads,
            "hot_merged": _hot_merged,
            "snapshot_only": _hot_snapshot_only,
            "hot_merge_rate_pct": _rate_pct(_hot_merged, hot_reads),
            "degraded_rate_pct": _rate_pct(_hot_degraded, hot_reads),
            "timeout_rate_pct": _rate_pct(_hot_timeout, hot_reads),
            "limit_hit_rate_pct": _rate_pct(_hot_limit_hit, hot_reads),
            "degraded_count": _hot_degraded,
            "timeout_count": _hot_timeout,
            "limit_hit_count": _hot_limit_hit,
            "queries_p50": _percentile([float(v) for v in hot_queries], 50),
            "queries_p90": _percentile([float(v) for v in hot_queries], 90),
            "queries_max": max(hot_queries) if hot_queries else None,
            "queries_cap": HOT_SLICE_MAX_QUERIES,
            "rows_cap": HOT_SLICE_MAX_ROWS,
        }

    return {
        "sample_window": _LAT_WINDOW,
        "total_requests": total,
        "latency": {
            "route_ms": route_all,
            "route_ms_by_endpoint": route_by_ep,
            "snapshot_read_ms": snap_read,
            "hot_slice_ms": hot_ms,
            "route_warning_threshold_ms": ROUTE_WARNING_MS,
            "route_critical_threshold_ms": ROUTE_CRITICAL_MS,
        },
        "read_path_distribution": {
            "total_requests": total,
            "by_read_path": read_path_dist,
            "by_branch": branch_dist,
            "by_endpoint": endpoint_dist,
        },
        "hot_slice": hot_block,
    }


def reset_dashboard_read_observability_for_tests() -> None:
    global _total_requests, _hot_reads, _hot_merged, _hot_snapshot_only
    global _hot_degraded, _hot_timeout, _hot_limit_hit
    with _lock:
        _route_ms_all.clear()
        _route_ms_by_endpoint.clear()
        _snapshot_read_ms_all.clear()
        _hot_slice_ms_all.clear()
        for k in _read_path_counts:
            _read_path_counts[k] = 0
        for k in _branch_counts:
            _branch_counts[k] = 0
        _endpoint_stats.clear()
        _hot_queries_samples.clear()
        _total_requests = 0
        _hot_reads = 0
        _hot_merged = 0
        _hot_snapshot_only = 0
        _hot_degraded = 0
        _hot_timeout = 0
        _hot_limit_hit = 0


__all__ = [
    "BRANCH_DEGRADED",
    "BRANCH_HIT",
    "BRANCH_MISSING_STORE_SLUG",
    "BRANCH_NO_SNAPSHOT",
    "BRANCH_ROUTE_BUDGET_EXCEEDED",
    "BRANCH_SNAPSHOT_READ_ERROR",
    "BRANCH_STALE",
    "DASHBOARD_ENDPOINTS",
    "READ_PATH_BOUNDED_LIVE",
    "READ_PATH_LIVE_ONLY",
    "READ_PATH_SNAPSHOT",
    "ROUTE_CRITICAL_MS",
    "ROUTE_WARNING_MS",
    "build_dashboard_read_observability_report",
    "classify_read_branch",
    "classify_read_path",
    "record_dashboard_read_sample",
    "reset_dashboard_read_observability_for_tests",
]
