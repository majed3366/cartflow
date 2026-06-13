# -*- coding: utf-8 -*-
"""
Durable normal recovery schedule materialization after reason save (v1).

When ``cart_state_sync`` created the ``AbandonedCart`` but ``handle_cart_abandoned``
never ran, in-memory pending arm markers are absent. This module arms scheduling
from persisted ``AbandonedCart`` + ``CartRecoveryReason`` truth instead.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Sequence

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryReason, RecoverySchedule

log = logging.getLogger("cartflow")

ACTIVE_SCHEDULE_STATUSES = frozenset({"scheduled", "running"})
SCHEDULE_BLOCKED_MISSING_PHONE = "schedule_blocked_missing_phone"


def recovery_key_candidates_for_reason_arm(
    store_slug: str,
    session_id: str,
    cart_id: Optional[str] = None,
) -> list[str]:
    from main import _recovery_key_from_store_and_session  # noqa: PLC0415

    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255] if cart_id else ""
    out: list[str] = []
    for cid_opt in (cid or None, None):
        rk = _recovery_key_from_store_and_session(ss, sid, cid_opt)
        if rk and rk not in out:
            out.append(rk)
    return out


def find_abandoned_cart_for_reason_arm(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str] = None,
) -> Optional[AbandonedCart]:
    """Resolve the newest ``AbandonedCart`` for reason-post scheduling."""
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255] if cart_id else ""
    if not sid and not cid:
        return None
    try:
        q = db.session.query(AbandonedCart)
        if cid and sid:
            row = (
                q.filter(
                    or_(
                        AbandonedCart.zid_cart_id == cid,
                        AbandonedCart.recovery_session_id == sid,
                    )
                )
                .order_by(AbandonedCart.id.desc())
                .first()
            )
        elif cid:
            row = (
                q.filter(AbandonedCart.zid_cart_id == cid)
                .order_by(AbandonedCart.id.desc())
                .first()
            )
        else:
            row = (
                q.filter(AbandonedCart.recovery_session_id == sid)
                .order_by(AbandonedCart.id.desc())
                .first()
            )
        return row
    except SQLAlchemyError:
        db.session.rollback()
        return None


def active_recovery_schedule_exists(
    recovery_keys: Sequence[str],
    *,
    session_id: str = "",
    cart_id: str = "",
) -> bool:
    keys = [str(k).strip()[:512] for k in recovery_keys if str(k or "").strip()]
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255]
    try:
        filt = [RecoverySchedule.status.in_(tuple(ACTIVE_SCHEDULE_STATUSES))]
        ors = []
        if keys:
            ors.append(RecoverySchedule.recovery_key.in_(keys))
        if sid:
            ors.append(RecoverySchedule.session_id == sid)
        if cid:
            ors.append(RecoverySchedule.cart_id == cid)
        if not ors:
            return False
        q = db.session.query(RecoverySchedule.id).filter(*filt, or_(*ors))
        return q.limit(1).first() is not None
    except SQLAlchemyError:
        db.session.rollback()
        return False


def reason_tag_saved_for_session(store_slug: str, session_id: str) -> Optional[str]:
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not ss or not sid:
        return None
    try:
        row = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        if row is None:
            return None
        tag = (getattr(row, "reason", None) or "").strip()[:64]
        return tag or None
    except SQLAlchemyError:
        db.session.rollback()
        return None


def build_reason_arm_synth_payload(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    cart_total: Optional[float],
    body: dict[str, Any],
) -> dict[str, Any]:
    synth: dict[str, Any] = {
        "event": "cart_abandoned",
        "store": store_slug,
        "store_slug": store_slug,
        "session_id": session_id,
    }
    cid = (cart_id or "").strip()[:255]
    if cid:
        synth["cart_id"] = cid
    if cart_total is not None:
        synth["cart_total"] = cart_total
    else:
        for k in ("cart_total", "cart_value"):
            if k in body and body.get(k) is not None:
                synth[k] = body[k]
    if isinstance(body.get("cart"), list):
        synth["cart"] = body["cart"]
    for k in ("phone", "customer_phone", "items_count"):
        if k in body and body.get(k) is not None:
            synth[k] = body[k]
    return synth


def try_durable_normal_recovery_materialization_after_reason(
    *,
    store_slug: str,
    session_id: str,
    body: dict[str, Any],
    cart_id_hint: Optional[str],
    rk_candidates: Sequence[str],
    arm_from_saved_reason_payload: Callable[[dict[str, Any]], None],
    is_user_converted: Callable[[str], bool],
    is_vip_cart_fn: Callable[[float, Any], bool],
    load_store_row: Callable[[str], Any],
    persist_cart_recovery_log: Callable[..., None],
    default_recovery_message: Callable[[], str],
) -> str:
    """
    Arm normal recovery when pending in-memory markers are absent.

    Returns action label: ``armed``, ``skipped_existing``, ``skipped_vip``,
    ``skipped_no_cart``, ``skipped_no_reason``, ``skipped_converted``, ``noop``.
    """
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not ss or not sid:
        return "noop"

    reason_tag = reason_tag_saved_for_session(ss, sid)
    if not reason_tag:
        return "skipped_no_reason"

    ac = find_abandoned_cart_for_reason_arm(
        store_slug=ss,
        session_id=sid,
        cart_id=cart_id_hint,
    )
    if ac is None:
        log.info(
            "[NORMAL RECOVERY DURABLE ARM SKIP] reason=no_abandoned_cart "
            "store_slug=%s session_id=%s",
            ss[:96],
            sid[:96],
        )
        return "skipped_no_cart"

    cid = (cart_id_hint or getattr(ac, "zid_cart_id", None) or "").strip()[:255]
    rk_list = list(rk_candidates) or recovery_key_candidates_for_reason_arm(ss, sid, cid)
    rk = rk_list[0] if rk_list else ""

    if is_user_converted(rk):
        return "skipped_converted"

    if active_recovery_schedule_exists(rk_list, session_id=sid, cart_id=cid):
        log.info(
            "[NORMAL RECOVERY DURABLE ARM SKIP] reason=schedule_already_exists "
            "recovery_key=%s session_id=%s cart_id=%s",
            rk[:120],
            sid[:96],
            cid[:80],
        )
        return "skipped_existing"

    store_row = load_store_row(ss)
    cart_total_raw = getattr(ac, "cart_value", None)
    cart_total: Optional[float] = None
    if cart_total_raw is not None:
        try:
            cart_total = float(cart_total_raw)
        except (TypeError, ValueError):
            cart_total = None

    if cart_total is not None and is_vip_cart_fn(cart_total, store_row):
        log.info(
            "[NORMAL RECOVERY DURABLE ARM SKIP] reason=vip_lane "
            "recovery_key=%s cart_total=%s",
            rk[:120],
            str(cart_total),
        )
        return "skipped_vip"

    synth_pl = build_reason_arm_synth_payload(
        store_slug=ss,
        session_id=sid,
        cart_id=cid or None,
        cart_total=cart_total,
        body=body,
    )

    arm_msg = (
        "[NORMAL RECOVERY DURABLE ARM FROM REASON] "
        f"recovery_key={rk[:120]} cart_id={(cid or '-')[:80]} "
        f"cart_total={'none' if cart_total is None else str(cart_total)} "
        f"reason={reason_tag[:64]}"
    )
    log.info(arm_msg)
    print(arm_msg, flush=True)

    arm_from_saved_reason_payload(synth_pl)
    return "armed"


__all__ = [
    "ACTIVE_SCHEDULE_STATUSES",
    "SCHEDULE_BLOCKED_MISSING_PHONE",
    "active_recovery_schedule_exists",
    "build_reason_arm_synth_payload",
    "find_abandoned_cart_for_reason_arm",
    "reason_tag_saved_for_session",
    "recovery_key_candidates_for_reason_arm",
    "try_durable_normal_recovery_materialization_after_reason",
]
