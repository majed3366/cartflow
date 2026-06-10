# -*- coding: utf-8 -*-
"""
Knowledge Layer v1 — Product Foundation read bridge (ONLY approved KL path).

May read foundation tables and foundation health outputs only.
No raw payload parsing, widget payload inference, or arbitrary product queries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from models import AbandonedCart
from services.product_data.product_foundation_health_v1 import assess_foundation_health

ALLOWED_BRIDGE_TABLES = frozenset(
    {
        "cart_line_snapshots",
        "product_catalog_entries",
        "product_hesitation_mappings",
        "product_purchase_mappings",
    }
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _window_bounds(*, window_days: int, now: Optional[datetime] = None) -> tuple[datetime, datetime]:
    end = _naive(now or _utc_now())
    start = end - timedelta(days=max(1, int(window_days)))
    return start, end


def _normal_lane_session_ids(
    db_session: Any,
    *,
    store_id: Optional[int],
    window_start: datetime,
    window_end: datetime,
) -> set[str]:
    if not store_id:
        return set()
    try:
        rows = (
            db_session.query(AbandonedCart.recovery_session_id)
            .filter(
                AbandonedCart.store_id == store_id,
                AbandonedCart.vip_mode.is_(False),
                AbandonedCart.first_seen_at >= window_start,
                AbandonedCart.first_seen_at < window_end,
                AbandonedCart.recovery_session_id.isnot(None),
                AbandonedCart.recovery_session_id != "",
            )
            .distinct()
            .all()
        )
        return {str(r[0]).strip() for r in rows if r and r[0]}
    except SQLAlchemyError:
        db_session.rollback()
        return set()


@dataclass
class KnowledgeProductMetricsBundle:
    """Read-only foundation bridge metrics — not product insights."""

    store_slug: str = ""
    window_days: int = 7
    bridge_module: str = "knowledge_product_metrics_v1"
    source_tables: list[str] = field(default_factory=list)
    foundation_readiness: str = "limited"
    snapshot_rows: int = 0
    catalog_rows: int = 0
    hesitation_mapping_rows: int = 0
    purchase_mapping_rows: int = 0
    snapshot_coverage: float = 0.0
    catalog_coverage: float = 0.0
    hesitation_mapping_coverage: float = 0.0
    purchase_mapping_coverage: float = 0.0
    session_sample_size: int = 0
    sessions_with_snapshots: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_slug": self.store_slug,
            "window_days": self.window_days,
            "bridge_module": self.bridge_module,
            "source_tables": list(self.source_tables),
            "foundation_readiness": self.foundation_readiness,
            "snapshot_rows": self.snapshot_rows,
            "catalog_rows": self.catalog_rows,
            "hesitation_mapping_rows": self.hesitation_mapping_rows,
            "purchase_mapping_rows": self.purchase_mapping_rows,
            "snapshot_coverage": round(self.snapshot_coverage, 4),
            "catalog_coverage": round(self.catalog_coverage, 4),
            "hesitation_mapping_coverage": round(self.hesitation_mapping_coverage, 4),
            "purchase_mapping_coverage": round(self.purchase_mapping_coverage, 4),
            "session_sample_size": self.session_sample_size,
            "sessions_with_snapshots": self.sessions_with_snapshots,
        }


def collect_knowledge_product_metrics(
    db_session: Any,
    store_slug: str,
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
    store_id: Optional[int] = None,
) -> KnowledgeProductMetricsBundle:
    """
    Single approved bridge from Knowledge Layer to Product Foundation (read-only).
    """
    ss = (store_slug or "").strip()[:255]
    start, end = _window_bounds(window_days=window_days, now=now)
    bundle = KnowledgeProductMetricsBundle(
        store_slug=ss,
        window_days=window_days,
        source_tables=sorted(ALLOWED_BRIDGE_TABLES),
    )
    if not ss:
        return bundle

    session_ids = _normal_lane_session_ids(
        db_session,
        store_id=store_id,
        window_start=start,
        window_end=end,
    )
    foundation = assess_foundation_health(
        db_session,
        ss,
        session_ids=session_ids,
        window_days=window_days,
        now=now,
    )
    bundle.foundation_readiness = foundation.readiness
    bundle.snapshot_rows = foundation.snapshot_rows
    bundle.catalog_rows = foundation.catalog_rows
    bundle.hesitation_mapping_rows = foundation.hesitation_mapping_rows
    bundle.purchase_mapping_rows = foundation.purchase_mapping_rows
    bundle.snapshot_coverage = foundation.snapshot_coverage
    bundle.catalog_coverage = foundation.catalog_coverage
    bundle.hesitation_mapping_coverage = foundation.hesitation_mapping_coverage
    bundle.purchase_mapping_coverage = foundation.purchase_mapping_coverage
    bundle.session_sample_size = foundation.session_sample_size
    bundle.sessions_with_snapshots = foundation.sessions_with_snapshots
    return bundle


__all__ = [
    "ALLOWED_BRIDGE_TABLES",
    "KnowledgeProductMetricsBundle",
    "collect_knowledge_product_metrics",
]
