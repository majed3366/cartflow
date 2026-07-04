# -*- coding: utf-8 -*-
"""
Operational Metrics v1 — read-only platform health read model.

Aggregates existing in-process scheduler/snapshot signals and bounded DB metadata.
No hot-path instrumentation; no PII; no product behavior changes.
"""
from __future__ import annotations

import os
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from models import DashboardSnapshot

METRICS_WALL_BUDGET_MS = 5_000
MAX_STORE_SLUG_STALENESS_SAMPLE = 50
METRIC_CONTRACTS_VERSION = "v1"

STATUS_HEALTHY = "healthy"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"
STATUS_UNKNOWN = "unknown"

# --- Optional rolling dashboard timing samples (tests / future wiring; not hot-path) ---
_sample_lock = Lock()
_route_ms_samples: deque[float] = deque(maxlen=20)
_snapshot_read_ms_samples: deque[float] = deque(maxlen=20)
_hot_slice_ms_samples: deque[float] = deque(maxlen=20)


def record_dashboard_timing_sample(
    *,
    route_ms: Optional[float] = None,
    snapshot_read_ms: Optional[float] = None,
    hot_slice_ms: Optional[float] = None,
) -> None:
    """Append bounded timing samples (diagnostics only — not wired on hot path in v1)."""
    with _sample_lock:
        if route_ms is not None:
            _route_ms_samples.append(max(0.0, float(route_ms)))
        if snapshot_read_ms is not None:
            _snapshot_read_ms_samples.append(max(0.0, float(snapshot_read_ms)))
        if hot_slice_ms is not None:
            _hot_slice_ms_samples.append(max(0.0, float(hot_slice_ms)))


def clear_dashboard_timing_samples_for_tests() -> None:
    with _sample_lock:
        _route_ms_samples.clear()
        _snapshot_read_ms_samples.clear()
        _hot_slice_ms_samples.clear()


def _percentile(values: list[float], pct: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[idx], 1)


