# -*- coding: utf-8 -*-
"""
Product catalog v1 — canonical mutable product entries (current truth).

Reads from cart line snapshots, Product Identity ``lines[]``, and
``cf_product_catalog_json``. Insert/update catalog only — snapshots stay immutable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartLineSnapshot, ProductCatalogEntry, Store
from schema_product_catalog_v1 import ensure_product_catalog_schema
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    parse_catalog_json_products,
    resolve_canonical_identity,
    same_product_merge_allowed,
)
from services.product_data.product_catalog_types_v1 import (
    CATALOG_SOURCE_CATALOG_JSON,
    CATALOG_SOURCE_PRODUCT_IDENTITY,
    CATALOG_SOURCE_SNAPSHOT,
    DEFAULT_CURRENCY,
    CatalogProductInput,
    CatalogUpsertResult,
    IdentityResolution,
    catalog_entry_to_dict,
)

log = logging.getLogger("cartflow")

MAX_LINES = 20


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _store_slug_from_payload(payload: dict[str, Any]) -> str:
    from main import _normalize_store_slug  # noqa: PLC0415

    return _normalize_store_slug(payload)[:255]


def _apply_mutable_fields(
    row: ProductCatalogEntry,
    product: CatalogProductInput,
    *,
    resolution: IdentityResolution,
    catalog_source: str,
    when: datetime,
) -> None:
    row.identity_tier = resolution.identity_tier
    row.stable_identity_key = resolution.stable_identity_key
    row.capture_confidence = resolution.capture_confidence
    row.catalog_source = catalog_source
    row.last_synced_at = when
    if product.product_id:
        row.product_id = product.product_id[:128]
    if product.variant_id:
        row.variant_id = product.variant_id[:128]
    if product.sku:
        row.sku = product.sku[:128]
    if product.name:
        row.name = product.name[:200]
    if product.category:
        row.category = product.category[:128]
    if product.price is not None:
        row.price = product.price
    if product.currency:
        row.currency = (product.currency or DEFAULT_CURRENCY)[:8]


def _find_merge_candidate(
    store_slug: str,
    product: CatalogProductInput,
    resolution: IdentityResolution,
) -> Optional[ProductCatalogEntry]:
    pid = (product.product_id or "").strip()
    if not pid:
        return None
    try:
        rows = (
            db.session.query(ProductCatalogEntry)
            .filter(
                ProductCatalogEntry.store_slug == store_slug,
                ProductCatalogEntry.product_id == pid,
            )
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None
    for row in rows:
        if row.stable_identity_key == resolution.stable_identity_key:
            return row
        if same_product_merge_allowed(
            row.identity_tier,
            resolution.identity_tier,
            existing_product_id=row.product_id or "",
            incoming_product_id=product.product_id,
        ):
            return row
    return None


def upsert_catalog_product(
    store_slug: str,
    product: CatalogProductInput,
    *,
    catalog_source: str,
    synced_at: Optional[datetime] = None,
) -> CatalogUpsertResult:
    """Upsert one canonical catalog entry. Never modifies snapshots."""
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return CatalogUpsertResult(skipped=1)

    resolution = resolve_canonical_identity(product)
    if resolution is None:
        return CatalogUpsertResult(skipped=1)

    ensure_product_catalog_schema(db)
    when = _naive(synced_at or _utc_now())

    try:
        with db.session.begin_nested():
            existing = (
                db.session.query(ProductCatalogEntry)
                .filter(
                    ProductCatalogEntry.store_slug == slug,
                    ProductCatalogEntry.stable_identity_key == resolution.stable_identity_key,
                )
                .first()
            )
            merged = False
            if existing is None:
                candidate = _find_merge_candidate(slug, product, resolution)
                if candidate is not None:
                    existing = candidate
                    merged = True

            if existing is not None:
                _apply_mutable_fields(
                    existing,
                    product,
                    resolution=resolution,
                    catalog_source=catalog_source,
                    when=when,
                )
                if merged:
                    return CatalogUpsertResult(updated=1, merged=1)
                return CatalogUpsertResult(updated=1)

            row = ProductCatalogEntry(
                store_slug=slug,
                stable_identity_key=resolution.stable_identity_key,
                identity_tier=resolution.identity_tier,
                product_id=(product.product_id or None),
                variant_id=(product.variant_id or None),
                sku=(product.sku or None),
                name=(product.name or None),
                category=(product.category or None),
                price=product.price,
                currency=(product.currency or DEFAULT_CURRENCY)[:8],
                capture_confidence=resolution.capture_confidence,
                catalog_source=catalog_source,
                first_seen_at=when,
                last_synced_at=when,
            )
            db.session.add(row)
            return CatalogUpsertResult(created=1)
    except SQLAlchemyError:
        log.warning("catalog upsert failed", exc_info=True)
        return CatalogUpsertResult(skipped=1)


def upsert_catalog_from_lines(
    store_slug: str,
    lines: list[dict[str, Any]],
    *,
    catalog_source: str = CATALOG_SOURCE_PRODUCT_IDENTITY,
) -> CatalogUpsertResult:
    total = CatalogUpsertResult()
    if not isinstance(lines, list):
        return total
    for raw in lines[:MAX_LINES]:
        if not isinstance(raw, dict):
            total = CatalogUpsertResult(
                created=total.created,
                updated=total.updated,
                skipped=total.skipped + 1,
                merged=total.merged,
            )
            continue
        product = catalog_input_from_line(raw)
        if product is None:
            total = CatalogUpsertResult(
                created=total.created,
                updated=total.updated,
                skipped=total.skipped + 1,
                merged=total.merged,
            )
            continue
        one = upsert_catalog_product(store_slug, product, catalog_source=catalog_source)
        total = CatalogUpsertResult(
            created=total.created + one.created,
            updated=total.updated + one.updated,
            skipped=total.skipped + one.skipped,
            merged=total.merged + one.merged,
        )
    return total


def upsert_catalog_from_payload_lines(
    payload: dict[str, Any],
    *,
    catalog_source: str = CATALOG_SOURCE_PRODUCT_IDENTITY,
) -> CatalogUpsertResult:
    if not isinstance(payload, dict):
        return CatalogUpsertResult(skipped=1)
    lines = payload.get("lines")
    if not isinstance(lines, list) or not lines:
        return CatalogUpsertResult(skipped=1)
    store_slug = _store_slug_from_payload(payload)
    return upsert_catalog_from_lines(store_slug, lines, catalog_source=catalog_source)


def sync_catalog_from_store_json(
    store_slug: str,
    *,
    store_row: Any | None = None,
) -> CatalogUpsertResult:
    """Normalize ``cf_product_catalog_json`` into canonical catalog entries."""
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return CatalogUpsertResult(skipped=1)

    row = store_row
    if row is None:
        try:
            row = db.session.query(Store).filter(Store.zid_store_id == slug).first()
        except SQLAlchemyError:
            db.session.rollback()
            return CatalogUpsertResult(skipped=1)

    raw_json = getattr(row, "cf_product_catalog_json", None) if row is not None else None
    products = parse_catalog_json_products(raw_json)
    if not products:
        return CatalogUpsertResult(skipped=1)

    total = CatalogUpsertResult()
    for product in products:
        one = upsert_catalog_product(
            slug, product, catalog_source=CATALOG_SOURCE_CATALOG_JSON
        )
        total = CatalogUpsertResult(
            created=total.created + one.created,
            updated=total.updated + one.updated,
            skipped=total.skipped + one.skipped,
            merged=total.merged + one.merged,
        )
    return total


def upsert_catalog_from_recent_snapshots(
    store_slug: str,
    *,
    limit: int = 50,
) -> CatalogUpsertResult:
    """Backfill catalog from recent cart line snapshots for one store."""
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return CatalogUpsertResult(skipped=1)

    ensure_product_catalog_schema(db)
    try:
        snaps = (
            db.session.query(CartLineSnapshot)
            .filter(CartLineSnapshot.store_slug == slug)
            .order_by(CartLineSnapshot.captured_at.desc(), CartLineSnapshot.id.desc())
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return CatalogUpsertResult(skipped=1)

    total = CatalogUpsertResult()
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
            total = CatalogUpsertResult(
                created=total.created,
                updated=total.updated,
                skipped=total.skipped + 1,
                merged=total.merged,
            )
            continue
        one = upsert_catalog_product(
            slug, product, catalog_source=CATALOG_SOURCE_SNAPSHOT
        )
        total = CatalogUpsertResult(
            created=total.created + one.created,
            updated=total.updated + one.updated,
            skipped=total.skipped + one.skipped,
            merged=total.merged + one.merged,
        )
    return total


def catalog_entries_for_store(
    store_slug: str,
    *,
    limit: int = 100,
) -> list[ProductCatalogEntry]:
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return []
    ensure_product_catalog_schema(db)
    try:
        return (
            db.session.query(ProductCatalogEntry)
            .filter(ProductCatalogEntry.store_slug == slug)
            .order_by(ProductCatalogEntry.last_synced_at.desc(), ProductCatalogEntry.id.desc())
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []


def catalog_entry_by_identity_key(
    store_slug: str,
    stable_identity_key: str,
) -> Optional[ProductCatalogEntry]:
    slug = (store_slug or "").strip()[:255]
    key = (stable_identity_key or "").strip()[:256]
    if not slug or not key:
        return None
    ensure_product_catalog_schema(db)
    try:
        return (
            db.session.query(ProductCatalogEntry)
            .filter(
                ProductCatalogEntry.store_slug == slug,
                ProductCatalogEntry.stable_identity_key == key,
            )
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def catalog_count_for_store(store_slug: str) -> int:
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return 0
    ensure_product_catalog_schema(db)
    try:
        return (
            db.session.query(ProductCatalogEntry)
            .filter(ProductCatalogEntry.store_slug == slug)
            .count()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0


def catalog_entries_as_dicts(store_slug: str, *, limit: int = 100) -> list[dict[str, Any]]:
    return [catalog_entry_to_dict(r) for r in catalog_entries_for_store(store_slug, limit=limit)]


__all__ = [
    "catalog_count_for_store",
    "catalog_entries_as_dicts",
    "catalog_entries_for_store",
    "catalog_entry_by_identity_key",
    "sync_catalog_from_store_json",
    "upsert_catalog_from_payload_lines",
    "upsert_catalog_from_lines",
    "upsert_catalog_from_recent_snapshots",
    "upsert_catalog_product",
]
