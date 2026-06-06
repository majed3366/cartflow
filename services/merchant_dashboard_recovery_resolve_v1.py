# -*- coding: utf-8 -*-
"""
Dashboard recovery row resolution — recovery_key first, then cart_id / session_id.

Read-only helpers for merchant messages/carts APIs and debug trace.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import or_

from extensions import db
from models import AbandonedCart, CartRecoveryLog

log = logging.getLogger("cartflow")

SENT_LOG_STATUSES = frozenset({"sent_real", "mock_sent"})


def _norm(s: Any) -> str:
    return str(s or "").strip()


def store_slug_from_dash(dash_store: Any) -> str:
    return _norm(getattr(dash_store, "zid_store_id", None))[:255]


def canonical_recovery_keys_for_abandoned_cart(
    ac: AbandonedCart,
    *,
    store_slug: str = "",
    recovery_key: str = "",
) -> list[str]:
    """All recovery_key aliases for one AbandonedCart row (parts vs log drift safe)."""
    slug = _norm(store_slug)
    if not slug:
        sid_raw = getattr(ac, "store_id", None)
        if sid_raw is not None:
            try:
                from models import Store

                st_row = db.session.get(Store, int(sid_raw))
                if st_row is not None:
                    slug = _norm(getattr(st_row, "zid_store_id", None))
            except Exception:  # noqa: BLE001
                db.session.rollback()
    return canonical_recovery_keys_for_cart(
        store_slug=slug,
        session_id=_norm(getattr(ac, "recovery_session_id", None)),
        cart_id=_norm(getattr(ac, "zid_cart_id", None)),
        recovery_key=recovery_key,
    )


def canonical_recovery_keys_for_cart(
    *,
    store_slug: str,
    session_id: str = "",
    cart_id: str = "",
    recovery_key: str = "",
) -> list[str]:
    """All recovery_key variants to try for one cart/log (deduped, order preserved)."""
    from services.recovery_message_context_v1 import recovery_key_from_parts  # noqa: PLC0415

    out: list[str] = []
    seen: set[str] = set()

    def _add(rk: str) -> None:
        k = _norm(rk)
        if not k or k in seen:
            return
        seen.add(k)
        out.append(k)

    _add(recovery_key)
    slug = _norm(store_slug)
    sid = _norm(session_id)
    cid = _norm(cart_id)
    if slug:
        if sid:
            _add(recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=""))
            if cid:
                _add(recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=cid))
        if cid:
            _add(recovery_key_from_parts(store_slug=slug, session_id="", cart_id=cid))
    return out


def sent_logs_for_store(
    store_slug: str,
    *,
    limit: int = 200,
    ensure_recovery_keys: Optional[list[str]] = None,
    ensure_log_ids: Optional[list[int]] = None,
) -> list[CartRecoveryLog]:
    """Recent sent logs for store; union explicit recovery_key / log_id targets."""
    slug = _norm(store_slug)
    if not slug:
        return []
    lim = max(1, min(int(limit), 500))
    by_id: dict[int, CartRecoveryLog] = {}
    try:
        rows = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.store_slug == slug,
                CartRecoveryLog.status.in_(tuple(SENT_LOG_STATUSES)),
            )
            .order_by(
                CartRecoveryLog.sent_at.desc().nullslast(),
                CartRecoveryLog.id.desc(),
            )
            .limit(lim)
            .all()
        )
        for lg in rows:
            lid = int(getattr(lg, "id", 0) or 0)
            if lid:
                by_id[lid] = lg
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return []

    extra_keys = [_norm(k) for k in (ensure_recovery_keys or []) if _norm(k)]
    extra_ids = [int(x) for x in (ensure_log_ids or []) if int(x) > 0]
    if extra_keys or extra_ids:
        try:
            clauses: list[Any] = []
            if extra_keys:
                clauses.append(CartRecoveryLog.recovery_key.in_(extra_keys))
            if extra_ids:
                clauses.append(CartRecoveryLog.id.in_(extra_ids))
            extra_rows = (
                db.session.query(CartRecoveryLog)
                .filter(
                    CartRecoveryLog.store_slug == slug,
                    or_(*clauses),
                )
                .all()
            )
            for lg in extra_rows:
                lid = int(getattr(lg, "id", 0) or 0)
                if lid:
                    by_id[lid] = lg
        except Exception:  # noqa: BLE001
            db.session.rollback()

    merged = list(by_id.values())
    merged.sort(
        key=lambda r: (
            getattr(r, "sent_at", None) or getattr(r, "created_at", None),
            int(getattr(r, "id", 0) or 0),
        ),
        reverse=True,
    )
    return merged


def find_sent_log_by_recovery_identity(
    *,
    store_slug: str,
    recovery_key: str = "",
    cart_id: str = "",
    session_id: str = "",
    log_id: Optional[int] = None,
) -> Optional[CartRecoveryLog]:
    """Resolve one sent log: log_id → recovery_key → cart_id → session_id."""
    slug = _norm(store_slug)
    if log_id and int(log_id) > 0:
        try:
            lg = (
                db.session.query(CartRecoveryLog)
                .filter(
                    CartRecoveryLog.id == int(log_id),
                    CartRecoveryLog.store_slug == slug,
                )
                .first()
            )
            if lg is not None:
                return lg
        except Exception:  # noqa: BLE001
            db.session.rollback()

    keys = canonical_recovery_keys_for_cart(
        store_slug=slug,
        session_id=session_id,
        cart_id=cart_id,
        recovery_key=recovery_key,
    )
    if keys:
        try:
            lg = (
                db.session.query(CartRecoveryLog)
                .filter(
                    CartRecoveryLog.store_slug == slug,
                    CartRecoveryLog.recovery_key.in_(keys),
                    CartRecoveryLog.status.in_(tuple(SENT_LOG_STATUSES)),
                )
                .order_by(CartRecoveryLog.id.desc())
                .first()
            )
            if lg is not None:
                return lg
        except Exception:  # noqa: BLE001
            db.session.rollback()

    cid = _norm(cart_id)
    sid = _norm(session_id)
    if cid or sid:
        try:
            parts: list[Any] = []
            if cid:
                parts.append(CartRecoveryLog.cart_id == cid)
            if sid:
                parts.append(CartRecoveryLog.session_id == sid)
            lg = (
                db.session.query(CartRecoveryLog)
                .filter(
                    CartRecoveryLog.store_slug == slug,
                    or_(*parts),
                    CartRecoveryLog.status.in_(tuple(SENT_LOG_STATUSES)),
                )
                .order_by(CartRecoveryLog.id.desc())
                .first()
            )
            if lg is not None:
                return lg
        except Exception:  # noqa: BLE001
            db.session.rollback()
    return None


def find_dashboard_message_row(
    rows: list[dict[str, Any]],
    *,
    recovery_key: str = "",
    cart_id: str = "",
    session_id: str = "",
    log_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Match messages API row: recovery_key first, then cart_id, session_id."""
    rk = _norm(recovery_key)
    cid = _norm(cart_id)
    sid = _norm(session_id)
    lid = int(log_id or 0)

    for r in rows:
        if lid and int(r.get("log_id") or 0) == lid:
            return r
    if rk:
        for r in rows:
            if _norm(r.get("recovery_key")) == rk:
                return r
    if cid:
        for r in rows:
            if _norm(r.get("cart_id")) == cid:
                return r
    if sid:
        for r in rows:
            if _norm(r.get("session_id")) == sid:
                return r
    return None


