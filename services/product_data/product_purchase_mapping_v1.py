# -*- coding: utf-8 -*-
"""
Purchase Mapping v1 — durable Product ↔ Purchase links (foundation only).

Source of truth:
  * Purchase → ``PurchaseTruthRecord`` via ``record_purchase`` (Purchase Truth).
    This module never creates a second purchase source; facts are written only
    after Purchase Truth confirms a purchase.
  * Product identity → canonical key scheme of the Product Catalog applied to
    products present in the session (Cart Line Snapshots).

Mapping rule (v1): for each distinct canonical product present in the session
when purchase is confirmed, record one immutable ``Product ↔ purchase`` fact.
Multi-product purchases produce one fact per product. No attribution scoring,
ranking, or recommendations — truth only.

Immutability: rows are insert-only history. Duplicate safety uses deterministic
``dedup_hash`` (store, order key, product identity) with a unique constraint.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartLineSnapshot, ProductPurchaseMapping
from schema_product_purchase_mapping_v1 import ensure_product_purchase_mapping_schema
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    resolve_canonical_identity,
)
from services.product_data.product_purchase_types_v1 import (
    PURCHASE_SOURCE_TRUTH,
    PurchaseMappingPersistResult,
    purchase_mapping_to_dict,
)

log = logging.getLogger("cartflow")

MAX_SESSION_SNAPSHOTS = 50
MAX_PRODUCTS_PER_PURCHASE = 20


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _dedup_hash(
    store_slug: str,
    order_id: Optional[str],
    recovery_key: Optional[str],
    stable_identity_key: str,
) -> str:
    order_key = (order_id or "").strip() or (recovery_key or "").strip()
    canonical = {
        "store_slug": store_slug,
        "order_key": order_key,
        "stable_identity_key": stable_identity_key,
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _present_products_for_session(
    store_slug: str,
    session_id: str,
) -> list[dict[str, Any]]:
    """Distinct canonical products from immutable Cart Line Snapshots."""
    try:
        snaps = (
            db.session.query(CartLineSnapshot)
            .filter(
                CartLineSnapshot.store_slug == store_slug,
                CartLineSnapshot.session_id == session_id,
            )
            .order_by(CartLineSnapshot.captured_at.desc(), CartLineSnapshot.id.desc())
            .limit(MAX_SESSION_SNAPSHOTS)
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []

    by_key: dict[str, dict[str, Any]] = {}
    for snap in snaps:
        line = {
            "product_id": snap.product_id,
            "variant_id": snap.variant_id,
            "sku": snap.sku,
            "name": snap.name,
            "unit_price": snap.unit_price,
            "quantity": snap.quantity,
        }
        product = catalog_input_from_line(line)
        if product is None:
            continue
        resolution = resolve_canonical_identity(product)
        if resolution is None:
            continue
        key = resolution.stable_identity_key
        if key in by_key:
            continue
        qty = snap.quantity if snap.quantity is not None and snap.quantity > 0 else 1
        by_key[key] = {
            "stable_identity_key": key,
            "purchase_confidence": resolution.capture_confidence,
            "product_id": (product.product_id or None),
            "name": (product.name or None),
            "quantity": qty,
            "unit_price": snap.unit_price,
        }
        if len(by_key) >= MAX_PRODUCTS_PER_PURCHASE:
            break
    return list(by_key.values())


def persist_purchase_mappings(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    order_id: Optional[str] = None,
    purchase_source: str,
    purchased_at: Optional[datetime] = None,
) -> PurchaseMappingPersistResult:
    """
    Insert immutable Product ↔ Purchase mappings for products present in the session.
    Never updates existing rows; duplicates are skipped.
    """
    slug = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    source = (purchase_source or "").strip()[:128]
    cid = (cart_id or "").strip()[:255]
    rkey = (recovery_key or "").strip()[:512] or None
    oid = (order_id or "").strip()[:255] or None

    if not slug or not sid or not source:
        return PurchaseMappingPersistResult(skipped_invalid=1)

    products = _present_products_for_session(slug, sid)
    if not products:
        return PurchaseMappingPersistResult(skipped_empty=1)

    ensure_product_purchase_mapping_schema(db)
    when = _naive(purchased_at or _utc_now())

    inserted = 0
    skipped_duplicate = 0
    try:
        with db.session.begin_nested():
            for product in products:
                dedup = _dedup_hash(slug, oid, rkey, product["stable_identity_key"])
                exists = (
                    db.session.query(ProductPurchaseMapping.id)
                    .filter(ProductPurchaseMapping.dedup_hash == dedup)
                    .limit(1)
                    .first()
                )
                if exists is not None:
                    skipped_duplicate += 1
                    continue
                row = ProductPurchaseMapping(
                    store_slug=slug,
                    session_id=sid,
                    cart_id=cid,
                    recovery_key=rkey,
                    order_id=oid,
                    stable_identity_key=product["stable_identity_key"][:256],
                    product_id=product["product_id"],
                    name=product["name"],
                    quantity=product["quantity"],
                    unit_price=product["unit_price"],
                    purchase_confidence=product["purchase_confidence"],
                    purchase_source=source,
                    purchased_at=when,
                    dedup_hash=dedup,
                )
                db.session.add(row)
                inserted += 1
        if inserted:
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        log.warning("purchase mapping persist failed", exc_info=True)
        return PurchaseMappingPersistResult(
            inserted=0,
            skipped_duplicate=skipped_duplicate,
            skipped_invalid=max(1, len(products) - skipped_duplicate),
        )

    return PurchaseMappingPersistResult(
        inserted=inserted,
        skipped_duplicate=skipped_duplicate,
    )


def try_persist_purchase_mappings(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    order_id: Optional[str] = None,
    purchase_source: str,
    purchased_at: Optional[datetime] = None,
) -> None:
    """Non-blocking wrapper — never raises (failure safety)."""
    try:
        persist_purchase_mappings(
            store_slug,
            session_id,
            cart_id=cart_id,
            recovery_key=recovery_key,
            order_id=order_id,
            purchase_source=purchase_source,
            purchased_at=purchased_at,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("purchase mapping persist skipped: %s", exc)


def purchases_for_product(
    store_slug: str,
    stable_identity_key: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Which confirmed purchases included one canonical product."""
    slug = (store_slug or "").strip()[:255]
    key = (stable_identity_key or "").strip()[:256]
    if not slug or not key:
        return []
    ensure_product_purchase_mapping_schema(db)
    try:
        rows = (
            db.session.query(ProductPurchaseMapping)
            .filter(
                ProductPurchaseMapping.store_slug == slug,
                ProductPurchaseMapping.stable_identity_key == key,
            )
            .order_by(
                ProductPurchaseMapping.purchased_at.desc(),
                ProductPurchaseMapping.id.desc(),
            )
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []
    return [purchase_mapping_to_dict(r) for r in rows]


def products_for_purchase(
    store_slug: str,
    *,
    order_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Which canonical products were associated with one confirmed purchase."""
    slug = (store_slug or "").strip()[:255]
    oid = (order_id or "").strip()[:255] or None
    rkey = (recovery_key or "").strip()[:512] or None
    if not slug or (not oid and not rkey):
        return []
    ensure_product_purchase_mapping_schema(db)
    try:
        q = db.session.query(ProductPurchaseMapping).filter(
            ProductPurchaseMapping.store_slug == slug
        )
        if oid:
            q = q.filter(ProductPurchaseMapping.order_id == oid)
        else:
            q = q.filter(ProductPurchaseMapping.recovery_key == rkey)
        rows = (
            q.order_by(
                ProductPurchaseMapping.purchased_at.desc(),
                ProductPurchaseMapping.id.desc(),
            )
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []
    return [purchase_mapping_to_dict(r) for r in rows]


def purchase_mapping_count(store_slug: str) -> int:
    """Total Product ↔ Purchase mapping rows for one store."""
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return 0
    ensure_product_purchase_mapping_schema(db)
    try:
        return (
            db.session.query(ProductPurchaseMapping)
            .filter(ProductPurchaseMapping.store_slug == slug)
            .count()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0


__all__ = [
    "persist_purchase_mappings",
    "products_for_purchase",
    "purchase_mapping_count",
    "purchases_for_product",
    "try_persist_purchase_mappings",
]
