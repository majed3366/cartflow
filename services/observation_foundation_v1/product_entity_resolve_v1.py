# -*- coding: utf-8 -*-
"""
Resolve a real merchant-facing product display name for observation findings.

No demo placeholders as display names. No inferred invented names.
Supports Product Identity tier keys: a|…, b|pid|sku, c|pid, d|sku.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from services.product_data.product_identity_authenticity_v1 import (
    text_has_forbidden_product_placeholder,
    unresolved_product_identity_ar,
)

_BANNED_KEY_RE = re.compile(
    r"^(?:orv[-_].*|test[-_].*|sample[-_].*)$",
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


def parse_identity_key_segments_v1(product_key: Any) -> list[str]:
    """
    Expand a product key into lookup segments.

    Examples:
      b|demo_watch_band|demo-watch-band → [full, demo_watch_band, demo-watch-band, DEMO-WATCH-BAND]
      sku:rose-oil → [sku:rose-oil, rose-oil]
      DEMO-CHARGER → [DEMO-CHARGER, demo-charger]
    """
    key = _norm(product_key)
    if not key:
        return []
    out: list[str] = [key]
    low = key.lower()

    # Tiered Product Identity keys
    if "|" in key:
        parts = [p for p in key.split("|") if p]
        # Drop tier letter segment (a/b/c/d)
        body = parts[1:] if parts and len(parts[0]) == 1 and parts[0].isalpha() else parts
        for p in body:
            out.append(p)
            out.append(p.lower())
            out.append(p.upper())
            out.append(p.replace("_", "-"))
            out.append(p.replace("-", "_"))
            # demo_watch_band → watch_band variants not needed; keep as-is

    if ":" in key:
        _, _, rest = key.partition(":")
        if rest:
            out.append(rest)
            out.append(rest.lower())

    out.append(low)
    # Dedupe preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        s2 = _norm(s)
        if not s2 or s2 in seen:
            continue
        seen.add(s2)
        uniq.append(s2)
    return uniq


def is_banned_product_key_v1(product_key: Any) -> bool:
    """
    True for placeholder / synthetic keys that must never become merchant findings.

    Does **not** ban Product Identity composite keys (`b|demo_watch_band|…`) —
    those are resolved to real catalog/snapshot display names.
    Does **not** ban sandbox product_ids solely because they start with ``demo_``
    when a real display name can be proven later.
    """
    key = _norm(product_key)
    if not key:
        return True
    low = key.lower()
    if low in _BANNED_KEYS:
        return True
    if _BANNED_KEY_RE.match(low):
        return True
    # Exact synthetic perfume mass key only — do NOT substring-match demo_perfume_velvet.
    if low in {"demo-perfume", "demo_perfume"}:
        return True
    if low.endswith("|demo-perfume") or low.endswith("|demo_perfume"):
        return True
    if low == "b|demo_perfume|demo-perfume" or low == "b|demo-perfume|demo-perfume":
        return True
    # Bare "demo" only — not demo_watch_band / b|demo_…
    if low == "demo":
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
    # Never treat a banned placeholder key as a display name
    if raw.lower() in _BANNED_KEYS or "demo-perfume" in raw.lower():
        return False
    if raw.lower().startswith("sku:") or raw.lower().startswith("pid:"):
        return False
    if re.fullmatch(r"[0-9a-f]{8,}", raw.lower()):
        return False
    # Technical identity keys are not display names
    if "|" in raw and re.match(r"^[a-d]\|", raw.lower()):
        return False
    if raw.lower().startswith("demo_") or raw.lower().startswith("demo-"):
        # Allow only if it looks like a human name with spaces/Arabic (rare)
        if " " not in raw and not re.search(r"[\u0600-\u06FF]", raw):
            return False
    return True


def _segments_match(key_segments: list[str], candidates: tuple[str, ...]) -> bool:
    cand_set = {c.lower() for c in candidates if c}
    if not cand_set:
        return False
    for seg in key_segments:
        if seg.lower() in cand_set:
            return True
        # suffix :sku style
        for c in cand_set:
            if seg.lower().endswith(":" + c) or c.endswith(":" + seg.lower()):
                return True
    return False


def resolve_real_product_display_name_v1(
    store_slug: str,
    product_key: Any,
) -> Optional[str]:
    """
    Return a merchant display name for ``product_key``, or None when unknown.

    Lookup order:
      product_catalog_entries → cart_line_snapshots → hesitation/purchase mappings.
    """
    slug = _norm(store_slug)
    key = _norm(product_key)
    if not slug or not key:
        return None
    low = key.lower()
    # Hard placeholders never resolve.
    if is_banned_product_key_v1(key) and "|" not in key:
        return None
    if low in {"demo-perfume", "demo_perfume"}:
        return None
    if low.startswith("orv-") or low.startswith("orv_"):
        return None

    segments = parse_identity_key_segments_v1(key)

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
            .limit(400)
            .all()
        )
        for row in rows:
            candidates = (
                _norm(getattr(row, "stable_identity_key", None)),
                _norm(getattr(row, "sku", None)),
                _norm(getattr(row, "product_id", None)),
                _norm(getattr(row, "name", None)),
            )
            if key in candidates or key.lower() in {c.lower() for c in candidates if c}:
                name = _norm(getattr(row, "name", None))
                if is_real_product_display_name_v1(name):
                    return name
            if _segments_match(segments, candidates):
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
            .limit(500)
            .all()
        )
        for snap in snaps:
            candidates = (
                _norm(getattr(snap, "sku", None)),
                _norm(getattr(snap, "product_id", None)),
                _norm(getattr(snap, "name", None)),
            )
            if key in candidates or key.lower() in {c.lower() for c in candidates if c}:
                name = _norm(getattr(snap, "name", None))
                if is_real_product_display_name_v1(name):
                    return name
            if _segments_match(segments, candidates):
                name = _norm(getattr(snap, "name", None))
                if is_real_product_display_name_v1(name):
                    return name
    except Exception:  # noqa: BLE001
        pass

    # Hesitation / purchase mappings often store stable_identity_key + display name
    try:
        from models import ProductHesitationMapping  # type: ignore

        maps = (
            db.session.query(ProductHesitationMapping)
            .filter(ProductHesitationMapping.store_slug == slug)
            .order_by(ProductHesitationMapping.id.desc())
            .limit(400)
            .all()
        )
        for row in maps:
            candidates = (
                _norm(getattr(row, "stable_identity_key", None)),
                _norm(getattr(row, "sku", None)),
                _norm(getattr(row, "product_id", None)),
            )
            if key in candidates or _segments_match(segments, candidates):
                name = _norm(getattr(row, "name", None) or getattr(row, "product_name", None))
                if is_real_product_display_name_v1(name):
                    return name
    except Exception:  # noqa: BLE001
        pass

    try:
        from models import ProductPurchaseMapping  # type: ignore

        maps = (
            db.session.query(ProductPurchaseMapping)
            .filter(ProductPurchaseMapping.store_slug == slug)
            .order_by(ProductPurchaseMapping.id.desc())
            .limit(400)
            .all()
        )
        for row in maps:
            candidates = (
                _norm(getattr(row, "stable_identity_key", None)),
                _norm(getattr(row, "sku", None)),
                _norm(getattr(row, "product_id", None)),
            )
            if key in candidates or _segments_match(segments, candidates):
                name = _norm(getattr(row, "name", None) or getattr(row, "product_name", None))
                if is_real_product_display_name_v1(name):
                    return name
    except Exception:  # noqa: BLE001
        pass

    # Last resort: product_key itself only if it already looks like a real name
    if is_real_product_display_name_v1(key) and (" " in key or re.search(r"[\u0600-\u06FF]", key)):
        return key
    return None


__all__ = [
    "is_banned_product_key_v1",
    "is_real_product_display_name_v1",
    "parse_identity_key_segments_v1",
    "resolve_real_product_display_name_v1",
]