def _timing_sample_summary(samples: deque[float]) -> dict[str, Any]:
    vals = list(samples)
    if not vals:
        return {
            "sample_count": 0,
            "source": "log_only",
            "last_ms": None,
            "p50_ms": None,
            "p90_ms": None,
        }
    return {
        "sample_count": len(vals),
        "source": "in_process_buffer",
        "last_ms": round(vals[-1], 1),
        "p50_ms": _percentile(vals, 50),
        "p90_ms": _percentile(vals, 90),
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _deadline_expired(started: float, budget_ms: float) -> bool:
    return (time.perf_counter() - started) * 1000.0 >= budget_ms


def _table_exists(db_session: Any, table_name: str) -> bool:
    try:
        from sqlalchemy import inspect as sa_inspect

        bind = db_session.get_bind() if hasattr(db_session, "get_bind") else db_session.bind
        return table_name in sa_inspect(bind).get_table_names()
    except Exception:  # noqa: BLE001
        return True


def _worst_status(*statuses: str) -> str:
    order = {STATUS_CRITICAL: 3, STATUS_WARNING: 2, STATUS_UNKNOWN: 1, STATUS_HEALTHY: 0}
    best = STATUS_HEALTHY
    for s in statuses:
        if order.get(s, 0) > order.get(best, 0):
            best = s
    return best


def classify_db_status(pressure: dict[str, Any]) -> str:
    if not pressure.get("available"):
        return STATUS_UNKNOWN
    if pressure.get("exhausted") or int(pressure.get("timeout_count") or 0) > 0:
        return STATUS_CRITICAL
    level = str(pressure.get("pressure_level") or "ok")
    if level == "critical":
        return STATUS_CRITICAL
    if level in ("high", "elevated"):
        return STATUS_WARNING
    return STATUS_HEALTHY


def classify_data_growth_status(baseline: dict[str, Any]) -> str:
    risk = str(baseline.get("platform_growth_risk") or "LOW")
    if risk == "HIGH":
        return STATUS_WARNING
    if baseline.get("hot_snapshot_rows", 0) >= 500_000:
        return STATUS_CRITICAL
    if baseline.get("hot_snapshot_rows", 0) >= 100_000:
        return STATUS_WARNING
    return STATUS_HEALTHY


def classify_archive_status(archive: dict[str, Any]) -> str:
    if not archive.get("ok"):
        return STATUS_WARNING
    enabled = bool(archive.get("archive_enabled"))
    eligible = int(archive.get("rows_eligible_for_archive") or 0)
    hot = int(archive.get("total_snapshot_rows_hot") or 0)
    risk = str(archive.get("remaining_risk") or "LOW")
    if not enabled and hot >= 100_000:
        return STATUS_WARNING
    if risk == "HIGH" and eligible > 0 and not enabled:
        return STATUS_WARNING
    if archive.get("last_tick_error"):
        return STATUS_WARNING
    return STATUS_HEALTHY


def classify_snapshot_status(snapshot: dict[str, Any]) -> str:
    if snapshot.get("error"):
        return STATUS_WARNING
    stale_pct = float(snapshot.get("normal_carts_stale_pct") or 0.0)
    if stale_pct >= 80.0:
        return STATUS_CRITICAL
    if stale_pct >= 40.0:
        return STATUS_WARNING
    if int(snapshot.get("snapshot_loop_failure_count") or 0) >= 3:
        return STATUS_WARNING
    return STATUS_HEALTHY


def classify_scheduler_status(scheduler: dict[str, Any]) -> str:
    role = str(scheduler.get("process_role") or "unset")
    if role == "api":
        return STATUS_HEALTHY if scheduler.get("role_isolation_ok") else STATUS_WARNING
    if role not in ("scheduler",):
        if scheduler.get("production_like"):
            return STATUS_CRITICAL
        return STATUS_WARNING
    reasons = list(scheduler.get("failure_reasons") or [])
    critical_codes = {
        "database_error",
        "role_unset_production",
        "compliance_misconfigured",
        "policy_error",
    }
    if any(r in critical_codes for r in reasons):
        return STATUS_CRITICAL
    if reasons:
        return STATUS_WARNING
    if int(scheduler.get("snapshot_loop_failure_count") or 0) > 0:
        return STATUS_WARNING
    if not scheduler.get("due_scanner_enabled") and scheduler.get("production_like"):
        return STATUS_CRITICAL
    return STATUS_HEALTHY


def classify_dashboard_status(
    *,
    snapshot: dict[str, Any],
    timing: dict[str, Any],
) -> str:
    snap_status = classify_snapshot_status(snapshot)
    route_p90 = timing.get("route_ms", {}).get("p90_ms")
    if route_p90 is not None and float(route_p90) >= 500.0:
        return STATUS_CRITICAL
    if route_p90 is not None and float(route_p90) >= 200.0:
        return _worst_status(snap_status, STATUS_WARNING)
    return snap_status


def compute_overall_status(domain_statuses: dict[str, str]) -> str:
    return _worst_status(*domain_statuses.values())


def collect_db_pressure() -> dict[str, Any]:
    from services.db_pool_pressure_v1 import evaluate_db_pool_pressure, pool_pressure_thresholds

    pressure = evaluate_db_pool_pressure()
    thresholds = pool_pressure_thresholds()
    return {
        "pool_size": pressure.get("pool_size"),
        "max_connections": pressure.get("max_connections"),
        "checked_out": pressure.get("checked_out"),
        "available_slots": pressure.get("available_slots"),
        "util_pct": pressure.get("utilization_pct"),
        "pressure_level": pressure.get("pressure_level"),
        "circuit_breaker_open": pressure.get("circuit_breaker_open"),
        "timeout_count": pressure.get("timeout_count"),
        "exhausted": pressure.get("exhausted"),
        "thresholds": thresholds,
        "status": classify_db_status(pressure),
    }


def collect_scheduler_health() -> dict[str, Any]:
    from services.recovery_process_role_v1 import evaluate_scheduler_ownership_policy
    from services.scheduler_heartbeat_v1 import build_scheduler_heartbeat_snapshot
    from services.scheduler_snapshot_loop_health_v1 import build_scheduler_snapshot_loop_status

    policy = evaluate_scheduler_ownership_policy(force=False)
    heartbeat = build_scheduler_heartbeat_snapshot()
    loop = build_scheduler_snapshot_loop_status()
    role = str(policy.get("role") or loop.get("process_role") or "unset")
    production_like = bool(policy.get("production_like"))

    return {
        "process_role": role,
        "production_like": production_like,
        "role_isolation_ok": role in ("api", "scheduler"),
        "due_scanner_enabled": bool(heartbeat.get("due_scanner_enabled")),
        "resume_enabled": bool(heartbeat.get("resume_enabled")),
        "scanner_status": heartbeat.get("scanner_status"),
        "scanner_loop_running": heartbeat.get("scanner_loop_running"),
        "last_scan_at": heartbeat.get("last_scan_at"),
        "scanner_last_error": heartbeat.get("scanner_last_error"),
        "overdue_scheduled_count": int(heartbeat.get("overdue_scheduled_count") or 0),
        "stuck_running_count": int(heartbeat.get("stuck_running_count") or 0),
        "failure_reasons": list(heartbeat.get("failure_reasons") or []),
        "snapshot_builder_enabled": bool(loop.get("dashboard_snapshot_builder_enabled")),
        "snapshot_loop_running": bool(loop.get("loop_running")),
        "snapshot_loop_last_tick_at": loop.get("snapshot_loop_last_tick_at"),
        "snapshot_loop_last_success_at": loop.get("snapshot_loop_last_success_at"),
        "snapshot_loop_last_error_at": loop.get("snapshot_loop_last_error_at"),
        "snapshot_loop_last_error": loop.get("snapshot_loop_last_error"),
        "snapshot_loop_tick_count": int(loop.get("snapshot_loop_tick_count") or 0),
        "snapshot_loop_success_count": int(loop.get("snapshot_loop_success_count") or 0),
        "snapshot_loop_failure_count": int(loop.get("snapshot_loop_failure_count") or 0),
        "last_snapshot_write_generated_at": loop.get("last_snapshot_write_generated_at"),
        "status": classify_scheduler_status(
            {
                "process_role": role,
                "production_like": production_like,
                "role_isolation_ok": role in ("api", "scheduler"),
                "due_scanner_enabled": bool(heartbeat.get("due_scanner_enabled")),
                "failure_reasons": heartbeat.get("failure_reasons"),
                "snapshot_loop_failure_count": loop.get("snapshot_loop_failure_count"),
            }
        ),
    }


def assess_snapshot_health(
    db_session: Any,
    *,
    deadline_started: Optional[float] = None,
    deadline_ms: float = METRICS_WALL_BUDGET_MS,
) -> dict[str, Any]:
    from services.dashboard_snapshot_v1 import (
        SNAPSHOT_TYPE_NORMAL_CARTS,
        snapshot_builder_failsafe_seconds,
        snapshot_row_is_stale,
    )

    try:
        now = _utc_now()
        failsafe_cutoff = now - timedelta(seconds=snapshot_builder_failsafe_seconds())

        newest = db_session.query(func.max(DashboardSnapshot.generated_at)).scalar()
        total_rows = int(db_session.query(DashboardSnapshot).count())

        if _deadline_expired(deadline_started or time.perf_counter(), deadline_ms):
            return {"error": "deadline", "partial": True, "total_snapshot_rows": total_rows}

        pair_rows = (
            db_session.query(
                DashboardSnapshot.store_slug,
                func.max(DashboardSnapshot.generated_at).label("max_gen"),
            )
            .filter(DashboardSnapshot.snapshot_type == SNAPSHOT_TYPE_NORMAL_CARTS)
            .group_by(DashboardSnapshot.store_slug)
            .limit(MAX_STORE_SLUG_STALENESS_SAMPLE)
            .all()
        )

        stale_count = 0
        missing_fresh = 0
        for slug, max_gen in pair_rows:
            if max_gen is None:
                missing_fresh += 1
                stale_count += 1
                continue
            gen = max_gen
            if gen.tzinfo is None:
                gen = gen.replace(tzinfo=timezone.utc)
            is_stale = gen < failsafe_cutoff.replace(tzinfo=timezone.utc)
            if not is_stale:
                row = (
                    db_session.query(DashboardSnapshot)
                    .filter(
                        DashboardSnapshot.store_slug == slug,
                        DashboardSnapshot.snapshot_type == SNAPSHOT_TYPE_NORMAL_CARTS,
                        DashboardSnapshot.generated_at == max_gen,
                    )
                    .order_by(DashboardSnapshot.id.desc())
                    .limit(1)
                    .first()
                )
                if row is not None and snapshot_row_is_stale(row, now=now):
                    is_stale = True
            if is_stale:
                stale_count += 1

        sampled = len(pair_rows)
        stale_pct = round(100.0 * stale_count / sampled, 1) if sampled else 0.0
        data_freshness_s = None
        if newest is not None:
            ng = newest
            if ng.tzinfo is None:
                ng = ng.replace(tzinfo=timezone.utc)
            data_freshness_s = int((now - ng.astimezone(timezone.utc)).total_seconds())

        loop = {}
        try:
            from services.scheduler_snapshot_loop_health_v1 import (
                build_scheduler_snapshot_loop_status,
            )

            loop = build_scheduler_snapshot_loop_status()
        except Exception:  # noqa: BLE001
            pass

        return {
            "total_snapshot_rows": total_rows,
            "stores_sampled": sampled,
            "normal_carts_stale_count": stale_count,
            "normal_carts_stale_pct": stale_pct,
            "newest_generated_at": _iso(newest),
            "data_freshness_seconds": data_freshness_s,
            "snapshot_stale_flag": stale_pct >= 40.0,
            "failsafe_seconds": snapshot_builder_failsafe_seconds(),
            "snapshot_loop_failure_count": int(loop.get("snapshot_loop_failure_count") or 0),
            "snapshot_loop_last_error": loop.get("snapshot_loop_last_error"),
            "status": classify_snapshot_status(
                {
                    "normal_carts_stale_pct": stale_pct,
                    "snapshot_loop_failure_count": loop.get("snapshot_loop_failure_count"),
                }
            ),
        }
    except SQLAlchemyError as exc:
        db_session.rollback()
        return {"error": "query_failed", "detail": type(exc).__name__}


def collect_archive_health(db_session: Any) -> dict[str, Any]:
    if not _table_exists(db_session, "dashboard_snapshots_archive"):
        hot = 0
        try:
            hot = int(db_session.query(DashboardSnapshot).count())
        except SQLAlchemyError:
            db_session.rollback()
        from services.dashboard_snapshot_archive_v1 import dashboard_snapshot_archive_enabled

        return {
            "ok": True,
            "archive_table_present": False,
            "archive_enabled": dashboard_snapshot_archive_enabled(),
            "total_snapshot_rows_hot": hot,
            "total_snapshot_rows_archive": None,
            "rows_eligible_for_archive": None,
            "remaining_risk": "UNKNOWN",
            "last_tick": None,
            "last_tick_error": None,
            "status": STATUS_UNKNOWN,
        }

    from services.dashboard_snapshot_archive_v1 import assess_dashboard_snapshot_archive_status

    status = assess_dashboard_snapshot_archive_status(db_session, include_last_tick=True)
    last_tick = status.get("last_tick") if isinstance(status.get("last_tick"), dict) else {}
    last_tick_error = None
    if isinstance(last_tick, dict) and not last_tick.get("ok", True):
        last_tick_error = str(last_tick.get("error") or "archive_tick_failed")[:200]

    out = {
        "archive_table_present": True,
        "archive_enabled": bool(status.get("archive_enabled")),
        "retention_days": status.get("retention_days"),
        "total_snapshot_rows_hot": status.get("total_snapshot_rows_hot"),
        "total_snapshot_rows_archive": status.get("total_snapshot_rows_archive"),
        "rows_eligible_for_archive": status.get("rows_eligible_for_archive"),
        "remaining_risk": status.get("remaining_risk"),
        "last_tick": last_tick or None,
        "last_tick_error": last_tick_error,
        "last_tick_duration_ms": (
            last_tick.get("duration_ms") if isinstance(last_tick, dict) else None
        ),
        "last_tick_rows_archived": (
            last_tick.get("rows_archived") if isinstance(last_tick, dict) else None
        ),
    }
    out["ok"] = bool(status.get("ok", True))
    out["status"] = classify_archive_status({**out, "ok": out["ok"]})
    return out


def collect_data_growth_baseline(
    db_session: Any,
    *,
    deadline_started: Optional[float] = None,
    deadline_ms: float = METRICS_WALL_BUDGET_MS,
) -> dict[str, Any]:
    from models import CartRecoveryLog, RecoveryTruthTimelineEvent

    baseline: dict[str, Any] = {
        "hot_snapshot_rows": 0,
        "archive_snapshot_rows": None,
        "cart_recovery_log_rows": 0,
        "timeline_event_rows": 0,
        "platform_growth_risk": "LOW",
    }
    try:
        baseline["hot_snapshot_rows"] = int(db_session.query(DashboardSnapshot).count())
        if _deadline_expired(deadline_started or time.perf_counter(), deadline_ms):
            baseline["partial"] = True
            return baseline

        if _table_exists(db_session, "dashboard_snapshots_archive"):
            try:
                from models import DashboardSnapshotArchive

                baseline["archive_snapshot_rows"] = int(
                    db_session.query(DashboardSnapshotArchive).count()
                )
            except SQLAlchemyError:
                db_session.rollback()
                baseline["archive_snapshot_rows"] = None

        baseline["cart_recovery_log_rows"] = int(db_session.query(CartRecoveryLog).count())
        baseline["timeline_event_rows"] = int(
            db_session.query(RecoveryTruthTimelineEvent).count()
        )

        hot = baseline["hot_snapshot_rows"]
        if hot >= 500_000:
            baseline["platform_growth_risk"] = "HIGH"
        elif hot >= 100_000:
            baseline["platform_growth_risk"] = "MEDIUM"

        baseline["status"] = classify_data_growth_status(baseline)
        return baseline
    except SQLAlchemyError as exc:
        db_session.rollback()
        baseline["error"] = type(exc).__name__
        baseline["status"] = STATUS_UNKNOWN
        return baseline


def collect_snapshot_generation_metrics() -> dict[str, Any]:
    """Snapshot Generation Governance SG-4 — write/skip/touch reduction metrics."""
    try:
        from services.dashboard_snapshot_generation_metrics_v1 import (
            snapshot_generation_metrics_report,
        )

        report = snapshot_generation_metrics_report()
    except Exception as exc:  # noqa: BLE001
        return {"error": type(exc).__name__}
    report["status"] = STATUS_HEALTHY
    return report


def collect_provider_reliability_metrics() -> dict[str, Any]:
    """Provider Reliability Governance V1 §6+§7 — denominator-based reliability read-model."""
    try:
        from services.provider_reliability_metrics_v1 import (
            build_provider_reliability_report,
        )

        return build_provider_reliability_report()
    except Exception as exc:  # noqa: BLE001
        return {"status": STATUS_UNKNOWN, "error": type(exc).__name__}


def collect_dashboard_timing_metrics() -> dict[str, Any]:
    with _sample_lock:
        route = _timing_sample_summary(_route_ms_samples)
        snap = _timing_sample_summary(_snapshot_read_ms_samples)
        hot = _timing_sample_summary(_hot_slice_ms_samples)

    from services.dashboard_hot_slice_v1 import HOT_SLICE_MAX_QUERIES, HOT_SLICE_MAX_ROWS

    return {
        "route_ms": route,
        "snapshot_read_ms": snap,
        "hot_slice_ms": hot,
        "hot_slice_rows_cap": HOT_SLICE_MAX_ROWS,
        "hot_slice_queries_cap": HOT_SLICE_MAX_QUERIES,
        "route_ms_warning_threshold": 200.0,
        "route_ms_critical_threshold": 500.0,
    }


def collect_failure_markers(
    *,
    scheduler: dict[str, Any],
    snapshot: dict[str, Any],
    archive: dict[str, Any],
) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []

    if scheduler.get("scanner_last_error"):
        markers.append(
            {
                "code": "scheduler.scanner_error",
                "at": scheduler.get("last_scan_at"),
                "detail": str(scheduler["scanner_last_error"])[:200],
            }
        )
    if scheduler.get("snapshot_loop_last_error"):
        markers.append(
            {
                "code": "scheduler.snapshot_builder_error",
                "at": scheduler.get("snapshot_loop_last_error_at"),
                "detail": str(scheduler["snapshot_loop_last_error"])[:200],
            }
        )
    if snapshot.get("snapshot_loop_last_error"):
        markers.append(
            {
                "code": "snapshot.write_failed",
                "at": None,
                "detail": str(snapshot["snapshot_loop_last_error"])[:200],
            }
        )
    if archive.get("last_tick_error"):
        markers.append(
            {
                "code": "archive.failed",
                "at": None,
                "detail": str(archive["last_tick_error"])[:200],
            }
        )
    for reason in scheduler.get("failure_reasons") or []:
        markers.append(
            {
                "code": f"scheduler.{reason}",
                "at": scheduler.get("last_scan_at"),
                "detail": reason,
            }
        )
    return markers[:20]


def build_operational_metrics_report(db_session: Any) -> dict[str, Any]:
    """Full read-only operational metrics payload."""
    t0 = time.perf_counter()
    now = _utc_now()

    db_pressure = collect_db_pressure()
    scheduler = collect_scheduler_health()
    timing = collect_dashboard_timing_metrics()
    snapshot = assess_snapshot_health(db_session, deadline_started=t0)
    snapshot_generation = collect_snapshot_generation_metrics()
    provider_reliability = collect_provider_reliability_metrics()
    archive = collect_archive_health(db_session)
    data_growth = collect_data_growth_baseline(db_session, deadline_started=t0)

    dashboard_status = classify_dashboard_status(snapshot=snapshot, timing=timing)
    scheduler_status = str(scheduler.get("status") or STATUS_UNKNOWN)
    snapshot_status = str(snapshot.get("status") or STATUS_UNKNOWN)
    archive_status = str(archive.get("status") or STATUS_UNKNOWN)
    data_growth_status = str(data_growth.get("status") or STATUS_UNKNOWN)
    db_status = str(db_pressure.get("status") or STATUS_UNKNOWN)

    domain_statuses = {
        "dashboard": dashboard_status,
        "scheduler": scheduler_status,
        "snapshot": snapshot_status,
        "archive": archive_status,
        "data_growth": data_growth_status,
        "db": db_status,
    }
    overall = compute_overall_status(domain_statuses)
    failure_markers = collect_failure_markers(
        scheduler=scheduler, snapshot=snapshot, archive=archive
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    partial = elapsed_ms >= METRICS_WALL_BUDGET_MS or bool(
        snapshot.get("partial") or data_growth.get("partial")
    )

    summary = {
        "ok": overall != STATUS_CRITICAL,
        "overall_status": overall,
        "dashboard_status": dashboard_status,
        "scheduler_status": scheduler_status,
        "snapshot_status": snapshot_status,
        "archive_status": archive_status,
        "data_growth_status": data_growth_status,
        "db_status": db_status,
    }

    return {
        "ok": True,
        "read_only": True,
        "metric_contracts_version": METRIC_CONTRACTS_VERSION,
        "measured_at": now.isoformat(),
        "measurement_elapsed_ms": elapsed_ms,
        "measurement_wall_budget_ms": METRICS_WALL_BUDGET_MS,
        "measurement_partial": partial,
        "process_role": scheduler.get("process_role"),
        "summary": summary,
        "metrics": {
            "dashboard": {
                **timing,
                "data_freshness_seconds": snapshot.get("data_freshness_seconds"),
                "snapshot_stale_flag": snapshot.get("snapshot_stale_flag"),
                "normal_carts_stale_pct": snapshot.get("normal_carts_stale_pct"),
            },
            "scheduler": scheduler,
            "snapshot": snapshot,
            "snapshot_generation": snapshot_generation,
            "provider_reliability": provider_reliability,
            "archive": archive,
            "data_growth": data_growth,
            "db": db_pressure,
        },
        "failure_markers": failure_markers,
    }


def list_metric_contracts() -> list[dict[str, Any]]:
    """Metric name registry for docs and Admin UI future consumption."""
    return [
        {
            "name": "dashboard.normal_carts.route_ms",
            "owner": "dashboard_snapshot_read_v1",
            "source": "in_process_buffer_or_logs",
            "unit": "ms",
            "frequency": "per_request",
            "acceptable_range": "0-200",
            "warning_threshold": 200,
            "critical_threshold": 500,
        },
        {
            "name": "dashboard.snapshot.read_ms",
            "owner": "dashboard_snapshot_v1",
            "source": "in_process_buffer_or_logs",
            "unit": "ms",
            "frequency": "per_request",
            "acceptable_range": "0-50",
            "warning_threshold": 50,
            "critical_threshold": 150,
        },
        {
            "name": "dashboard.hot_slice.rows",
            "owner": "dashboard_hot_slice_v1",
            "source": "request_meta",
            "unit": "count",
            "frequency": "per_request",
            "acceptable_range": "0-25",
            "warning_threshold": 25,
            "critical_threshold": 25,
        },
        {
            "name": "dashboard.hot_slice.ms",
            "owner": "dashboard_hot_slice_v1",
            "source": "in_process_buffer_or_logs",
            "unit": "ms",
            "frequency": "per_request",
            "acceptable_range": "0-80",
            "warning_threshold": 80,
            "critical_threshold": 150,
        },
        {
            "name": "dashboard.hot_slice.queries",
            "owner": "dashboard_hot_slice_v1",
            "source": "request_meta",
            "unit": "count",
            "frequency": "per_request",
            "acceptable_range": "0-15",
            "warning_threshold": 15,
            "critical_threshold": 15,
        },
        {
            "name": "dashboard.snapshot.stale",
            "owner": "dashboard_snapshot_v1",
            "source": "db_metadata",
            "unit": "boolean",
            "frequency": "on_demand",
            "acceptable_range": "false",
            "warning_threshold": "stale_pct>=40",
            "critical_threshold": "stale_pct>=80",
        },
        {
            "name": "scheduler.snapshot_builder.duration_ms",
            "owner": "dashboard_snapshot_builder_v1",
            "source": "scheduler_loop_tick",
            "unit": "ms",
            "frequency": "per_tick",
            "acceptable_range": "0-30000",
            "warning_threshold": 45000,
            "critical_threshold": 120000,
        },
        {
            "name": "scheduler.snapshot_builder.stores_built",
            "owner": "dashboard_snapshot_builder_v1",
            "source": "scheduler_loop_tick",
            "unit": "count",
            "frequency": "per_tick",
            "acceptable_range": ">=1 when due",
            "warning_threshold": 0,
            "critical_threshold": 0,
        },
        {
            "name": "scheduler.archive.rows_eligible",
            "owner": "dashboard_snapshot_archive_v1",
            "source": "db_count",
            "unit": "count",
            "frequency": "on_demand",
            "acceptable_range": "bounded by retention",
            "warning_threshold": 10000,
            "critical_threshold": 100000,
        },
        {
            "name": "scheduler.archive.rows_archived",
            "owner": "dashboard_snapshot_archive_v1",
            "source": "last_tick_result",
            "unit": "count",
            "frequency": "per_tick",
            "acceptable_range": ">=0",
            "warning_threshold": None,
            "critical_threshold": None,
        },
        {
            "name": "db.pool.util_pct",
            "owner": "db_pool_pressure_v1",
            "source": "sqlalchemy_pool",
            "unit": "percent",
            "frequency": "on_demand",
            "acceptable_range": "0-60",
            "warning_threshold": 75,
            "critical_threshold": 85,
        },
        {
            "name": "db.pool.pressure_level",
            "owner": "db_pool_pressure_v1",
            "source": "sqlalchemy_pool",
            "unit": "enum",
            "frequency": "on_demand",
            "acceptable_range": "ok",
            "warning_threshold": "elevated|high",
            "critical_threshold": "critical",
        },
        {
            "name": "data_growth.dashboard_snapshots.hot_rows",
            "owner": "data_growth_measurement_v1",
            "source": "db_count",
            "unit": "count",
            "frequency": "on_demand",
            "acceptable_range": "<100000",
            "warning_threshold": 100000,
            "critical_threshold": 500000,
        },
        {
            "name": "data_growth.dashboard_snapshots.archive_rows",
            "owner": "dashboard_snapshot_archive_v1",
            "source": "db_count",
            "unit": "count",
            "frequency": "on_demand",
            "acceptable_range": "growing with retention",
            "warning_threshold": None,
            "critical_threshold": None,
        },
        {
            "name": "snapshot_generation.rows_written",
            "owner": "dashboard_snapshot_change_v1",
            "source": "in_process_counter",
            "unit": "count",
            "frequency": "per_generation",
            "acceptable_range": "tracks real change events",
            "warning_threshold": None,
            "critical_threshold": None,
        },
        {
            "name": "snapshot_generation.rows_avoided",
            "owner": "dashboard_snapshot_change_v1",
            "source": "in_process_counter",
            "unit": "count",
            "frequency": "per_generation",
            "acceptable_range": "identical rewrites skipped/touched",
            "warning_threshold": None,
            "critical_threshold": None,
        },
        {
            "name": "snapshot_generation.write_reduction_pct",
            "owner": "dashboard_snapshot_change_v1",
            "source": "in_process_counter",
            "unit": "percent",
            "frequency": "on_demand",
            "acceptable_range": "higher is better (idle stores near 100)",
            "warning_threshold": None,
            "critical_threshold": None,
        },
        {
            "name": "snapshot_generation.change_detection_hit_rate_pct",
            "owner": "dashboard_snapshot_change_v1",
            "source": "in_process_counter",
            "unit": "percent",
            "frequency": "on_demand",
            "acceptable_range": "0-100",
            "warning_threshold": None,
            "critical_threshold": None,
        },
        {
            "name": "provider_reliability.acceptance_rate",
            "owner": "provider_reliability_metrics_v1",
            "source": "db_ratio",
            "unit": "percent",
            "frequency": "on_demand",
            "acceptable_range": "0-100 (null when no sends)",
            "warning_threshold": 95,
            "critical_threshold": 80,
        },
        {
            "name": "provider_reliability.delivery_rate",
            "owner": "provider_reliability_metrics_v1",
            "source": "db_ratio",
            "unit": "percent",
            "frequency": "on_demand",
            "acceptable_range": "0-100 (requires delivery webhooks)",
            "warning_threshold": None,
            "critical_threshold": None,
        },
        {
            "name": "provider_reliability.retry_exhaustion_rate",
            "owner": "provider_retry_ledger_v1",
            "source": "db_ratio",
            "unit": "percent",
            "frequency": "on_demand",
            "acceptable_range": "lower is better",
            "warning_threshold": None,
            "critical_threshold": None,
        },
        {
            "name": "provider_reliability.unknown_state_rate",
            "owner": "provider_reliability_metrics_v1",
            "source": "db_ratio",
            "unit": "percent",
            "frequency": "on_demand",
            "acceptable_range": "lower is better",
            "warning_threshold": None,
            "critical_threshold": None,
        },
    ]


__all__ = [
    "METRICS_WALL_BUDGET_MS",
    "METRIC_CONTRACTS_VERSION",
    "STATUS_CRITICAL",
    "STATUS_HEALTHY",
    "STATUS_UNKNOWN",
    "STATUS_WARNING",
    "assess_snapshot_health",
    "build_operational_metrics_report",
    "classify_archive_status",
    "classify_dashboard_status",
    "classify_data_growth_status",
    "classify_db_status",
    "classify_scheduler_status",
    "classify_snapshot_status",
    "clear_dashboard_timing_samples_for_tests",
    "collect_archive_health",
    "collect_data_growth_baseline",
    "collect_db_pressure",
    "collect_failure_markers",
    "collect_provider_reliability_metrics",
    "collect_scheduler_health",
    "collect_snapshot_generation_metrics",
    "compute_overall_status",
    "list_metric_contracts",
    "record_dashboard_timing_sample",
]
