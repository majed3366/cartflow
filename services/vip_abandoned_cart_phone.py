# -*- coding: utf-8 -*-
"""ربط رقم ‎vip_phone_capture‎ (جلسة الودجت) بصف ‎AbandonedCart‎ في لوحة VIP."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, Store
from services.vip_cart import abandoned_cart_in_vip_operational_lane, merchant_vip_threshold_int


def resolve_store_row_for_cartflow_slug_session(
    session: Any, store_slug: str
) -> Optional[Store]:
    """قراءة ‎Store‎ حسب ‎store_slug‎ — canonical identity layer only."""
    from services.store_identity_v1 import resolve_store_row_by_identifier

    ss = (store_slug or "").strip()[:255]
    if not ss:
        return None
    try:
        row, _via = resolve_store_row_by_identifier(ss, session=session)
        return row
    except (SQLAlchemyError, OSError):
        session.rollback()
        return None


def resolve_store_row_for_cartflow_slug(store_slug: str) -> Optional[Store]:
    ss = (store_slug or "").strip()[:255]
    if not ss:
        return None
    try:
        db.create_all()
        return resolve_store_row_for_cartflow_slug_session(db.session, ss)
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None


def hydrate_abandoned_cart_customer_phone_from_recovery(
    ac: AbandonedCart,
    *,
    store_slug: str = "",
) -> bool:
    """
    Backfill ‎AbandonedCart.customer_phone‎ from ‎CartRecoveryReason‎ / session memory
    when the column is empty — closes phone-before-cart and store_slug drift gaps.
    """
    if ac is None:
        return False
    existing = (getattr(ac, "customer_phone", None) or "").strip()
    if existing:
        return False
    store_row = resolve_store_row_for_cartflow_slug(store_slug) if store_slug else None
    if store_row is None:
        sid_raw = getattr(ac, "store_id", None)
        if sid_raw is not None:
            try:
                store_row = db.session.get(Store, int(sid_raw))
            except (SQLAlchemyError, TypeError, ValueError):
                db.session.rollback()
                store_row = None
    try:
        from main import _vip_dashboard_customer_phone_raw  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return False
    resolved = (_vip_dashboard_customer_phone_raw(ac, store_row) or "").strip()
    if not resolved:
        return False
    ac.customer_phone = resolved[:100]
    return True


def apply_vip_phone_capture_to_abandoned_carts(
    *,
    store_slug: str,
    recovery_session_id: str,
    normalized_phone: str,
) -> int:
    """
    يحدّث ‎customer_phone‎ لسلات ‎VIP‎ المهجورة ذات ‎recovery_session_id‎ المطابقة.
    يُستدعى قبل ‎commit‎ في نفس المعاملة.
    """
    ss = (store_slug or "").strip()[:255]
    sid = (recovery_session_id or "").strip()[:512]
    phone = (normalized_phone or "").strip()[:100]
    if not sid or not phone:
        return 0
    n = 0
    store_row = resolve_store_row_for_cartflow_slug(ss)
    q = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.recovery_session_id == sid)
        .filter(AbandonedCart.status == "abandoned")
    )
    if store_row is not None:
        vid = int(store_row.id)
        q = q.filter(
            (AbandonedCart.store_id == vid) | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
        )
    for ac in q.all():
        vip_flag = bool(getattr(ac, "vip_mode", False))
        in_lane = abandoned_cart_in_vip_operational_lane(ac, store_row)
        if not vip_flag and not in_lane:
            continue
        ac.customer_phone = phone
        if in_lane and not vip_flag:
            ac.vip_mode = True
        n += 1
    return n


def vip_cart_value_for_recovery_session(store_slug: str, session_id: str) -> float:
    """قيمة أحدث سلة ‎VIP‎ لهذه الجلسة (أي ‎status‎) لعرضها في تنبيه التاجر."""
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not sid:
        return 0.0
    try:
        db.create_all()
        store_row = resolve_store_row_for_cartflow_slug(ss)
        q = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid)
            .filter(AbandonedCart.vip_mode.is_(True))
        )
        if store_row is not None:
            vid = int(store_row.id)
            q = q.filter(
                (AbandonedCart.store_id == vid) | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
            )
        ac = q.order_by(AbandonedCart.last_seen_at.desc()).first()
        if ac is None:
            return 0.0
        return float(ac.cart_value or 0.0)
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return 0.0