def find_dashboard_cart_row(
    rows: list[dict[str, Any]],
    *,
    recovery_key: str = "",
    cart_id: str = "",
    session_id: str = "",
) -> Optional[dict[str, Any]]:
    """Match carts API row: recovery_key first, then cart_id, session_id."""
    rk = _norm(recovery_key)
    cid = _norm(cart_id)
    sid = _norm(session_id)
    if rk:
        for r in rows:
            if _norm(r.get("recovery_key")) == rk:
                return r
    if cid:
        for r in rows:
            if _norm(r.get("cart_id")) == cid:
                return r
    if sid:
        for r in rows:
            if _norm(r.get("session_id")) == sid:
                return r
    return None


def cart_row_identity_fields(ac: AbandonedCart, *, store_slug: str) -> dict[str, str]:
    """Canonical identity fields for a cart payload."""
    from services.recovery_message_context_v1 import recovery_key_from_parts  # noqa: PLC0415

    sid = _norm(getattr(ac, "recovery_session_id", None))
    cid = _norm(getattr(ac, "zid_cart_id", None))
    slug = _norm(store_slug)
    rk = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=cid)
    return {
        "recovery_key": rk,
        "session_id": sid,
        "cart_id": cid,
        "store_slug": slug,
    }


def log_matches_cart_identity(
    lg: CartRecoveryLog,
    ac: AbandonedCart,
    *,
    store_slug: str,
) -> bool:
    """True when log belongs to cart (recovery_key first)."""
    from services.recovery_message_context_v1 import (  # noqa: PLC0415
        log_row_matches_abandoned_cart,
        recovery_key_from_parts,
    )

    slug = _norm(store_slug)
    sid = _norm(getattr(ac, "recovery_session_id", None))
    cid = _norm(getattr(ac, "zid_cart_id", None))
    ac_rk = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=cid)
    lrk = _norm(getattr(lg, "recovery_key", None))
    if lrk and ac_rk and lrk == ac_rk:
        return True
    for rk in canonical_recovery_keys_for_cart(
        store_slug=slug,
        session_id=sid,
        cart_id=cid,
        recovery_key=lrk,
    ):
        if lrk and lrk == rk:
            return True
    return log_row_matches_abandoned_cart(lg, ac, recovery_key=ac_rk)


__all__ = [
    "SENT_LOG_STATUSES",
    "canonical_recovery_keys_for_abandoned_cart",
    "canonical_recovery_keys_for_cart",
    "cart_row_identity_fields",
    "find_dashboard_cart_row",
    "find_dashboard_message_row",
    "find_sent_log_by_recovery_identity",
    "log_matches_cart_identity",
    "sent_logs_for_store",
    "store_slug_from_dash",
]
