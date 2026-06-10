# -*- coding: utf-8 -*-
"""
Product Foundation health v1 — read-only readiness from foundation tables.

Measures snapshot, catalog, hesitation mapping, and purchase mapping coverage
for one store within a time window. Diagnostic only — no writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from models import (
    CartLineSnapshot,
    CartRecoveryReason,
    ProductCatalogEntry,
    ProductHesitationMapping,
    ProductPurchaseMapping,
    PurchaseTruthRecord,
)
from schema_cart_line_snapshots_v1 import ensure_cart_line_snapshots_schema
from schema_product_catalog_v1 import ensure_product_catalog_schema
from schema_product_hesitation_mapping_v1 import ensure_product_hesitation_mapping_schema
from schema_product_purchase_mapping_v1 import ensure_product_purchase_mapping_schema
from services.product_data.product_data_types_v1 import (
    DEFAULT_HEALTH_THRESHOLDS,
    ProductDataHealthThresholds,
    classify_readiness,
)

FOUNDATION_LAYER_SNAPSHOTS = "cart_line_snapshots"
FOUNDATION_LAYER_CATALOG = "product_catalog_entries"
FOUNDATION_LAYER_HESITATION = "product_hesitation_mappings"
FOUNDATION_LAYER_PURCHASE = "product_purchase_mappings"


@dataclass
class FoundationHealthMetrics:
    """Read-only Product Foundation table readiness."""

    readiness: str = "limited"
    snapshot_coverage: float = 0.0
    catalog_coverage: float = 0.0
    hesitation_mapping_coverage: float = 0.0
    purchase_mapping_coverage: float = 0.0
    snapshot_rows: int = 0
    catalog_rows: int = 0
    hesitation_mapping_rows: int = 0
    purchase_mapping_rows: int = 0
    reason_events: int = 0
    purchase_events: int = 0
    session_sample_size: int = 0
    sessions_with_snapshots: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness": self.readiness,
            "snapshot_coverage": round(self.snapshot_coverage, 4),
            "catalog_coverage": round(self.catalog_coverage, 4),
            "hesitation_mapping_coverage": round(self.hesitation_mapping_coverage, 4),
            "purchase_mapping_coverage": round(self.purchase_mapping_coverage, 4),
            "snapshot_rows": self.snapshot_rows,
            "catalog_rows": self.catalog_rows,
            "hesitation_mapping_rows": self.hesitation_mapping_rows,
            "purchase_mapping_rows": self.purchase_mapping_rows,
            "reason_events": self.reason_events,
            "purchase_events": self.purchase_events,
            "session_sample_size": self.session_sample_size,
            "sessions_with_snapshots": self.sessions_with_snapshots,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _window_start(*, window_days: int, now: Optional[datetime] = None) -> datetime:
    end = _naive(now or _utc_now())
    return end - timedelta(days=max(1, int(window_days)))


def _coverage_ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return float(count) / float(total)


def _ensure_schemas(db: Any) -> None:
    ensure_cart_line_snapshots_schema(db)
    ensure_product_catalog_schema(db)
    ensure_product_hesitation_mapping_schema(db)
    ensure_product_purchase_mapping_schema(db)


def assess_foundation_health(
    db_session: Any,
    store_slug: str,
    *,
    session_ids: set[str] | None = None,
    window_days: int = 7,
    now: Optional[datetime] = None,
    thresholds: ProductDataHealthThresholds = DEFAULT_HEALTH_THRESHOLDS,
) -> FoundationHealthMetrics:
    """
    Read-only foundation readiness for one store.

    ``session_ids`` should be recovery session ids from abandoned carts in the
    same window — used to compute snapshot session coverage.
    """
    slug = (store_slug or "").strip()[:255]
    metrics = FoundationHealthMetrics()
    if not slug:
        return metrics

    start = _window_start(window_days=window_days, now=now)
    sessions = {s.strip() for s in (session_ids or set()) if (s or "").strip()}
    metrics.session_sample_size = len(sessions)

    try:
        _ensure_schemas(db_session)
    except Exception:  # noqa: BLE001
        pass

    try:
        metrics.snapshot_rows = (
            db_session.query(CartLineSnapshot)
            .filter(
                CartLineSnapshot.store_slug == slug,
                CartLineSnapshot.captured_at >= start,
            )
            .count()
        )
        metrics.catalog_rows = (
            db_session.query(ProductCatalogEntry)
            .filter(ProductCatalogEntry.store_slug == slug)
            .count()
        )
        metrics.hesitation_mapping_rows = (
            db_session.query(ProductHesitationMapping)
            .filter(
                ProductHesitationMapping.store_slug == slug,
                ProductHesitationMapping.captured_at >= start,
            )
            .count()
        )
        metrics.purchase_mapping_rows = (
            db_session.query(ProductPurchaseMapping)
            .filter(
                ProductPurchaseMapping.store_slug == slug,
                ProductPurchaseMapping.purchased_at >= start,
            )
            .count()
        )
        metrics.reason_events = (
            db_session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == slug,
                CartRecoveryReason.created_at >= start,
            )
            .count()
        )
        metrics.purchase_events = (
            db_session.query(PurchaseTruthRecord)
            .filter(
                PurchaseTruthRecord.store_slug == slug,
                PurchaseTruthRecord.purchase_time >= start,
            )
            .count()
        )

        snap_session_rows = (
            db_session.query(CartLineSnapshot.session_id)
            .filter(
                CartLineSnapshot.store_slug == slug,
                CartLineSnapshot.captured_at >= start,
            )
            .distinct()
            .all()
        )
        snap_sessions = {str(r[0]).strip() for r in snap_session_rows if r and r[0]}
        metrics.sessions_with_snapshots = len(snap_sessions & sessions) if sessions else len(
            snap_sessions
        )

        if sessions:
            metrics.snapshot_coverage = _coverage_ratio(
                metrics.sessions_with_snapshots, len(sessions)
            )
        elif metrics.snapshot_rows > 0:
            metrics.snapshot_coverage = 1.0
        else:
            metrics.snapshot_coverage = 0.0

        if metrics.snapshot_rows > 0:
            metrics.catalog_coverage = 1.0 if metrics.catalog_rows > 0 else 0.0
        else:
            metrics.catalog_coverage = 1.0 if metrics.catalog_rows > 0 else 0.0

        if metrics.reason_events > 0:
            metrics.hesitation_mapping_coverage = min(
                1.0,
                _coverage_ratio(metrics.hesitation_mapping_rows, metrics.reason_events),
            )
        else:
            metrics.hesitation_mapping_coverage = (
                1.0 if metrics.hesitation_mapping_rows == 0 else 1.0
            )

        if metrics.purchase_events > 0:
            metrics.purchase_mapping_coverage = min(
                1.0,
                _coverage_ratio(metrics.purchase_mapping_rows, metrics.purchase_events),
            )
        else:
            metrics.purchase_mapping_coverage = (
                1.0 if metrics.purchase_mapping_rows == 0 else 1.0
            )

        components = [metrics.snapshot_coverage]
        if metrics.snapshot_rows > 0:
            components.append(metrics.catalog_coverage)
        if metrics.reason_events > 0:
            components.append(metrics.hesitation_mapping_coverage)
        if metrics.purchase_events > 0:
            components.append(metrics.purchase_mapping_coverage)

        composite = sum(components) / len(components) if components else 0.0
        metrics.readiness = classify_readiness(composite, thresholds=thresholds)
    except SQLAlchemyError:
        db_session.rollback()

    return metrics


__all__ = [
    "FOUNDATION_LAYER_CATALOG",
    "FOUNDATION_LAYER_HESITATION",
    "FOUNDATION_LAYER_PURCHASE",
    "FOUNDATION_LAYER_SNAPSHOTS",
    "FoundationHealthMetrics",
    "assess_foundation_health",
]
