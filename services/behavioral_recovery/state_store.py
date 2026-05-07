# -*- coding: utf-8 -*-
"""Persist behavioral flags on AbandonedCart.raw_payload under cf_behavioral."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog

BEHAVIOR_KEY = "cf_behavioral"

_NORMAL_SENT = frozenset({"sent_real", "mock_sent"})


def behavioral_dict_for_abandoned_cart(ac: Optional[AbandonedCart]) -> dict[str, Any]:
    if ac is None:
        return {}
    rp = getattr(ac, "raw_payload", None)
    if not isinstance(rp, str) or not rp.strip():
        return {}
    try:
        data = json.loads(rp)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    b = data.get(BEHAVIOR_KEY)
    return dict(b) if isinstance(b, dict) else {}


def _attach_behavioral_to_payload_dict(data: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    cur = data.get(BEHAVIOR_KEY)
    base: dict[str, Any] = dict(cur) if isinstance(cur, dict) else {}
    for k, v in patch.items():
        if v is None:
            base.pop(k, None)
        else:
            base[k] = v
    out = dict(data)
    out[BEHAVIOR_KEY] = base
    return out


def merge_behavioral_state(ac: AbandonedCart, **fields: Any) -> None:
    """Merge keys into cf_behavioral and persist abondoned_cart row."""
    rp = getattr(ac, "raw_payload", None)
    data: dict[str, Any]
    if isinstance(rp, str) and rp.strip():
        try:
            parsed = json.loads(rp)
            data = dict(parsed) if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError, ValueError):
            data = {}
    else:
        data = {}
    merged = _attach_behavioral_to_payload_dict(data, fields)
    AbandonedCart.set_raw(ac, merged)


def abandoned_carts_for_session_or_cart(
    session_id: str,
    cart_id: Optional[str],
) -> list[AbandonedCart]:
    sid = (session_id or "").strip()[:512]
    cid = (str(cart_id).strip()[:255] if cart_id else "") or ""
    out: list[AbandonedCart] = []
    seen: set[int] = set()
    try:
        db.create_all()
        if cid:
            row = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.zid_cart_id == cid)
                .order_by(AbandonedCart.last_seen_at.desc())
                .first()
            )
            if row is not None and row.id not in seen:
                seen.add(int(row.id))
                out.append(row)
        if sid:
            for row in (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.recovery_session_id == sid)
                .order_by(AbandonedCart.last_seen_at.desc())
                .limit(12)
                .all()
            ):
                rid = getattr(row, "id", None)
                if rid is not None and int(rid) not in seen:
                    seen.add(int(rid))
                    out.append(row)
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
    return out


def customer_replied_flagged_for_session(
    session_id: str,
    cart_id: Optional[str],
) -> bool:
    for ac in abandoned_carts_for_session_or_cart(session_id, cart_id):
        b = behavioral_dict_for_abandoned_cart(ac)
        if b.get("customer_replied") is True:
            return True
    return False


def normal_recovery_message_was_sent_for_abandoned(ac: AbandonedCart) -> bool:
    """At least one normal customer recovery WhatsApp logged for this cart/session."""
    conds = []
    sess = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
    zid = (getattr(ac, "zid_cart_id", None) or "").strip()[:255]

    if sess:
        conds.append(CartRecoveryLog.session_id == sess)
    if zid:
        conds.append(CartRecoveryLog.cart_id == zid)
    if not conds:
        return False
    try:
        db.create_all()
        n = (
            db.session.query(CartRecoveryLog.id)
            .filter(
                CartRecoveryLog.status.in_(_NORMAL_SENT),
                CartRecoveryLog.step.isnot(None),
                CartRecoveryLog.step >= 1,
                or_(*conds),
            )
            .limit(1)
            .first()
        )
        return n is not None
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
