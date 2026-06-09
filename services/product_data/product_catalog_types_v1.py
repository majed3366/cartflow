# -*- coding: utf-8 -*-
"""Product Data Foundation v1 — canonical catalog types and identity tiers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from services.product_data.product_data_types_v1 import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
)

# Identity tier labels (architecture review v1)
IDENTITY_TIER_A = "A"  # product_id + variant_id
IDENTITY_TIER_B = "B"  # product_id + sku
IDENTITY_TIER_C = "C"  # product_id
IDENTITY_TIER_D = "D"  # sku
IDENTITY_TIER_E = "E"  # normalized name hash (last resort)

IDENTITY_TIER_VALUES = frozenset(
    {IDENTITY_TIER_A, IDENTITY_TIER_B, IDENTITY_TIER_C, IDENTITY_TIER_D, IDENTITY_TIER_E}
)

# Catalog ingest sources (allowed inputs only)
CATALOG_SOURCE_SNAPSHOT = "cart_line_snapshot"
CATALOG_SOURCE_PRODUCT_IDENTITY = "product_identity"
CATALOG_SOURCE_CATALOG_JSON = "cf_product_catalog_json"

CATALOG_SOURCE_VALUES = frozenset(
    {
        CATALOG_SOURCE_SNAPSHOT,
        CATALOG_SOURCE_PRODUCT_IDENTITY,
        CATALOG_SOURCE_CATALOG_JSON,
    }
)

DEFAULT_CURRENCY = "SAR"


@dataclass(frozen=True, slots=True)
class CatalogProductInput:
    """Normalized product facts before identity resolution."""

    product_id: str = ""
    variant_id: str = ""
    sku: str = ""
    name: str = ""
    category: str = ""
    price: Optional[float] = None
    currency: str = DEFAULT_CURRENCY


@dataclass(frozen=True, slots=True)
class IdentityResolution:
    """Result of canonical identity precedence rules."""

    stable_identity_key: str
    identity_tier: str
    capture_confidence: str


@dataclass(frozen=True, slots=True)
class CatalogUpsertResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    merged: int = 0


def tier_confidence(tier: str) -> str:
    if tier == IDENTITY_TIER_A:
        return CONFIDENCE_HIGH
    if tier in (IDENTITY_TIER_B, IDENTITY_TIER_C, IDENTITY_TIER_D):
        return CONFIDENCE_MEDIUM
    if tier == IDENTITY_TIER_E:
        return CONFIDENCE_LOW
    return CONFIDENCE_LOW


def catalog_entry_to_dict(row: Any) -> dict[str, Any]:
    """Read-model dict for tests and read helpers."""
    return {
        "id": getattr(row, "id", None),
        "store_slug": getattr(row, "store_slug", "") or "",
        "stable_identity_key": getattr(row, "stable_identity_key", "") or "",
        "identity_tier": getattr(row, "identity_tier", "") or "",
        "product_id": getattr(row, "product_id", None),
        "variant_id": getattr(row, "variant_id", None),
        "sku": getattr(row, "sku", None),
        "name": getattr(row, "name", None),
        "category": getattr(row, "category", None),
        "price": getattr(row, "price", None),
        "currency": getattr(row, "currency", None),
        "capture_confidence": getattr(row, "capture_confidence", "") or "",
        "catalog_source": getattr(row, "catalog_source", "") or "",
        "first_seen_at": getattr(row, "first_seen_at", None),
        "last_synced_at": getattr(row, "last_synced_at", None),
    }
