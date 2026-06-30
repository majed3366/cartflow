# -*- coding: utf-8 -*-
"""
Cart action identity V1 — safe mutation keys for archive/reopen.

Session-only recovery keys (store_slug:session_id) may alias multiple carts in one
browser session. They are valid for read/diagnostic resolution but must never
drive write actions that affect more than one cart.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, Store


def _norm(value: Any) -> str:
    return (str(value or "")).strip()[:512]


def session_only_recovery_key(*, store_slug: str, session_id: str) -> str:
    """Canonical session-only key — not valid for cart mutation actions."""
    from services.recovery_message_context_v1 import recovery_key_from_parts  # noqa: PLC0415

    slug = _norm(store_slug)[:255]
    sid = _norm(session_id)
    if not slug or not sid:
        return ""
    return recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id="")


def is_session_only_recovery_key(
    recovery_key: str,
    *,
    store_slug: str = "",
    session_id: str = "",
) -> bool:
    """True when key is exactly store_slug:session_id with no cart segment."""
    rk = _norm(recovery_key)
    if not rk:
        return False
    slug = _norm(store_slug)[:255]
    sid = _norm(session_id)
    if not slug or not sid:
        return False
    return rk == session_only_recovery_key(store_slug=slug, session_id=sid)


def filter_mutation_recovery_keys(
    keys: Sequence[str],
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> list[str]:
    """Drop session-only aliases; keep cart-specific / log recovery keys."""
    slug = _norm(store_slug)[:255]
    sid = _norm(session_id)
    cid = _norm(cart_id)[:255]
    session_only = session_only_recovery_key(store_slug=slug, session_id=sid) if slug and sid else ""

    out: list[str] = []
    seen: set[str] = set()
    for raw in keys or ():
        rk = _norm(raw)
        if not rk or rk in seen:
            continue
        if session_only and rk == session_only:
            continue
        if is_session_only_recovery_key(rk, store_slug=slug, session_id=sid):
            continue
        seen.add(rk)
        out.append(rk)

    if not out and cid and slug and sid:
        from services.recovery_message_context_v1 import recovery_key_from_parts  # noqa: PLC0415

        rk_cart = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=cid)
        if rk_cart and rk_cart not in seen:
            out.append(rk_cart)

    return out


def mutation_recovery_keys_for_abandoned_cart(
    ac: AbandonedCart,
    *,
    store_slug: str = "",
    recovery_key: str = "",
) -> list[str]:
    """Cart-specific recovery keys safe for archive/reopen mutations."""
    from services.merchant_dashboard_recovery_resolve_v1 import (  # noqa: PLC0415
        canonical_recovery_keys_for_abandoned_cart,
    )

    slug = _norm(store_slug)[:255]
    sid = _norm(getattr(ac, "recovery_session_id", None))
    cid = _norm(getattr(ac, "zid_cart_id", None))[:255]
    if not slug and getattr(ac, "store_id", None):
        try:
            st_row = db.session.get(Store, int(ac.store_id))
            if st_row is not None:
                slug = _norm(getattr(st_row, "zid_store_id", None))[:255]
        except (SQLAlchemyError, TypeError, ValueError):
            db.session.rollback()

    aliases = canonical_recovery_keys_for_abandoned_cart(
        ac,
        store_slug=slug,
        recovery_key=_norm(recovery_key),
    )
    seed: list[str] = []
    rk_req = _norm(recovery_key)
    if rk_req:
        seed.append(rk_req)
    for k in aliases:
        if k and k not in seed:
            seed.append(k)

    return filter_mutation_recovery_keys(
        seed,
        store_slug=slug,
        session_id=sid,
        cart_id=cid,
    )


def any_merchant_archived_for_mutation_keys(
    merchant_archived_by_rk: Mapping[str, bool],
    alias_keys: Sequence[str],
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> bool:
    """Read path aligned with mutation identity — ignores session-only archive rows."""
    safe = filter_mutation_recovery_keys(
        alias_keys,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )
    return any(bool(merchant_archived_by_rk.get(k)) for k in safe if k)


def resolve_abandoned_cart_for_dashboard_action(
    body: Mapping[str, Any],
    *,
    recovery_key: str = "",
) -> tuple[Optional[AbandonedCart], str, Optional[int]]:
    """Resolve target cart row for dashboard archive/reopen (store-scoped when possible)."""
    rk = _norm(recovery_key or body.get("recovery_key"))
    store_slug = _norm(body.get("store_slug"))[:255]
    if not store_slug and rk and ":" in rk:
        store_slug = rk.split(":", 1)[0].strip()[:255]

    ac_id_raw = body.get("abandoned_cart_id")
    try:
        ac_id_i = int(ac_id_raw) if ac_id_raw is not None else None
    except (TypeError, ValueError):
        ac_id_i = None

    body_session = _norm(body.get("session_id"))
    body_cart_id = _norm(body.get("cart_id"))[:255]

    store_id: Optional[int] = None
    if store_slug:
        try:
            st_row = (
                db.session.query(Store.id)
                .filter(Store.zid_store_id == store_slug)
                .first()
            )
            if st_row is not None:
                store_id = int(st_row[0])
        except (SQLAlchemyError, TypeError, ValueError):
            db.session.rollback()

    ac_row: Optional[AbandonedCart] = None
    if ac_id_i is not None:
        try:
            ac_row = db.session.get(AbandonedCart, ac_id_i)
            if ac_row is not None and store_id is not None:
                if int(getattr(ac_row, "store_id", 0) or 0) != store_id:
                    ac_row = None
        except (SQLAlchemyError, OSError, TypeError, ValueError):
            db.session.rollback()
            ac_row = None

    if ac_row is None and body_session:
        try:
            q = db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id == body_session
            )
            if store_id is not None:
                q = q.filter(AbandonedCart.store_id == store_id)
            if body_cart_id:
                q = q.filter(AbandonedCart.zid_cart_id == body_cart_id)
            ac_row = q.order_by(AbandonedCart.id.desc()).first()
        except (SQLAlchemyError, OSError):
            db.session.rollback()
            ac_row = None

    if ac_row is None and body_cart_id and store_id is not None:
        try:
            ac_row = (
                db.session.query(AbandonedCart)
                .filter(
                    AbandonedCart.store_id == store_id,
                    AbandonedCart.zid_cart_id == body_cart_id,
                )
                .order_by(AbandonedCart.id.desc())
                .first()
            )
        except (SQLAlchemyError, OSError):
            db.session.rollback()
            ac_row = None

    if ac_row is not None and ac_id_i is None:
        try:
            ac_id_i = int(getattr(ac_row, "id", 0) or 0) or None
        except (TypeError, ValueError):
            ac_id_i = None

    return ac_row, store_slug, ac_id_i


def mutation_recovery_keys_for_dashboard_body(body: Mapping[str, Any]) -> list[str]:
    """Safe mutation keys from dashboard archive/reopen POST body."""
    rk = _norm(body.get("recovery_key"))
    if not rk:
        return []
    ac_row, store_slug, _ac_id = resolve_abandoned_cart_for_dashboard_action(
        body, recovery_key=rk
    )
    if ac_row is not None:
        return mutation_recovery_keys_for_abandoned_cart(
            ac_row,
            store_slug=store_slug,
            recovery_key=rk,
        )
    return filter_mutation_recovery_keys(
        [rk],
        store_slug=store_slug,
        session_id=_norm(body.get("session_id")),
        cart_id=_norm(body.get("cart_id"))[:255],
    )


__all__ = [
    "any_merchant_archived_for_mutation_keys",
    "filter_mutation_recovery_keys",
    "is_session_only_recovery_key",
    "mutation_recovery_keys_for_abandoned_cart",
    "mutation_recovery_keys_for_dashboard_body",
    "resolve_abandoned_cart_for_dashboard_action",
    "session_only_recovery_key",
]
