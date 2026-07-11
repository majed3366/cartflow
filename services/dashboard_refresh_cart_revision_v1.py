# -*- coding: utf-8 -*-
"""
Live AbandonedCart revision for dashboard refresh-state.

New cart persistence must bump ``merchant_dashboard_refresh_token`` so open
dashboard tabs (desktop + mobile) refetch without relying on
``sessionStorage.cartflow_cart_event_id`` (device-local only).

Bounded: one indexed MAX(id) query scoped to the merchant store.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart

log = logging.getLogger("cartflow")

_CART_REV_SUFFIX_RE = re.compile(r":c\d+$")


def live_abandoned_cart_max_id(
    *,
    store_slug: str = "",
    dash_store: Any = None,
) -> int:
    """Return max AbandonedCart.id for the merchant dashboard store scope, or 0."""
    store = dash_store
    slug = (store_slug or "").strip()
    if store is None and slug:
        try:
            from models import Store  # noqa: PLC0415

            store = (
                db.session.query(Store)
                .filter(Store.zid_store_id == slug)
                .order_by(Store.id.desc())
                .first()
            )
        except (SQLAlchemyError, OSError, TypeError, ValueError):
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass
            store = None
    if store is None:
        return 0
    try:
        from main import _normal_recovery_abandoned_scope_filter  # noqa: PLC0415

        scope = _normal_recovery_abandoned_scope_filter(store)
        if scope is None:
            return 0
        q = db.session.query(func.coalesce(func.max(AbandonedCart.id), 0)).filter(scope)
        return int(q.scalar() or 0)
    except (SQLAlchemyError, OSError, TypeError, ValueError) as exc:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.warning("live_abandoned_cart_max_id failed: %s", exc)
        return 0


def append_cart_revision_to_refresh_token(token: str, cart_max_id: int) -> str:
    """Replace or append ``:c{id}`` cart revision suffix on a refresh token."""
    base = _CART_REV_SUFFIX_RE.sub("", str(token or "").strip())
    rev = max(0, int(cart_max_id or 0))
    if not base:
        return f"c{rev}"
    return f"{base}:c{rev}"


def apply_live_cart_revision_to_refresh_state(
    payload: dict[str, Any],
    *,
    store_slug: str = "",
    dash_store: Any = None,
) -> dict[str, Any]:
    """
    Overlay live AbandonedCart max id onto refresh-state payload token.

    Snapshot refresh-state alone cannot see new carts until the builder runs,
    and the token historically ignored AbandonedCart inserts entirely.
    """
    if not isinstance(payload, dict):
        return payload
    rev = live_abandoned_cart_max_id(store_slug=store_slug, dash_store=dash_store)
    tok = str(payload.get("merchant_dashboard_refresh_token") or "")
    payload["merchant_dashboard_refresh_token"] = append_cart_revision_to_refresh_token(
        tok, rev
    )
    payload["merchant_dashboard_refresh_cart_rev"] = rev
    return payload


__all__ = [
    "append_cart_revision_to_refresh_token",
    "apply_live_cart_revision_to_refresh_state",
    "live_abandoned_cart_max_id",
]
