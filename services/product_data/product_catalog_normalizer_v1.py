# -*- coding: utf-8 -*-
"""
Product catalog normalizer v1 — canonical identity precedence (no intelligence).

Tier order (architecture review v1):
  A: product_id + variant_id
  B: product_id + sku
  C: product_id
  D: sku
  E: normalized name hash (low confidence only)
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

from services.product_data.product_catalog_types_v1 import (
    DEFAULT_CURRENCY,
    IDENTITY_TIER_A,
    IDENTITY_TIER_B,
    IDENTITY_TIER_C,
    IDENTITY_TIER_D,
    IDENTITY_TIER_E,
    CatalogProductInput,
    IdentityResolution,
    tier_confidence,
)

_WS_RE = re.compile(r"\s+")


def _norm_str(value: Any, *, max_len: int) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    return s[:max_len]


def normalize_product_name(name: Any) -> str:
    raw = _norm_str(name, max_len=200)
    if not raw:
        return ""
    collapsed = _WS_RE.sub(" ", raw.lower())
    return collapsed.strip()


def _norm_price(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            n = float(value)
        else:
            n = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if not (n == n):
        return None
    return round(n, 4)


def _norm_currency(value: Any) -> str:
    c = _norm_str(value, max_len=8).upper()
    return c or DEFAULT_CURRENCY


def catalog_input_from_line(line: dict[str, Any]) -> Optional[CatalogProductInput]:
    """Normalize widget Product Identity line or cart snapshot shape."""
    if not isinstance(line, dict):
        return None

    product_id = _norm_str(line.get("product_id"), max_len=128)
    if not product_id:
        prod = line.get("product")
        if isinstance(prod, dict):
            product_id = _norm_str(prod.get("id"), max_len=128)
        raw_id = _norm_str(line.get("id"), max_len=128)
        variant_id_probe = _norm_str(line.get("variant_id"), max_len=128)
        if raw_id and not variant_id_probe:
            product_id = product_id or raw_id

    variant_id = _norm_str(line.get("variant_id"), max_len=128)
    sku = _norm_str(line.get("sku") or line.get("product_num"), max_len=128)
    name = _norm_str(
        line.get("name")
        or line.get("title")
        or line.get("product_name")
        or (line.get("product") or {}).get("name"),
        max_len=200,
    )
    category = _norm_str(
        line.get("category")
        or line.get("normalized_category")
        or (line.get("product") or {}).get("category"),
        max_len=128,
    )
    price = _norm_price(
        line.get("unit_price")
        if line.get("unit_price") is not None
        else line.get("price")
    )
    currency = _norm_currency(line.get("currency"))

    if not any((product_id, variant_id, sku, name)):
        return None

    return CatalogProductInput(
        product_id=product_id,
        variant_id=variant_id,
        sku=sku,
        name=name,
        category=category,
        price=price,
        currency=currency,
    )


def catalog_input_from_catalog_json_product(prod: dict[str, Any]) -> Optional[CatalogProductInput]:
    """Normalize one product dict from ``cf_product_catalog_json``."""
    if not isinstance(prod, dict):
        return None
    product_id = _norm_str(prod.get("id") or prod.get("product_id") or prod.get("key"), max_len=128)
    variant_id = _norm_str(prod.get("variant_id"), max_len=128)
    sku = _norm_str(prod.get("sku"), max_len=128)
    name = _norm_str(prod.get("name") or prod.get("title"), max_len=200)
    category = _norm_str(prod.get("category") or prod.get("normalized_category"), max_len=128)
    price = _norm_price(prod.get("price") if prod.get("price") is not None else prod.get("unit_price"))
    currency = _norm_currency(prod.get("currency"))
    if not any((product_id, variant_id, sku, name)):
        return None
    return CatalogProductInput(
        product_id=product_id,
        variant_id=variant_id,
        sku=sku,
        name=name,
        category=category,
        price=price,
        currency=currency,
    )


def parse_catalog_json_products(raw_json: Any) -> list[CatalogProductInput]:
    """Extract product list from ``cf_product_catalog_json`` text or dict."""
    data: Any = raw_json
    if isinstance(raw_json, str):
        text = raw_json.strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
    if not isinstance(data, dict):
        return []
    products = data.get("products")
    if not isinstance(products, list):
        return []
    out: list[CatalogProductInput] = []
    for item in products[:500]:
        parsed = catalog_input_from_catalog_json_product(item)
        if parsed is not None:
            out.append(parsed)
    return out


def resolve_canonical_identity(product: CatalogProductInput) -> Optional[IdentityResolution]:
    """
    Compute stable identity key using approved precedence order.
    Never uses name-hash when product_id is present.
    """
    pid = product.product_id.strip()
    vid = product.variant_id.strip()
    sku = product.sku.strip()
    name_norm = normalize_product_name(product.name)

    if pid and vid:
        key = f"a|{pid}|{vid}"
        return IdentityResolution(key, IDENTITY_TIER_A, tier_confidence(IDENTITY_TIER_A))
    if pid and sku:
        key = f"b|{pid}|{sku.lower()}"
        return IdentityResolution(key, IDENTITY_TIER_B, tier_confidence(IDENTITY_TIER_B))
    if pid:
        key = f"c|{pid}"
        return IdentityResolution(key, IDENTITY_TIER_C, tier_confidence(IDENTITY_TIER_C))
    if sku:
        key = f"d|{sku.lower()}"
        return IdentityResolution(key, IDENTITY_TIER_D, tier_confidence(IDENTITY_TIER_D))
    if name_norm:
        name_hash = hashlib.sha256(name_norm.encode("utf-8")).hexdigest()[:32]
        key = f"e|{name_hash}"
        return IdentityResolution(key, IDENTITY_TIER_E, tier_confidence(IDENTITY_TIER_E))
    return None


def tier_rank(tier: str) -> int:
    """Lower rank = higher identity confidence."""
    return {
        IDENTITY_TIER_A: 0,
        IDENTITY_TIER_B: 1,
        IDENTITY_TIER_C: 2,
        IDENTITY_TIER_D: 3,
        IDENTITY_TIER_E: 4,
    }.get(tier, 99)


def same_product_merge_allowed(
    existing_tier: str,
    incoming_tier: str,
    *,
    existing_product_id: str,
    incoming_product_id: str,
) -> bool:
    """
    Allow upgrading a weaker catalog row when incoming identity is stronger
    for the same platform product_id (duplicate merge).
    """
    ep = (existing_product_id or "").strip()
    ip = (incoming_product_id or "").strip()
    if not ep or not ip or ep != ip:
        return False
    return tier_rank(incoming_tier) < tier_rank(existing_tier)


__all__ = [
    "catalog_input_from_catalog_json_product",
    "catalog_input_from_line",
    "normalize_product_name",
    "parse_catalog_json_products",
    "resolve_canonical_identity",
    "same_product_merge_allowed",
    "tier_rank",
]
