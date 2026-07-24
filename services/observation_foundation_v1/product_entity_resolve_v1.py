# -*- coding: utf-8 -*-
"""
Resolve a real merchant-facing product display name for observation findings.

No demo keys. No placeholders. No inferred names.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from services.product_data.product_identity_authenticity_v1 import (
    text_has_forbidden_product_placeholder,
    unresolved_product_identity_ar,
)

_BANNED_KEY_RE = re.compile(
    r"^(?:demo(?:[-_].*)?|orv[-_].*|test[-_].*|sample[-_].*)$",
    re.IGNORECASE,
)
_BANNED_KEYS = frozenset(
    {
        "demo-perfume",
        "demo_perfume",
        "demo",
        "perfume",
        "product",
        "unknown",
        "n/a",
        "na",
        "none",
        "null",
    }
)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def is_banned_product_key_v1(product_key: Any) -> bool:
    key = _norm(product_key)
    if not key:
        return True
    low = key.lower()
    if low in _BANNED_KEYS:
        return True
    if _BANNED_KEY_RE.match(low):
        return True
    if "demo-perfume" in low or low.startswith("demo"):
        return True
    if low.startswith("orv-") or low.startswith("orv_"):
        return True
    return False


_BANNED_DISPLAY_NAMES = frozenset(
    {
        "هذا المنتج",
        "هذاالمنتج",
        "المنتج",
        "منتج",
        "product",
        "this product",
        "unknown product",
    }
)


def is_real_product_display_name_v1(name: Any) -> bool:
    raw = _norm(name)
    if not raw:
        return False
    if raw == unresolved_product_identity_ar():
        return False
    if raw in _BANNED_DISPLAY_NAMES or raw.lower() in _BANNED_DISPLAY_NAMES:
        return False
    if "هذا المنتج" in raw:
        return False
    if text_has_forbidden_product_placeholder(raw):
        return False
    if is_banned_product_key_v1(raw):
        return False
    # Reject bare technical keys used as names
    if raw.lower().startswith("sku:") or raw.lower().startswith("pid:"):
        return False
    if re.fullmatch(r"[0-9a-f]{8,}", raw.lower()):
        return False
    return True


def resolve_real_product_display_name_v1(
    store_slug: str,
    product_key: Any,
) -> Optional[str]:
    """
    Return a merchant display name for ``product_key``, or None when unknown.

    Lookup order: product_catalog_entries → cart_line_snapshots.
    """
    slug = _norm(store_slug)
    key = _norm(product_key)
    if not slug or is_banned_product_key_v1(key):
        return None

    try:
        from extensions import db
        from models import CartLineSnapshot, ProductCatalogEntry
    except Exception:  # noqa: BLE001
        return None

    try:
        rows = (
            db.session.query(ProductCatalogEntry)
            .filter(ProductCatalogEntry.store_slug == slug)
            .order_by(ProductCatalogEntry.id.desc())
            .limit(200)
            .all()
        )
        for row in rows:
            candidates = (
                _norm(getattr(row, "stable_identity_key", None)),
                _norm(getattr(row, "sku", None)),
                _norm(getattr(row, "product_id", None)),
                _norm(getattr(row, "name", None)),
            )
            if key not in candidates and key.lower() not in {
                c.lower() for c in candidates if c
            }:
                continue
            name = _norm(getattr(row, "name", None))
            if is_real_product_display_name_v1(name):
                return name
    except Exception:  # noqa: BLE001
        pass

    try:
        snaps = (
            db.session.query(CartLineSnapshot)
            .filter(CartLineSnapshot.store_slug == slug)
            .order_by(CartLineSnapshot.id.desc())
            .limit(300)
            .all()
        )
        for snap in snaps:
            candidates = (
                _norm(getattr(snap, "sku", None)),
                _norm(getattr(snap, "product_id", None)),
                _norm(getattr(snap, "name", None)),
            )
            if key not in candidates and key.lower() not in {
                c.lower() for c in candidates if c
            }:
                # also allow stable-style keys like sku:XXX
                if not any(
                    key.lower().endswith((":" + c.lower()) if c else "\0")
                    for c in candidates
                ):
                    continue
            name = _norm(getattr(snap, "name", None))
            if is_real_product_display_name_v1(name):
                return name
    except Exception:  # noqa: BLE001
        pass

    # Last resort: product_key itself only if it already looks like a real name
    if is_real_product_display_name_v1(key) and " " in key:
        return key
    return None


__all__ = [
    "is_banned_product_key_v1",
    "is_real_product_display_name_v1",
    "resolve_real_product_display_name_v1",
]
