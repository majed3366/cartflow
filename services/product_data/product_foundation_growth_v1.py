# -*- coding: utf-8 -*-
"""
Product Foundation growth v1 — read-only table growth metrics.

Measures row counts and recent insert rates for durable Product Foundation
tables. Diagnostic only — no writes, archives, or deletes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from models import (
    CartLineSnapshot,
    ProductCatalogEntry,
    ProductHesitationMapping,
    ProductPurchaseMapping,
)

GROWTH_NORMAL = "normal"
GROWTH_WATCH = "watch"
GROWTH_HIGH = "high"
GROWTH_UNKNOWN = "unknown"

GROWTH_STATUS_VALUES = frozenset(
    {GROWTH_NORMAL, GROWTH_WATCH, GROWTH_HIGH, GROWTH_UNKNOWN}
)

WATCH_ROWS_LAST_7_DAYS = 100
WATCH_ROWS_LAST_30_DAYS = 500
HIGH_ROWS_LAST_7_DAYS = 1000
HIGH_ROWS_LAST_30_DAYS = 5000


@dataclass(frozen=True, slots=True)
class TableGrowthMetrics:
    table: str
    total_rows: int = 0
    rows_added_today: int = 0
    rows_added_last_7_days: int = 0
    rows_added_last_30_days: int = 0
    oldest_row_at: Optional[datetime] = None
    newest_row_at: Optional[datetime] = None
    growth_status: str = GROWTH_UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "total_rows": self.total_rows,
            "rows_added_today": self.rows_added_today,
            "rows_added_last_7_days": self.rows_added_last_7_days,
            "rows_added_last_30_days": self.rows_added_last_30_days,
            "oldest_row_at": (
                self.oldest_row_at.isoformat() if self.oldest_row_at is not None else None
            ),
            "newest_row_at": (
                self.newest_row_at.isoformat() if self.newest_row_at is not None else None
            ),
            "growth_status": self.growth_status,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _start_of_day(now: datetime) -> datetime:
    n = _naive(now)
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def classify_growth_status(
    *,
    rows_last_7_days: int,
    rows_last_30_days: int,
) -> str:
    if rows_last_7_days >= HIGH_ROWS_LAST_7_DAYS or rows_last_30_days >= HIGH_ROWS_LAST_30_DAYS:
        return GROWTH_HIGH
    if rows_last_7_days >= WATCH_ROWS_LAST_7_DAYS or rows_last_30_days >= WATCH_ROWS_LAST_30_DAYS:
        return GROWTH_WATCH
    return GROWTH_NORMAL


def _count_since(
    db_session: Any,
    model: Any,
    ts_attr: Any,
    store_slug: str,
    since: datetime,
) -> int:
    return (
        db_session.query(model)
        .filter(model.store_slug == store_slug, ts_attr >= _naive(since))
        .count()
    )


def assess_table_growth(
    db_session: Any,
    store_slug: str,
    table_key: str,
    *,
    now: Optional[datetime] = None,
) -> TableGrowthMetrics:
    """Read-only growth metrics for one Product Foundation table."""
    slug = (store_slug or "").strip()[:255]
    when = now or _utc_now()
    if not slug:
        return TableGrowthMetrics(table=table_key, growth_status=GROWTH_UNKNOWN)

    table_map: dict[str, tuple[Any, str, str]] = {
        "cart_line_snapshots": (CartLineSnapshot, "captured_at", "cart_line_snapshots"),
        "product_catalog_entries": (
            ProductCatalogEntry,
            "first_seen_at",
            "product_catalog_entries",
        ),
        "product_hesitation_mappings": (
            ProductHesitationMapping,
            "captured_at",
            "product_hesitation_mappings",
        ),
        "product_purchase_mappings": (
            ProductPurchaseMapping,
            "purchased_at",
            "product_purchase_mappings",
        ),
    }
    spec = table_map.get(table_key)
    if spec is None:
        return TableGrowthMetrics(table=table_key, growth_status=GROWTH_UNKNOWN)

    model, ts_name, table_name = spec
    ts_attr = getattr(model, ts_name)

    start_today = _start_of_day(when)
    start_7 = _naive(when) - timedelta(days=7)
    start_30 = _naive(when) - timedelta(days=30)

    try:
        base = db_session.query(model).filter(model.store_slug == slug)
        total = base.count()
        rows_today = _count_since(db_session, model, ts_attr, slug, start_today)
        rows_7 = _count_since(db_session, model, ts_attr, slug, start_7)
        rows_30 = _count_since(db_session, model, ts_attr, slug, start_30)
        oldest = (
            db_session.query(func.min(ts_attr))
            .filter(model.store_slug == slug)
            .scalar()
        )
        newest = (
            db_session.query(func.max(ts_attr))
            .filter(model.store_slug == slug)
            .scalar()
        )
        status = classify_growth_status(
            rows_last_7_days=rows_7,
            rows_last_30_days=rows_30,
        )
        if total == 0:
            status = GROWTH_NORMAL
        return TableGrowthMetrics(
            table=table_name,
            total_rows=total,
            rows_added_today=rows_today,
            rows_added_last_7_days=rows_7,
            rows_added_last_30_days=rows_30,
            oldest_row_at=oldest,
            newest_row_at=newest,
            growth_status=status,
        )
    except SQLAlchemyError:
        db_session.rollback()
        return TableGrowthMetrics(table=table_name, growth_status=GROWTH_UNKNOWN)


__all__ = [
    "GROWTH_HIGH",
    "GROWTH_NORMAL",
    "GROWTH_STATUS_VALUES",
    "GROWTH_UNKNOWN",
    "GROWTH_WATCH",
    "TableGrowthMetrics",
    "assess_table_growth",
    "classify_growth_status",
]
