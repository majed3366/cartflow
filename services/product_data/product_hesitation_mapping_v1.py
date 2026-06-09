# -*- coding: utf-8 -*-
"""
Hesitation Mapping v1 — durable Product ↔ Reason links (foundation only).

Source of truth:
  * Product identity → canonical key scheme of the Product Catalog
    (``resolve_canonical_identity``), applied to the products that were actually
    present in the cart/session (Cart Line Snapshots).
  * Reason → ``CartRecoveryReason`` (reason capture truth). This module never
    creates a second reason source; the captured reason is passed in by the
    reason-capture write path.

Mapping rule (v1): for each distinct canonical product present in the session,
record one immutable ``Product ↔ reason`` fact. Multi-product carts produce one
fact per product for the same hesitation event. No scoring, no weighting, no AI,
no blame attribution — truth first, inference later.

Immutability: rows are insert-only history. Existing rows are never overwritten
or reclassified. Duplicate safety is enforced by a deterministic ``dedup_hash``
(store, session, cart, product identity, reason, sub_reason) with a unique
constraint, which bounds growth.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartLineSnapshot, ProductHesitationMapping
from schema_product_hesitation_mapping_v1 import (
    ensure_product_hesitation_mapping_schema,
)
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    resolve_canonical_identity,
)
from services.product_data.product_hesitation_types_v1 import (
    MAPPING_SOURCE_REASON_CAPTURE,
    HesitationMappingPersistResult,
    hesitation_mapping_to_dict,
    normalize_reason,
    normalize_sub_reason,
)

log = logging.getLogger("cartflow")

# Bound how many recent session snapshots we scan to discover present products.
MAX_SESSION_SNAPSHOTS = 50
# Bound distinct products mapped per hesitation event (sane multi-product ceiling).
MAX_PRODUCTS_PER_EVENT = 20


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _dedup_hash(
    store_slug: str,
    session_id: str,
    cart_id: str,
    stable_identity_key: str,
    reason: str,
    sub_reason: Optional[str],
) -> str:
    canonical = {
        "store_slug": store_slug,
        "session_id": session_id,
        "cart_id": cart_id or "",
        "stable_identity_key": stable_identity_key,
        "reason": reason,
        "sub_reason": sub_reason or "",
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _present_products_for_session(
    store_slug: str,
    session_id: str,
) -> list[dict[str, Any]]:
    """
    Resolve the distinct canonical products present in a session from immutable
    Cart Line Snapshots. Returns one entry per ``stable_identity_key``.
    """
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
        by_key[key] = {
            "stable_identity_key": key,
            "identity_tier": resolution.identity_tier,
            "mapping_confidence": resolution.capture_confidence,
            "product_id": (product.product_id or None),
            "name": (product.name or None),
        }
        if len(by_key) >= MAX_PRODUCTS_PER_EVENT:
            break
    return list(by_key.values())


def persist_hesitation_mappings(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    reason: str,
    sub_reason: Optional[str] = None,
    captured_at: Optional[datetime] = None,
    mapping_source: str = MAPPING_SOURCE_REASON_CAPTURE,
) -> HesitationMappingPersistResult:
    """
    Insert immutable Product ↔ Reason mappings for every canonical product present
    in the session. Never updates existing rows; duplicates are skipped.
    """
    slug = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    norm_reason = normalize_reason(reason)
    norm_sub = normalize_sub_reason(sub_reason)
    cid = (cart_id or "").strip()[:255]
    rkey = (recovery_key or "").strip()[:512] or None

    if not slug or not sid or not norm_reason:
        return HesitationMappingPersistResult(skipped_invalid=1)

    products = _present_products_for_session(slug, sid)
    if not products:
        return HesitationMappingPersistResult(skipped_empty=1)

    ensure_product_hesitation_mapping_schema(db)
    when = _naive(captured_at or _utc_now())

    inserted = 0
    skipped_duplicate = 0
    try:
        with db.session.begin_nested():
            for product in products:
                dedup = _dedup_hash(
                    slug, sid, cid, product["stable_identity_key"], norm_reason, norm_sub
                )
                exists = (
                    db.session.query(ProductHesitationMapping.id)
                    .filter(ProductHesitationMapping.dedup_hash == dedup)
                    .limit(1)
                    .first()
                )
                if exists is not None:
                    skipped_duplicate += 1
                    continue
                row = ProductHesitationMapping(
                    store_slug=slug,
                    session_id=sid,
                    cart_id=cid,
                    recovery_key=rkey,
                    stable_identity_key=product["stable_identity_key"][:256],
                    identity_tier=product["identity_tier"],
                    product_id=product["product_id"],
                    name=product["name"],
                    reason=norm_reason,
                    sub_reason=norm_sub,
                    mapping_confidence=product["mapping_confidence"],
                    mapping_source=(mapping_source or MAPPING_SOURCE_REASON_CAPTURE)[:32],
                    captured_at=when,
                    dedup_hash=dedup,
                )
                db.session.add(row)
                inserted += 1
        if inserted:
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        log.warning("hesitation mapping persist failed", exc_info=True)
        return HesitationMappingPersistResult(
            inserted=0,
            skipped_duplicate=skipped_duplicate,
            skipped_invalid=max(1, len(products) - skipped_duplicate),
        )

    return HesitationMappingPersistResult(
        inserted=inserted,
        skipped_duplicate=skipped_duplicate,
    )


def try_persist_hesitation_mappings(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    reason: str,
    sub_reason: Optional[str] = None,
) -> None:
    """Non-blocking wrapper — never raises (failure safety)."""
    try:
        persist_hesitation_mappings(
            store_slug,
            session_id,
            cart_id=cart_id,
            recovery_key=recovery_key,
            reason=reason,
            sub_reason=sub_reason,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("hesitation mapping persist skipped: %s", exc)


# ----------------------------------------------------------------------------
# Read helpers (no UI, no API, no scoring) — historical fact lookups only.
# ----------------------------------------------------------------------------


def reasons_for_product(
    store_slug: str,
    stable_identity_key: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Which hesitation reasons were recorded for one canonical product."""
    slug = (store_slug or "").strip()[:255]
    key = (stable_identity_key or "").strip()[:256]
    if not slug or not key:
        return []
    ensure_product_hesitation_mapping_schema(db)
    try:
        rows = (
            db.session.query(ProductHesitationMapping)
            .filter(
                ProductHesitationMapping.store_slug == slug,
                ProductHesitationMapping.stable_identity_key == key,
            )
            .order_by(
                ProductHesitationMapping.captured_at.desc(),
                ProductHesitationMapping.id.desc(),
            )
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []
    return [hesitation_mapping_to_dict(r) for r in rows]


def products_for_reason(
    store_slug: str,
    reason: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Which canonical products were associated with one hesitation reason."""
    slug = (store_slug or "").strip()[:255]
    norm_reason = normalize_reason(reason)
    if not slug or not norm_reason:
        return []
    ensure_product_hesitation_mapping_schema(db)
    try:
        rows = (
            db.session.query(ProductHesitationMapping)
            .filter(
                ProductHesitationMapping.store_slug == slug,
                ProductHesitationMapping.reason == norm_reason,
            )
            .order_by(
                ProductHesitationMapping.captured_at.desc(),
                ProductHesitationMapping.id.desc(),
            )
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []
    return [hesitation_mapping_to_dict(r) for r in rows]


def mapping_count_for_store(store_slug: str) -> int:
    """Total Product ↔ Reason mapping rows for one store."""
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return 0
    ensure_product_hesitation_mapping_schema(db)
    try:
        return (
            db.session.query(ProductHesitationMapping)
            .filter(ProductHesitationMapping.store_slug == slug)
            .count()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0


__all__ = [
    "mapping_count_for_store",
    "persist_hesitation_mappings",
    "products_for_reason",
    "reasons_for_product",
    "try_persist_hesitation_mappings",
]
