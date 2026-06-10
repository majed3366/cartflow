# -*- coding: utf-8 -*-
"""
Product Data Health v1 — read-only readiness diagnostics.

Analyzes existing ``abandoned_carts.raw_payload`` and ``stores.cf_product_catalog_json``.
No writes, migrations, snapshots, or product intelligence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from models import AbandonedCart, Store
from services.product_data.product_foundation_health_v1 import assess_foundation_health
from services.product_data.product_identity_coverage_v1 import assess_identity_coverage
from services.product_data.product_data_types_v1 import (
    DEFAULT_HEALTH_THRESHOLDS,
    ProductDataHealthReport,
    ProductDataHealthThresholds,
    classify_confidence,
    classify_readiness,
)
from services.recovery_product_context import line_items_from_abandoned_cart


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _window_start(*, window_days: int, now: Optional[datetime] = None) -> datetime:
    end = _naive(now or _utc_now())
    return end - timedelta(days=max(1, int(window_days)))


def _line_product_name(line: dict[str, Any]) -> str:
    name = (
        line.get("name")
        or line.get("title")
        or line.get("product_name")
        or (line.get("product") or {}).get("name")
        or ""
    )
    return str(name).strip()


def _line_product_id(line: dict[str, Any]) -> str:
    pid = str(line.get("product_id") or "").strip()
    if pid:
        return pid[:128]
    prod = line.get("product")
    if isinstance(prod, dict):
        nested = str(prod.get("id") or "").strip()
        if nested:
            return nested[:128]
    raw_id = str(line.get("id") or "").strip()
    if raw_id and not str(line.get("variant_id") or "").strip():
        return raw_id[:128]
    return ""


def _line_variant_id(line: dict[str, Any]) -> str:
    return str(line.get("variant_id") or "").strip()[:128]


def _line_sku(line: dict[str, Any]) -> str:
    return str(line.get("sku") or line.get("product_num") or "").strip()[:128]


@dataclass(frozen=True, slots=True)
class _CartProductSignals:
    has_identity: bool = False
    has_name: bool = False
    has_product_id: bool = False
    has_variant_id: bool = False


def _signals_from_cart(ac: AbandonedCart) -> _CartProductSignals:
    lines = line_items_from_abandoned_cart(ac)
    if not lines:
        return _CartProductSignals()

    has_name = False
    has_product_id = False
    has_variant_id = False
    has_identity = False

    for line in lines:
        name = _line_product_name(line)
        pid = _line_product_id(line)
        vid = _line_variant_id(line)
        sku = _line_sku(line)

        if name:
            has_name = True
        if pid:
            has_product_id = True
        if vid:
            has_variant_id = True
        if pid or vid or sku or name:
            has_identity = True

    return _CartProductSignals(
        has_identity=has_identity,
        has_name=has_name,
        has_product_id=has_product_id,
        has_variant_id=has_variant_id,
    )


def _catalog_available(store_row: Optional[Store]) -> bool:
    if store_row is None:
        return False
    raw = getattr(store_row, "cf_product_catalog_json", None)
    if not isinstance(raw, str) or not raw.strip():
        return False
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    products = data.get("products")
    return isinstance(products, list) and len(products) > 0


def _coverage_ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return float(count) / float(total)


def assess_product_data_health(
    db_session: Any,
    store_slug: str,
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
    thresholds: ProductDataHealthThresholds = DEFAULT_HEALTH_THRESHOLDS,
) -> ProductDataHealthReport:
    """
    Read-only product readiness for one store within ``window_days``.

    No writes; rolls back on SQLAlchemy errors.
    """
    ss = (store_slug or "").strip()[:255]
    report = ProductDataHealthReport(
        store_slug=ss,
        window_days=max(1, int(window_days)),
    )
    if not ss:
        return report

    store_row: Optional[Store] = None
    store_id: Optional[int] = None

    try:
        from services.vip_abandoned_cart_phone import (  # noqa: PLC0415
            resolve_store_row_for_cartflow_slug_session,
        )

        store_row = resolve_store_row_for_cartflow_slug_session(db_session, ss)
        if store_row is not None:
            report.store_resolved = True
            store_id = int(getattr(store_row, "id", 0) or 0) or None
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db_session.rollback()

    report.catalog_available = _catalog_available(store_row)

    if not store_id:
        report.foundation = assess_foundation_health(
            db_session,
            ss,
            session_ids=set(),
            window_days=window_days,
            now=now,
            thresholds=thresholds,
        )
        report.identity_coverage = assess_identity_coverage(
            db_session,
            ss,
            [],
            window_days=window_days,
            now=now,
            thresholds=thresholds,
        )
        return report

    start = _window_start(window_days=window_days, now=now)
    carts: list[AbandonedCart] = []

    try:
        carts = (
            db_session.query(AbandonedCart)
            .filter(
                AbandonedCart.store_id == store_id,
                AbandonedCart.first_seen_at >= start,
            )
            .all()
        )
    except (SQLAlchemyError, OSError):
        db_session.rollback()
        return report

    total = len(carts)
    report.cart_sample_size = total
    session_ids = {
        (getattr(ac, "recovery_session_id", None) or "").strip()
        for ac in carts
        if (getattr(ac, "recovery_session_id", None) or "").strip()
    }
    report.foundation = assess_foundation_health(
        db_session,
        ss,
        session_ids=session_ids,
        window_days=window_days,
        now=now,
        thresholds=thresholds,
    )
    report.identity_coverage = assess_identity_coverage(
        db_session,
        ss,
        carts,
        window_days=window_days,
        now=now,
        thresholds=thresholds,
    )
    if total == 0:
        report.readiness = classify_readiness(0.0, thresholds=thresholds)
        report.confidence = classify_confidence(0.0, 0.0, thresholds=thresholds)
        return report

    identity_n = 0
    name_n = 0
    pid_n = 0
    variant_n = 0

    for ac in carts:
        sig = _signals_from_cart(ac)
        if sig.has_identity:
            identity_n += 1
        if sig.has_name:
            name_n += 1
        if sig.has_product_id:
            pid_n += 1
        if sig.has_variant_id:
            variant_n += 1

    report.coverage = _coverage_ratio(identity_n, total)
    report.product_name_coverage = _coverage_ratio(name_n, total)
    report.product_id_coverage = _coverage_ratio(pid_n, total)
    report.variant_coverage = _coverage_ratio(variant_n, total)
    report.readiness = classify_readiness(report.coverage, thresholds=thresholds)
    report.confidence = classify_confidence(
        report.coverage,
        report.product_id_coverage,
        thresholds=thresholds,
    )
    return report


def build_product_data_health_report(
    db_session: Any,
    store_slug: str,
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
    thresholds: ProductDataHealthThresholds = DEFAULT_HEALTH_THRESHOLDS,
) -> ProductDataHealthReport:
    """Public entry — same as ``assess_product_data_health``."""
    return assess_product_data_health(
        db_session,
        store_slug,
        window_days=window_days,
        now=now,
        thresholds=thresholds,
    )
