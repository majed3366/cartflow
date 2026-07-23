# -*- coding: utf-8 -*-
"""
Product Identity Cart Projection V1 — attach governed product identity to cart rows.

Presentation-safe: real snapshot/catalog names, or explicit unresolved.
Never fabricates Product X / placeholder labels.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Mapping, MutableMapping, Optional

from sqlalchemy.exc import SQLAlchemyError

from services.product_data.product_identity_authenticity_v1 import (
    text_has_forbidden_product_placeholder,
    unresolved_product_identity_ar,
)

log = logging.getLogger("cartflow")

PROJECTION_VERSION = "product_identity_cart_projection_v1"
STATUS_RESOLVED = "resolved"
STATUS_UNRESOLVED = "unresolved"


def _norm(value: Any, *, max_len: int = 200) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    return s[:max_len]


def _looks_like_internal_key(name: str) -> bool:
    """Reject snake_case catalog keys used as display names (sim degradation)."""
    n = (name or "").strip()
    if not n:
        return True
    if " " in n or "—" in n or any(ord(c) > 127 for c in n):
        return False
    if "_" in n and n.replace("_", "").isalnum():
        return True
    if n.isalnum() and n.islower() and len(n) <= 32:
        return True
    return False


def _name_usable(name: str) -> bool:
    n = _norm(name)
    if not n:
        return False
    if text_has_forbidden_product_placeholder(n):
        return False
    if _looks_like_internal_key(n):
        return False
    return True


def _payload_scope(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    else:
        return {}
    if not isinstance(data, dict):
        return {}
    inner = data.get("data")
    if isinstance(inner, dict):
        return inner
    return data


def _lines_from_payload_scope(scope: Mapping[str, Any]) -> list[dict[str, Any]]:
    for key in ("lines", "cart", "items", "products", "line_items"):
        raw = scope.get(key)
        if isinstance(raw, list) and raw:
            return [x for x in raw if isinstance(x, dict)]
        if key == "cart" and isinstance(raw, dict):
            for nested in ("products", "items"):
                arr = raw.get(nested)
                if isinstance(arr, list) and arr:
                    return [x for x in arr if isinstance(x, dict)]
    return []


def _line_display_name(line: Mapping[str, Any]) -> str:
    nested = line.get("product")
    nested_name = nested.get("name") if isinstance(nested, dict) else None
    return _norm(
        line.get("name") or line.get("title") or line.get("product_name") or nested_name
    )


def resolve_product_identity_for_cart_v1(
    *,
    store_slug: str,
    cart_id: str = "",
    session_id: str = "",
    raw_payload: Any = None,
    db_session: Any = None,
) -> dict[str, Any]:
    """
    Resolve product identity for one cart.

    Preference: cart_line_snapshots → payload lines → unresolved.
    """
    slug = _norm(store_slug, max_len=255)
    cid = _norm(cart_id, max_len=255)
    sid = _norm(session_id, max_len=512)
    names: list[str] = []
    product_ids: list[str] = []
    source = "none"

    if slug and (cid or sid) and db_session is not None:
        try:
            from models import CartLineSnapshot  # noqa: PLC0415

            q = db_session.query(CartLineSnapshot).filter(
                CartLineSnapshot.store_slug == slug
            )
            if cid:
                q = q.filter(CartLineSnapshot.cart_id == cid)
            elif sid:
                q = q.filter(CartLineSnapshot.session_id == sid)
            rows = (
                q.order_by(CartLineSnapshot.captured_at.desc(), CartLineSnapshot.id.desc())
                .limit(20)
                .all()
            )
            for row in rows:
                nm = _norm(getattr(row, "name", None))
                pid = _norm(getattr(row, "product_id", None), max_len=128)
                if pid and pid not in product_ids:
                    product_ids.append(pid)
                if _name_usable(nm) and nm not in names:
                    names.append(nm)
            if names:
                source = "cart_line_snapshots"
        except (SQLAlchemyError, Exception):  # noqa: BLE001
            try:
                db_session.rollback()
            except Exception:  # noqa: BLE001
                pass

    if not names:
        scope = _payload_scope(raw_payload)
        for line in _lines_from_payload_scope(scope):
            nm = _line_display_name(line)
            nested = line.get("product")
            nested_id = nested.get("id") if isinstance(nested, dict) else None
            pid = _norm(
                line.get("product_id") or nested_id or line.get("id"),
                max_len=128,
            )
            if pid and pid not in product_ids:
                product_ids.append(pid)
            if _name_usable(nm) and nm not in names:
                names.append(nm)
        if names:
            source = "raw_payload"

    if names:
        primary = names[0]
        return {
            "version": PROJECTION_VERSION,
            "status": STATUS_RESOLVED,
            "product_name": primary,
            "product_names": names[:5],
            "product_id": product_ids[0] if product_ids else None,
            "product_ids": product_ids[:5],
            "identity_source": source,
            "display_name_ar": primary,
            "unresolved": False,
        }

    return {
        "version": PROJECTION_VERSION,
        "status": STATUS_UNRESOLVED,
        "product_name": None,
        "product_names": [],
        "product_id": product_ids[0] if product_ids else None,
        "product_ids": product_ids[:5],
        "identity_source": source if product_ids else "none",
        "display_name_ar": unresolved_product_identity_ar(),
        "unresolved": True,
    }


def attach_product_identity_cart_projection_v1(
    row: MutableMapping[str, Any],
    *,
    abandoned_cart: Any = None,
    db_session: Any = None,
) -> MutableMapping[str, Any]:
    """Attach ``product_identity_v1`` onto a merchant cart row. Never raises."""
    if not isinstance(row, MutableMapping):
        return row
    try:
        from extensions import db as _db  # noqa: PLC0415

        session = db_session if db_session is not None else _db.session
        slug = _norm(
            row.get("store_slug")
            or getattr(abandoned_cart, "store_slug", None)
            or "",
            max_len=255,
        )
        # AbandonedCart may only have store_id — prefer row store_slug
        if not slug and abandoned_cart is not None:
            try:
                from models import Store  # noqa: PLC0415

                sid = getattr(abandoned_cart, "store_id", None)
                if sid is not None:
                    st = session.query(Store).filter(Store.id == int(sid)).first()
                    if st is not None:
                        slug = _norm(getattr(st, "zid_store_id", None), max_len=255)
            except Exception:  # noqa: BLE001
                pass

        cart_id = _norm(
            row.get("zid_cart_id")
            or row.get("cart_id")
            or getattr(abandoned_cart, "zid_cart_id", None),
            max_len=255,
        )
        session_id = _norm(
            row.get("session_id")
            or row.get("recovery_session_id")
            or getattr(abandoned_cart, "recovery_session_id", None),
            max_len=512,
        )
        raw = None
        if abandoned_cart is not None:
            raw = getattr(abandoned_cart, "raw_payload", None)
        if raw is None:
            raw = row.get("raw_payload")

        identity = resolve_product_identity_for_cart_v1(
            store_slug=slug,
            cart_id=cart_id,
            session_id=session_id,
            raw_payload=raw,
            db_session=session,
        )
        row["product_identity_v1"] = identity
        # Flat fields for slim allowlist / table render
        row["merchant_product_name"] = identity.get("display_name_ar")
        row["merchant_product_identity_status"] = identity.get("status")
        row["merchant_product_identity_unresolved"] = bool(identity.get("unresolved"))
    except Exception as exc:  # noqa: BLE001
        log.debug("product identity cart projection skipped: %s", exc)
        row["product_identity_v1"] = {
            "version": PROJECTION_VERSION,
            "status": STATUS_UNRESOLVED,
            "product_name": None,
            "product_names": [],
            "product_id": None,
            "product_ids": [],
            "identity_source": "error",
            "display_name_ar": unresolved_product_identity_ar(),
            "unresolved": True,
        }
        row["merchant_product_name"] = unresolved_product_identity_ar()
        row["merchant_product_identity_status"] = STATUS_UNRESOLVED
        row["merchant_product_identity_unresolved"] = True
    return row


__all__ = [
    "PROJECTION_VERSION",
    "STATUS_RESOLVED",
    "STATUS_UNRESOLVED",
    "attach_product_identity_cart_projection_v1",
    "resolve_product_identity_for_cart_v1",
]
