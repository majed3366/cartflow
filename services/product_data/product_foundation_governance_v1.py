# -*- coding: utf-8 -*-
"""
Product Foundation governance v1 — growth visibility, query cost, archive policy.

Read-only diagnostics for durable Product Foundation tables. Never writes,
never blocks capture/mapping/recovery paths. Failure-safe by design.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from schema_cart_line_snapshots_v1 import ensure_cart_line_snapshots_schema
from schema_product_catalog_v1 import ensure_product_catalog_schema
from schema_product_hesitation_mapping_v1 import ensure_product_hesitation_mapping_schema
from schema_product_purchase_mapping_v1 import ensure_product_purchase_mapping_schema
from services.product_data.product_foundation_archive_policy_v1 import (
    archive_policy_summary,
)
from services.product_data.product_foundation_growth_v1 import (
    GROWTH_UNKNOWN,
    TableGrowthMetrics,
    assess_table_growth,
)
from services.product_data.product_foundation_query_cost_v1 import (
    QueryCostRecord,
    run_timed_read,
)

log = logging.getLogger("cartflow")

FOUNDATION_TABLE_KEYS: tuple[str, ...] = (
    "cart_line_snapshots",
    "product_catalog_entries",
    "product_hesitation_mappings",
    "product_purchase_mappings",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_schemas(db: Any) -> None:
    ensure_cart_line_snapshots_schema(db)
    ensure_product_catalog_schema(db)
    ensure_product_hesitation_mapping_schema(db)
    ensure_product_purchase_mapping_schema(db)


def _growth_with_timing(
    db_session: Any,
    store_slug: str,
    table_key: str,
    *,
    now: Optional[datetime] = None,
) -> tuple[TableGrowthMetrics, QueryCostRecord]:
    query_name = f"growth_{table_key}"

    def _read() -> TableGrowthMetrics:
        return assess_table_growth(
            db_session, store_slug, table_key, now=now
        )

    metrics, cost = run_timed_read(
        query_name,
        _read,
        row_count_from=lambda m: m.total_rows,
    )
    if metrics is None:
        return (
            TableGrowthMetrics(table=table_key, growth_status=GROWTH_UNKNOWN),
            cost,
        )
    return metrics, cost


def build_product_foundation_governance_report(
    db_session: Any,
    store_slug: str,
    *,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Read-only governance snapshot for one store.

    Combines per-table growth metrics, query timing records, and archive policy.
    """
    slug = (store_slug or "").strip()[:255]
    when = now or _utc_now()
    report: dict[str, Any] = {
        "ok": True,
        "store_slug": slug,
        "generated_at": when.isoformat(),
        "tables": {},
        "query_costs": [],
        "archive_policy": archive_policy_summary(),
    }
    if not slug:
        report["ok"] = False
        return report

    try:
        _ensure_schemas(db_session)
    except Exception as exc:  # noqa: BLE001
        log.debug("governance schema ensure skipped: %s", exc)

    tables: dict[str, Any] = {}
    costs: list[dict[str, Any]] = []
    for key in FOUNDATION_TABLE_KEYS:
        metrics, cost = _growth_with_timing(
            db_session, slug, key, now=when
        )
        tables[key] = metrics.to_dict()
        costs.append(cost.to_dict())

    report["tables"] = tables
    report["query_costs"] = costs
    return report


def try_build_product_foundation_governance_report(
    db_session: Any,
    store_slug: str,
    *,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Failure-safe wrapper — never raises."""
    try:
        return build_product_foundation_governance_report(
            db_session, store_slug, now=now
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("governance report skipped: %s", exc)
        return {
            "ok": False,
            "store_slug": (store_slug or "").strip()[:255],
            "error": "governance_unavailable",
        }


__all__ = [
    "FOUNDATION_TABLE_KEYS",
    "build_product_foundation_governance_report",
    "try_build_product_foundation_governance_report",
]
