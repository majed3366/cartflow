# -*- coding: utf-8 -*-
"""
Data Growth Measurement v1 — read-only table growth, snapshot accumulation,
and log density metrics. Diagnostic only — no writes, archives, or deletes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

from models import (
    AbandonedCart,
    CartRecoveryLog,
    DashboardSnapshot,
    MovementSnapshot,
    PurchaseTruthRecord,
    RecoverySchedule,
    RecoveryTruthTimelineEvent,
    Store,
)

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"

# Thresholds from docs/data_growth_governance_v1.md
TABLE_THRESHOLDS: dict[str, tuple[int, int]] = {
    "abandoned_carts": (500_000, 2_000_000),
    "cart_recovery_logs": (5_000_000, 20_000_000),
    "recovery_truth_timeline_events": (5_000_000, 20_000_000),
    "recovery_schedules": (100_000, 500_000),
    "dashboard_snapshots": (100_000, 1_000_000),
    "movement_snapshots": (100_000, 500_000),
    "purchase_truth_records": (200_000, 1_000_000),
    "stores": (10_000, 50_000),
}


@dataclass(frozen=True, slots=True)
class TableSizeMetrics:
    table: str
    row_count: int = 0
    estimated_bytes: Optional[int] = None
    oldest_at: Optional[datetime] = None
    newest_at: Optional[datetime] = None
    rows_added_today: int = 0
    rows_added_last_7_days: int = 0
    rows_added_last_30_days: int = 0
    daily_growth_estimate: float = 0.0
    warning_threshold: Optional[int] = None
    critical_threshold: Optional[int] = None
    threshold_status: str = "unknown"
    risk_score: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "row_count": self.row_count,
            "estimated_bytes": self.estimated_bytes,
            "estimated_mb": round(self.estimated_bytes / (1024 * 1024), 2)
            if self.estimated_bytes
            else None,
            "oldest_at": self.oldest_at.isoformat() if self.oldest_at else None,
            "newest_at": self.newest_at.isoformat() if self.newest_at else None,
            "rows_added_today": self.rows_added_today,
            "rows_added_last_7_days": self.rows_added_last_7_days,
            "rows_added_last_30_days": self.rows_added_last_30_days,
            "daily_growth_estimate": round(self.daily_growth_estimate, 2),
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "threshold_status": self.threshold_status,
            "risk_score": self.risk_score,
        }


RISK_UNKNOWN = "UNKNOWN"

MEASUREMENT_WALL_BUDGET_MS = 8_000
TOP_STORE_SLUG_LIMIT = 20
TOP_VERSION_ACCUMULATOR_LIMIT = 10


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat()


def _deadline_expired(started: float, budget_ms: float) -> bool:
    import time

    return (time.perf_counter() - started) * 1000.0 >= budget_ms


def compute_platform_growth_risk_score(
    *,
    tables: list[TableSizeMetrics],
    snapshot_acc: dict[str, Any],
    log_growth: dict[str, Any],
) -> str:
    """Aggregate LOW / MEDIUM / HIGH from table + structural signals."""
    scores = [
        t.risk_score
        for t in tables
        if t.risk_score in (RISK_LOW, RISK_MEDIUM, RISK_HIGH)
    ]
    scores.append(str(snapshot_acc.get("risk_score") or RISK_UNKNOWN))
    for block in (log_growth.get("cart_recovery_logs"), log_growth.get("recovery_truth_timeline_events")):
        if isinstance(block, dict):
            scores.append(str(block.get("risk_score") or RISK_UNKNOWN))
    if snapshot_acc.get("append_only_accumulation_confirmed"):
        scores.append(RISK_HIGH)
    if RISK_HIGH in scores:
        return RISK_HIGH
    if RISK_MEDIUM in scores:
        return RISK_MEDIUM
    return RISK_LOW


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _start_of_day(now: datetime) -> datetime:
    n = _naive(now)
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def _threshold_status(row_count: int, warn: int, crit: int) -> str:
    if row_count >= crit:
        return "critical"
    if row_count >= warn:
        return "warning"
    return "ok"


def _risk_score_for_table(
    *,
    table: str,
    row_count: int,
    rows_last_7_days: int,
    rows_last_30_days: int,
    threshold_status: str,
) -> str:
    hot_path_tables = frozenset(
        {
            "dashboard_snapshots",
            "cart_recovery_logs",
            "recovery_truth_timeline_events",
            "abandoned_carts",
            "movement_snapshots",
        }
    )
    if threshold_status == "critical":
        return RISK_HIGH
    if table in hot_path_tables:
        if rows_last_7_days >= 1000 or rows_last_30_days >= 5000:
            return RISK_HIGH
        if threshold_status == "warning" or rows_last_7_days >= 100:
            return RISK_MEDIUM
    if threshold_status == "warning":
        return RISK_MEDIUM
    if rows_last_30_days >= 500:
        return RISK_MEDIUM
    return RISK_LOW


def _pg_table_bytes(db_session: Any, table_name: str) -> Optional[int]:
    try:
        dialect = db_session.bind.dialect.name if db_session.bind else ""
        if dialect != "postgresql":
            return None
        row = db_session.execute(
            text(
                "SELECT pg_total_relation_size(CAST(:tbl AS regclass)) AS sz"
            ),
            {"tbl": table_name},
        ).mappings().first()
        if row and row.get("sz") is not None:
            return int(row["sz"])
    except SQLAlchemyError:
        db_session.rollback()
    return None


def _count_since(
    db_session: Any,
    model: Any,
    ts_attr: Any,
    since: datetime,
) -> int:
    return (
        db_session.query(model)
        .filter(ts_attr >= _naive(since))
        .count()
    )


def assess_table_size(
    db_session: Any,
    *,
    table_name: str,
    model: Any,
    ts_attr: Any,
    now: Optional[datetime] = None,
) -> TableSizeMetrics:
    when = now or _utc_now()
    start_today = _start_of_day(when)
    start_7 = _naive(when) - timedelta(days=7)
    start_30 = _naive(when) - timedelta(days=30)
    warn, crit = TABLE_THRESHOLDS.get(table_name, (None, None))

    try:
        total = db_session.query(model).count()
        rows_today = _count_since(db_session, model, ts_attr, start_today)
        rows_7 = _count_since(db_session, model, ts_attr, start_7)
        rows_30 = _count_since(db_session, model, ts_attr, start_30)
        oldest = db_session.query(func.min(ts_attr)).scalar()
        newest = db_session.query(func.max(ts_attr)).scalar()
        est_bytes = _pg_table_bytes(db_session, table_name)
        daily = rows_30 / 30.0 if rows_30 else (rows_7 / 7.0 if rows_7 else 0.0)
        t_status = _threshold_status(total, warn or 0, crit or 0) if warn else "unknown"
        risk = _risk_score_for_table(
            table=table_name,
            row_count=total,
            rows_last_7_days=rows_7,
            rows_last_30_days=rows_30,
            threshold_status=t_status if warn else "ok",
        )
        return TableSizeMetrics(
            table=table_name,
            row_count=total,
            estimated_bytes=est_bytes,
            oldest_at=oldest,
            newest_at=newest,
            rows_added_today=rows_today,
            rows_added_last_7_days=rows_7,
            rows_added_last_30_days=rows_30,
            daily_growth_estimate=daily,
            warning_threshold=warn,
            critical_threshold=crit,
            threshold_status=t_status,
            risk_score=risk,
        )
    except SQLAlchemyError:
        db_session.rollback()
        return TableSizeMetrics(table=table_name, risk_score=RISK_UNKNOWN)


def assess_cf_behavioral(db_session: Any) -> dict[str, Any]:
    """Nested cf_behavioral in abandoned_carts.raw_payload — not a separate table."""
    try:
        total_carts = db_session.query(AbandonedCart).count()
        with_behavioral = (
            db_session.query(AbandonedCart)
            .filter(AbandonedCart.raw_payload.isnot(None))
            .filter(AbandonedCart.raw_payload.contains('"cf_behavioral"'))
            .count()
        )
        payload_sizes = (
            db_session.query(func.avg(func.length(AbandonedCart.raw_payload)))
            .scalar()
        )
        behavioral_sizes = (
            db_session.query(func.avg(func.length(AbandonedCart.raw_payload)))
            .filter(AbandonedCart.raw_payload.contains('"cf_behavioral"'))
            .scalar()
        )
        return {
            "storage": "nested in abandoned_carts.raw_payload",
            "abandoned_carts_total": total_carts,
            "carts_with_cf_behavioral": with_behavioral,
            "cf_behavioral_coverage_pct": round(
                100.0 * with_behavioral / total_carts, 2
            )
            if total_carts
            else 0.0,
            "avg_raw_payload_bytes": round(float(payload_sizes or 0), 1),
            "avg_raw_payload_bytes_with_behavioral": round(
                float(behavioral_sizes or 0), 1
            ),
            "max_write_cap_bytes": 65_000,
            "risk_score": RISK_MEDIUM if with_behavioral > 10_000 else RISK_LOW,
        }
    except SQLAlchemyError:
        db_session.rollback()
        return {"storage": "nested", "error": "query_failed", "risk_score": RISK_UNKNOWN}


def assess_dashboard_snapshot_accumulation(
    db_session: Any,
    *,
    deadline_started: Optional[float] = None,
    deadline_ms: float = MEASUREMENT_WALL_BUDGET_MS,
) -> dict[str, Any]:
    """Snapshot version accumulation — metadata only; never reads payload_json."""
    try:
        total = db_session.query(DashboardSnapshot).count()
        if total == 0:
            return {
                "total_rows": 0,
                "by_snapshot_type": {},
                "by_store_slug": {},
                "oldest_generated_at": None,
                "newest_generated_at": None,
                "historical_only_rows": 0,
                "rows_read_in_practice_estimate": 0,
                "rows_ignored_estimate": 0,
                "latest_row_per_store_type_count": 0,
                "historical_pct": 0.0,
                "append_only_accumulation_confirmed": False,
                "risk_score": RISK_LOW,
            }

        by_type_rows = (
            db_session.query(
                DashboardSnapshot.snapshot_type,
                func.count(DashboardSnapshot.id),
            )
            .group_by(DashboardSnapshot.snapshot_type)
            .all()
        )
        by_type = {str(t): int(c) for t, c in by_type_rows}

        version_stats = (
            db_session.query(
                DashboardSnapshot.store_slug,
                DashboardSnapshot.snapshot_type,
                func.count(DashboardSnapshot.id),
                func.min(DashboardSnapshot.version),
                func.max(DashboardSnapshot.version),
                func.min(DashboardSnapshot.generated_at),
                func.max(DashboardSnapshot.generated_at),
            )
            .group_by(DashboardSnapshot.store_slug, DashboardSnapshot.snapshot_type)
            .all()
        )

        store_type_pairs = len(version_stats)
        max_versions = max((int(c) for _, _, c, _, _, _, _ in version_stats), default=0)
        avg_versions = (
            sum(int(c) for _, _, c, _, _, _, _ in version_stats) / store_type_pairs
            if store_type_pairs
            else 0.0
        )
        historical_only = sum(max(0, int(c) - 1) for _, _, c, _, _, _, _ in version_stats)
        read_in_practice = store_type_pairs  # latest row per (store, type)
        ignored = max(0, total - read_in_practice)
        hist_pct = round(100.0 * ignored / total, 2) if total else 0.0
        append_only = store_type_pairs > 0 and max_versions > 1

        top_version_stores = sorted(
            (
                {
                    "store_slug": slug,
                    "snapshot_type": stype,
                    "version_count": int(cnt),
                    "version_min": int(vmin or 0),
                    "version_max": int(vmax or 0),
                    "oldest_generated_at": _iso(oldest),
                    "newest_generated_at": _iso(newest),
                }
                for slug, stype, cnt, vmin, vmax, oldest, newest in version_stats
            ),
            key=lambda x: x["version_count"],
            reverse=True,
        )[:10]

        risk = RISK_LOW
        if total >= 100_000 or hist_pct >= 80 or (append_only and hist_pct >= 50):
            risk = RISK_HIGH
        elif total >= 10_000 or hist_pct >= 30 or append_only:
            risk = RISK_MEDIUM

        oldest_gen = db_session.query(func.min(DashboardSnapshot.generated_at)).scalar()
        newest_gen = db_session.query(func.max(DashboardSnapshot.generated_at)).scalar()
        by_store_rows = (
            db_session.query(
                DashboardSnapshot.store_slug,
                func.count(DashboardSnapshot.id),
            )
            .group_by(DashboardSnapshot.store_slug)
            .order_by(func.count(DashboardSnapshot.id).desc())
            .limit(TOP_STORE_SLUG_LIMIT)
            .all()
        )
        by_store = {str(s): int(c) for s, c in by_store_rows}

        return {
            "total_rows": total,
            "by_snapshot_type": by_type,
            "by_store_slug": by_store,
            "store_type_pairs": store_type_pairs,
            "max_versions_per_pair": max_versions,
            "avg_versions_per_pair": round(avg_versions, 2),
            "oldest_generated_at": _iso(oldest_gen),
            "newest_generated_at": _iso(newest_gen),
            "historical_only_rows": historical_only,
            "rows_read_in_practice_estimate": read_in_practice,
            "rows_ignored_estimate": ignored,
            "latest_row_per_store_type_count": read_in_practice,
            "historical_pct": hist_pct,
            "append_only_accumulation_confirmed": append_only,
            "top_version_accumulators": top_version_stores,
            "risk_score": risk,
        }
    except SQLAlchemyError:
        db_session.rollback()
        return {"error": "query_failed", "risk_score": RISK_UNKNOWN}


def assess_log_growth(db_session: Any) -> dict[str, Any]:
    """Recovery logs and timeline event density."""
    try:
        log_total = db_session.query(CartRecoveryLog).count()
        timeline_total = db_session.query(RecoveryTruthTimelineEvent).count()

        distinct_rk_logs = (
            db_session.query(func.count(func.distinct(CartRecoveryLog.recovery_key)))
            .filter(CartRecoveryLog.recovery_key.isnot(None))
            .scalar()
        )
        distinct_rk_timeline = (
            db_session.query(
                func.count(func.distinct(RecoveryTruthTimelineEvent.recovery_key))
            ).scalar()
        )

        avg_logs_per_rk = (
            log_total / distinct_rk_logs if distinct_rk_logs else 0.0
        )
        avg_timeline_per_rk = (
            timeline_total / distinct_rk_timeline if distinct_rk_timeline else 0.0
        )

        now = _utc_now()
        start_30 = _naive(now) - timedelta(days=30)
        logs_30 = (
            db_session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.created_at >= start_30)
            .count()
        )
        timeline_30 = (
            db_session.query(RecoveryTruthTimelineEvent)
            .filter(RecoveryTruthTimelineEvent.created_at >= start_30)
            .count()
        )

        top_log_stores = (
            db_session.query(
                CartRecoveryLog.store_slug,
                func.count(CartRecoveryLog.id),
            )
            .group_by(CartRecoveryLog.store_slug)
            .order_by(func.count(CartRecoveryLog.id).desc())
            .limit(10)
            .all()
        )
        top_timeline_stores = (
            db_session.query(
                RecoveryTruthTimelineEvent.store_slug,
                func.count(RecoveryTruthTimelineEvent.id),
            )
            .group_by(RecoveryTruthTimelineEvent.store_slug)
            .order_by(func.count(RecoveryTruthTimelineEvent.id).desc())
            .limit(10)
            .all()
        )

        return {
            "cart_recovery_logs": {
                "total_rows": log_total,
                "distinct_recovery_keys": int(distinct_rk_logs or 0),
                "avg_rows_per_recovery_key": round(avg_logs_per_rk, 2),
                "rows_last_30_days": logs_30,
                "estimated_monthly_growth": logs_30,
                "estimated_daily_growth": round(logs_30 / 30.0, 2),
                "top_stores": [
                    {"store_slug": s, "row_count": int(c)} for s, c in top_log_stores
                ],
                "risk_score": _risk_score_for_table(
                    table="cart_recovery_logs",
                    row_count=log_total,
                    rows_last_7_days=0,
                    rows_last_30_days=logs_30,
                    threshold_status=_threshold_status(
                        log_total, 5_000_000, 20_000_000
                    ),
                ),
            },
            "recovery_truth_timeline_events": {
                "total_rows": timeline_total,
                "distinct_recovery_keys": int(distinct_rk_timeline or 0),
                "avg_rows_per_recovery_key": round(avg_timeline_per_rk, 2),
                "rows_last_30_days": timeline_30,
                "estimated_monthly_growth": timeline_30,
                "estimated_daily_growth": round(timeline_30 / 30.0, 2),
                "top_stores": [
                    {"store_slug": s, "row_count": int(c)}
                    for s, c in top_timeline_stores
                ],
                "risk_score": _risk_score_for_table(
                    table="recovery_truth_timeline_events",
                    row_count=timeline_total,
                    rows_last_7_days=0,
                    rows_last_30_days=timeline_30,
                    threshold_status=_threshold_status(
                        timeline_total, 5_000_000, 20_000_000
                    ),
                ),
            },
        }
    except SQLAlchemyError:
        db_session.rollback()
        return {"error": "query_failed"}


def query_pressure_inventory() -> dict[str, Any]:
    """Code-verified LIMIT values and hot-path budgets (no DB required)."""
    return {
        "dashboard_hot_slice": {
            "max_queries": 15,
            "max_rows": 25,
            "window_hours": 36,
            "source": "services/dashboard_hot_slice_v1.py",
        },
        "normal_carts_log_bulk": {
            "limit": 3000,
            "source": "main.py cart recovery log bulk load",
            "risk": RISK_HIGH,
        },
        "sent_logs_for_store": {
            "limit": 250,
            "source": "main.py sent_logs_for_store enrich",
            "risk": RISK_MEDIUM,
        },
        "due_scanner": {
            "limit": 25,
            "source": "services/recovery_db_due_scanner.py",
            "risk": RISK_LOW,
        },
        "normal_carts_row_cap": {
            "limit": "50+50 materialization",
            "source": "services/normal_carts_dashboard_batch_v1.py",
            "risk": RISK_LOW,
        },
        "timeline_per_key_reads": {
            "limit": 12,
            "source": "services/recovery_truth_timeline_v1.py",
            "risk": RISK_LOW,
        },
        "admin_store_scan": {
            "limit": 400,
            "source": "main.py admin scoring",
            "risk": RISK_LOW,
        },
        "vip_augment": {
            "limit": 4000,
            "source": "main.py VIP augment path",
            "risk": RISK_MEDIUM,
        },
        "performance_budgets": {
            "normal_carts_soft": 80,
            "normal_carts_hard": 150,
            "summary_soft": 40,
            "refresh_state_soft": 15,
            "source": "docs/cartflow_performance_governance_v1.md",
        },
        "dashboard_budgets_respected": {
            "hot_slice_enforced": True,
            "snapshot_latest_row_only": True,
            "normal_carts_wall_guard_s": 12,
            "note": "Full live build can exceed 15 queries; hot slice path is bounded",
        },
    }


def archive_readiness_ranking(
    tables: list[TableSizeMetrics],
    snapshot_acc: dict[str, Any],
    log_growth: dict[str, Any],
) -> list[dict[str, Any]]:
    """Evidence-based archive priority."""
    candidates: list[dict[str, Any]] = []

    snap_total = int(snapshot_acc.get("total_rows") or 0)
    snap_hist = int(snapshot_acc.get("historical_only_rows") or 0)
    candidates.append(
        {
            "priority": 1,
            "table": "dashboard_snapshots",
            "reason": "append-only; historical versions never read on merchant path",
            "row_count": snap_total,
            "archivable_rows_estimate": snap_hist,
            "append_only_confirmed": bool(snapshot_acc.get("append_only_accumulation_confirmed")),
            "risk_score": snapshot_acc.get("risk_score", RISK_HIGH),
        }
    )

    tl = log_growth.get("recovery_truth_timeline_events") or {}
    candidates.append(
        {
            "priority": 2,
            "table": "recovery_truth_timeline_events",
            "reason": "high append rate; no retention; warm/cold after 180d",
            "row_count": tl.get("total_rows", 0),
            "archivable_rows_estimate": "rows older than 180d (future)",
            "monthly_growth": tl.get("estimated_monthly_growth"),
            "risk_score": tl.get("risk_score", RISK_HIGH),
        }
    )

    logs = log_growth.get("cart_recovery_logs") or {}
    candidates.append(
        {
            "priority": 3,
            "table": "cart_recovery_logs",
            "reason": "multi-row per recovery; dashboard uses bounded bulk only",
            "row_count": logs.get("total_rows", 0),
            "archivable_rows_estimate": "rows older than 365d (future)",
            "monthly_growth": logs.get("estimated_monthly_growth"),
            "risk_score": logs.get("risk_score", RISK_HIGH),
        }
    )

    for tm in tables:
        if tm.table in {
            "dashboard_snapshots",
            "cart_recovery_logs",
            "recovery_truth_timeline_events",
        }:
            continue
        if tm.threshold_status in ("warning", "critical") or tm.risk_score == RISK_HIGH:
            candidates.append(
                {
                    "priority": len(candidates) + 1,
                    "table": tm.table,
                    "reason": f"threshold={tm.threshold_status} risk={tm.risk_score}",
                    "row_count": tm.row_count,
                    "risk_score": tm.risk_score,
                }
            )

    return candidates


def build_data_growth_measurement_report(db_session: Any) -> dict[str, Any]:
    """Full read-only measurement report."""
    import time

    t0 = time.perf_counter()
    now = _utc_now()
    table_specs = [
        ("abandoned_carts", AbandonedCart, AbandonedCart.first_seen_at),
        ("cart_recovery_logs", CartRecoveryLog, CartRecoveryLog.created_at),
        (
            "recovery_truth_timeline_events",
            RecoveryTruthTimelineEvent,
            RecoveryTruthTimelineEvent.created_at,
        ),
        ("recovery_schedules", RecoverySchedule, RecoverySchedule.created_at),
        ("dashboard_snapshots", DashboardSnapshot, DashboardSnapshot.created_at),
        ("movement_snapshots", MovementSnapshot, MovementSnapshot.created_at),
        ("purchase_truth_records", PurchaseTruthRecord, PurchaseTruthRecord.created_at),
        ("stores", Store, Store.created_at),
    ]

    tables = [
        assess_table_size(
            db_session,
            table_name=name,
            model=model,
            ts_attr=ts,
            now=now,
        )
        for name, model, ts in table_specs
    ]

    snapshot_acc = assess_dashboard_snapshot_accumulation(
        db_session,
        deadline_started=t0,
        deadline_ms=MEASUREMENT_WALL_BUDGET_MS,
    )
    log_growth = assess_log_growth(db_session)
    cf_behavioral = assess_cf_behavioral(db_session)
    query_pressure = query_pressure_inventory()
    archive_priority = archive_readiness_ranking(tables, snapshot_acc, log_growth)
    growth_risk_score = compute_platform_growth_risk_score(
        tables=tables,
        snapshot_acc=snapshot_acc,
        log_growth=log_growth,
    )

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    partial = elapsed_ms >= MEASUREMENT_WALL_BUDGET_MS or bool(snapshot_acc.get("partial"))

    dialect = ""
    try:
        dialect = db_session.bind.dialect.name if db_session.bind else ""
    except Exception:  # noqa: BLE001
        pass

    return {
        "ok": True,
        "measured_at": now.isoformat(),
        "measurement_elapsed_ms": elapsed_ms,
        "measurement_wall_budget_ms": MEASUREMENT_WALL_BUDGET_MS,
        "measurement_partial": partial,
        "database_dialect": dialect,
        "growth_risk_score": growth_risk_score,
        "tables": [t.to_dict() for t in tables],
        "cf_behavioral": cf_behavioral,
        "dashboard_snapshot_accumulation": snapshot_acc,
        "log_growth": log_growth,
        "query_pressure": query_pressure,
        "archive_readiness_priority": archive_priority,
    }


__all__ = [
    "RISK_HIGH",
    "RISK_LOW",
    "RISK_MEDIUM",
    "RISK_UNKNOWN",
    "TABLE_THRESHOLDS",
    "TableSizeMetrics",
    "assess_cf_behavioral",
    "assess_dashboard_snapshot_accumulation",
    "assess_log_growth",
    "assess_table_size",
    "build_data_growth_measurement_report",
    "compute_platform_growth_risk_score",
    "query_pressure_inventory",
]
