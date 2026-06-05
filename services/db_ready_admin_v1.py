# -*- coding: utf-8 -*-
"""
Admin Operations read-only view for DB ready initialization health (Step 4A).
"""
from __future__ import annotations

from typing import Any

from services.db_ready_operational_snapshot_v1 import (
    HEALTHY_MAX_MS,
    SLOW_MAX_MS,
    load_db_ready_operational_snapshot,
    status_emoji,
    status_label_ar,
)
from services.db_ready_restart_survival_v1 import restart_survival_public_view

SECTION_KEY = "dashboard_db_ready"


def _startup_warm_headline(snap: dict[str, Any]) -> tuple[str, str]:
    st = str(snap.get("startup_warm_status") or "not_started").strip().lower()
    if st == "succeeded":
        return (
            "Dashboard pre-warmed at startup",
            "تم تجهيز لوحة التاجر مسبقاً",
        )
    if st == "running":
        return (
            "Dashboard initialization running in background",
            "تهيئة لوحة التاجر تعمل في الخلفية",
        )
    if st == "failed":
        return (
            "Startup warm failed — requests may retry warm",
            "فشل التجهيز عند الإقلاع — قد تُعاد المحاولة مع الطلبات",
        )
    return (
        "Startup warm not started yet",
        "لم يبدأ التجهيز عند الإقلاع بعد",
    )


def build_admin_db_ready_health_section_readonly() -> dict[str, Any]:
    snap = load_db_ready_operational_snapshot(reload_db=True)
    status = str(snap.get("status") or "healthy").strip().lower()
    last_ms = round(float(snap.get("last_duration_ms") or 0.0), 1)
    avg_ms = round(float(snap.get("avg_duration_ms") or 0.0), 1)
    worst_ms = round(float(snap.get("worst_duration_ms") or 0.0), 1)
    last_success = bool(snap.get("last_success", True))
    startup_en, startup_ar = _startup_warm_headline(snap)
    startup_status = str(snap.get("startup_warm_status") or "not_started")
    startup_duration = round(float(snap.get("startup_warm_duration_ms") or 0.0), 1)
    cached_verification = snap.get("last_request_cached_verification")
    restart_survival = restart_survival_public_view(snap)

    return {
        "section": SECTION_KEY,
        "status": status,
        "status_emoji": status_emoji(status),
        "status_label": status_label_ar(status),
        "problem_en": "Dashboard initialization is slower than expected",
        "impact_en": "Merchant dashboard or demo pages may load slowly",
        "where_en": "Dashboard Initialization",
        "action_en": "Inspect DB Ready initialization stages",
        "problem_ar": "تهيئة لوحة التاجر أبطأ من المتوقع",
        "impact_ar": "قد تتأخر تحميل لوحة التاجر أو صفحات التجربة",
        "where_ar": "تهيئة لوحة التاجر",
        "action_ar": "راجع مراحل تهيئة DB Ready في السجلات",
        "startup_warm": {
            "status": startup_status,
            "duration_ms": startup_duration,
            "error": snap.get("startup_warm_error"),
            "headline_en": startup_en,
            "headline_ar": startup_ar,
            "last_request_cached_verification": cached_verification,
        },
        "restart_survival": restart_survival,
        "verification": {
            "last_duration_ms": last_ms,
            "avg_duration_ms": avg_ms,
            "worst_duration_ms": worst_ms,
            "last_success": last_success,
            "last_failure": (snap.get("last_failure_message") or None),
            "thresholds_ms": {
                "healthy_max": HEALTHY_MAX_MS,
                "slow_max": SLOW_MAX_MS,
            },
        },
        "technical": {
            "last_trace_id": snap.get("last_trace_id") or "",
            "last_stage": snap.get("last_stage") or "",
            "last_duration_ms": last_ms,
            "lock_wait_ms": round(float(snap.get("last_lock_wait_ms") or 0.0), 1),
            "query_count": int(snap.get("last_query_count") or 0),
            "total_sql_ms": round(float(snap.get("last_sql_ms") or 0.0), 1),
            "sample_count": int(snap.get("sample_count") or 0),
            "last_seen_at": snap.get("last_seen_at"),
            "top_substage": snap.get("last_top_substage") or "",
            "top_substage_queries": int(snap.get("last_top_substage_queries") or 0),
            "top_substage_sql_ms": round(float(snap.get("last_top_substage_sql_ms") or 0.0), 1),
            "top_substage_elapsed_ms": round(
                float(snap.get("last_top_substage_elapsed_ms") or 0.0), 1
            ),
            "top_substages": snap.get("top_substages") or [],
            "stage_classifications": snap.get("stage_classifications") or [],
            "startup_warm_status": startup_status,
            "startup_warm_duration_ms": startup_duration,
            "startup_warm_error": snap.get("startup_warm_error"),
            "last_request_cached_verification": cached_verification,
        },
        "snapshot": snap,
        "stage_classifications": snap.get("stage_classifications") or [],
    }


def build_restart_survival_admin_alert() -> dict[str, Any] | None:
    snap = load_db_ready_operational_snapshot(reload_db=False)
    rs = restart_survival_public_view(snap)
    result = str(rs.get("verification_result") or "PENDING").strip().upper()
    if result != "FAIL":
        return None
    return {
        "kind": "dashboard_restart_survival_failed",
        "severity": "high",
        "title_ar": "فشل حماية إقلاع لوحة التاجر",
        "detail_ar": (
            f"Startup warm: {rs.get('startup_warm_status') or '—'} — "
            f"first dashboard: {rs.get('first_dashboard_duration_ms') or 0}ms"
        ),
        "records_total": 1,
        "meta": {
            "startup_warm_status": rs.get("startup_warm_status"),
            "startup_warm_duration_ms": rs.get("startup_warm_duration_ms"),
            "first_dashboard_duration_ms": rs.get("first_dashboard_duration_ms"),
            "first_dashboard_cached_verification": rs.get(
                "first_dashboard_cached_verification"
            ),
            "verification_result": result,
        },
    }


def build_db_ready_admin_alert() -> dict[str, Any] | None:
    """Operational alert when status is slow or blocking."""
    snap = load_db_ready_operational_snapshot(reload_db=False)
    status = str(snap.get("status") or "healthy").strip().lower()
    if status not in ("slow", "blocking"):
        return None
    last_ms = round(float(snap.get("last_duration_ms") or 0.0), 1)
    sev = "critical" if status == "blocking" else "high"
    return {
        "kind": "dashboard_db_init_slow",
        "severity": sev,
        "title_ar": "تهيئة لوحة التاجر بطيئة",
        "detail_ar": (
            f"آخر مدة تهيئة: {last_ms}ms — "
            f"المرحلة الأبطأ: {snap.get('last_stage') or 'غير معروف'}"
        ),
        "records_total": 1,
        "meta": {
            "last_duration_ms": last_ms,
            "avg_duration_ms": round(float(snap.get("avg_duration_ms") or 0.0), 1),
            "last_stage": snap.get("last_stage") or "",
            "lock_wait_ms": round(float(snap.get("last_lock_wait_ms") or 0.0), 1),
        },
    }


__all__ = [
    "SECTION_KEY",
    "build_admin_db_ready_health_section_readonly",
    "build_db_ready_admin_alert",
    "build_restart_survival_admin_alert",
]
