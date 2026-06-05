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

SECTION_KEY = "dashboard_db_ready"


def build_admin_db_ready_health_section_readonly() -> dict[str, Any]:
    snap = load_db_ready_operational_snapshot(reload_db=True)
    status = str(snap.get("status") or "healthy").strip().lower()
    last_ms = round(float(snap.get("last_duration_ms") or 0.0), 1)
    avg_ms = round(float(snap.get("avg_duration_ms") or 0.0), 1)
    worst_ms = round(float(snap.get("worst_duration_ms") or 0.0), 1)
    last_success = bool(snap.get("last_success", True))

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
        },
        "snapshot": snap,
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
]
