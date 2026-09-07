# -*- coding: utf-8 -*-
"""
Product read-model contract V1 — freeze only.

Future Products surface consumes these fields from existing tables.
This module does not implement the Products page, invent metrics, or
claim unique visitors / real merchant PDP views.
"""
from __future__ import annotations

from typing import FrozenSet, Tuple

PRODUCT_READ_MODEL_SCHEMA = "product_read_model_v1"
PRODUCT_READ_MODEL_VERSION = "1"

# Authoritative identity / commercial facts (existing models).
AUTHORITATIVE_FIELDS: Tuple[str, ...] = (
    "product_id",
    "name",
    "price",
    "currency",
    "missing_name",
    "cart_count",
    "cart_value",
    "purchase_count",
    "revenue",
    "hesitation_reason_counts",
    "commercial_family",
    "recommendation_ar",
    "recheck_at_hint_ar",
    "known_unknowns",
)

# Sources — do not add a second table.
FIELD_SOURCES = {
    "product_id": "ProductCatalogEntry + cart_line_snapshots",
    "name": "ProductCatalogEntry.name / line name",
    "price": "ProductCatalogEntry.price / line unit_price",
    "cart_count": "cart_line_snapshots grouped by product_id",
    "cart_value": "AbandonedCart.cart_value for sessions with that product_id",
    "purchase_count": "purchase_mapping / purchase_truth",
    "revenue": "purchase_truth attributed amount (0 is a real zero)",
    "hesitation_reason_counts": (
        "CartRecoveryReason.store_slug joined to sessions that contain the product"
    ),
    "commercial_family": (
        "COL family only when product-scoped join is proven; else store-level "
        "with attribution_boundary=store"
    ),
}

# Never claim these until a real merchant capability exists.
KNOWN_UNKNOWNS: FrozenSet[str] = frozenset(
    {
        "unique_visitors",
        "real_merchant_pdp_views",
        "pixel_product_viewed",
        "product_scoped_shipping_count_without_session_join",
    }
)

VISIT_FIELD_CLASS_LAB_ONLY = "LAB-SYNTHETIC PRODUCTION-SHAPED VISIT TRUTH"
VISIT_FIELD_NAME = "lab_synthetic_visit_count"

# Store-level hesitation may annotate a product as context, never as a causal count.
PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED = False


def visit_field_label(*, lab_tenant: bool) -> str:
    """Lab tenant visits stay labeled. Normal merchants: field omitted / unknown."""
    if lab_tenant:
        return VISIT_FIELD_CLASS_LAB_ONLY
    return "NOT_STORED"


def product_scoped_shipping_claim_allowed(
    *,
    product_hesitation_n: int,
    store_shipping_n: int,
) -> bool:
    """Refuse store-level shipping counts as a product causal claim."""
    del product_hesitation_n, store_shipping_n
    return PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED


__all__ = [
    "AUTHORITATIVE_FIELDS",
    "FIELD_SOURCES",
    "KNOWN_UNKNOWNS",
    "PRODUCT_READ_MODEL_SCHEMA",
    "PRODUCT_READ_MODEL_VERSION",
    "PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED",
    "VISIT_FIELD_CLASS_LAB_ONLY",
    "VISIT_FIELD_NAME",
    "product_scoped_shipping_claim_allowed",
    "visit_field_label",
]
