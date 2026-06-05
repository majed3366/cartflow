# -*- coding: utf-8 -*-
"""
Read-only root-cause probes for DB Ready stages (Step 4B.2).

Inspects in-process caches / flags only — no behavior changes.
"""
from __future__ import annotations

from typing import Any, Optional

TRACKED_CLASSIFICATION_STAGES: tuple[str, ...] = (
    "widget_schema",
    "identity_backfill",
    "identity_backfill_register",
    "production_schema",
    "bootstrap_merchant_auth",
)


def probe_widget_schema_reason() -> str:
    try:
        from schema_widget import store_widget_schema_warm_done

        if store_widget_schema_warm_done():
            return "cache_hit_skip"
    except Exception:  # noqa: BLE001
        pass
    return "cache_miss"


def probe_production_schema_reason(*, context: str = "startup") -> str:
    try:
        from schema_production_store_bootstrap import production_store_bootstrap_verified

        if production_store_bootstrap_verified():
            return "verification_required"
    except Exception:  # noqa: BLE001
        pass
    ctx = (context or "startup").strip().lower()
    if ctx == "dashboard":
        return "bootstrap_not_verified"
    try:
        import main

        if not bool(getattr(main, "_cartflow_api_db_warmed", False)):
            return "cold_start"
    except Exception:  # noqa: BLE001
        pass
    return "bootstrap_not_verified"


def probe_bootstrap_merchant_auth_reason() -> str:
    try:
        from schema_merchant_auth import merchant_auth_schema_warm_done

        if merchant_auth_schema_warm_done():
            return "verification_required"
    except Exception:  # noqa: BLE001
        pass
    try:
        from extensions import db
        from schema_merchant_auth import verify_merchant_auth_schema

        status = verify_merchant_auth_schema(db)
        missing = status.get("missing_columns") or []
        if missing:
            return "missing_column"
    except Exception:  # noqa: BLE001
        pass
    return "cache_miss"


def probe_identity_backfill_reason() -> str:
    try:
        import main

        if bool(getattr(main, "_cartflow_api_db_warmed", False)):
            return "warm_already_done"
    except Exception:  # noqa: BLE001
        pass
    return "always_run_on_cold_warm"


def probe_identity_backfill_register_reason(
    *,
    rows_scanned: int = 0,
    rows_inserted: int = 0,
) -> str:
    if int(rows_scanned) <= 0:
        return "no_stores_to_scan"
    if int(rows_inserted) > 0:
        return "backfill_needed"
    return "aliases_already_present"


def build_tracked_classifications(
    substage_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract tracked stages from substage/stage rows (latest row per stage name)."""
    by_stage: dict[str, dict[str, Any]] = {}
    for row in substage_rows or []:
        if not isinstance(row, dict):
            continue
        st = str(row.get("stage") or "").strip()
        if st not in TRACKED_CLASSIFICATION_STAGES:
            continue
        by_stage[st] = dict(row)
    out: list[dict[str, Any]] = []
    for st in TRACKED_CLASSIFICATION_STAGES:
        row = by_stage.get(st)
        if not row:
            continue
        out.append(
            {
                "stage": st,
                "reason": str(row.get("reason") or "unknown")[:64],
                "query_count": int(row.get("query_count") or 0),
                "sql_ms": round(float(row.get("sql_ms") or 0.0), 1),
                "elapsed_ms": round(float(row.get("elapsed_ms") or 0.0), 1),
                "rows_scanned": int(row.get("rows_scanned") or 0),
                "rows_updated": int(row.get("rows_updated") or 0),
                "rows_inserted": int(row.get("rows_inserted") or 0),
            }
        )
    return out


__all__ = [
    "TRACKED_CLASSIFICATION_STAGES",
    "build_tracked_classifications",
    "probe_bootstrap_merchant_auth_reason",
    "probe_identity_backfill_register_reason",
    "probe_identity_backfill_reason",
    "probe_production_schema_reason",
    "probe_widget_schema_reason",
]
