# -*- coding: utf-8 -*-
"""ربط رقم ‎vip_phone_capture‎ (جلسة الودجت) بصف ‎AbandonedCart‎ في لوحة VIP."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, Store

# يطابق ‎main._WIDGET_STORE_SLUGS_USE_DASHBOARD_LATEST‎ (بدون استيراد ‎main‎ لتفادي الدورات).
_WIDGET_SLUGS_MAP_TO_LATEST_STORE = frozenset(
    {"demo", "default", "cartflow-default-recovery"}
)


def resolve_store_row_for_cartflow_slug(store_slug: str) -> Optional[Store]:
    ss = (store_slug or "").strip()[:255]
    if not ss:
        return None
    try:
        db.create_all()
        row = db.session.query(Store).filter(Store.zid_store_id == ss).first()
        if row is not None:
            return row
        if ss.casefold() in {x.casefold() for x in _WIDGET_SLUGS_MAP_TO_LATEST_STORE}:
            return db.session.query(Store).order_by(Store.id.desc()).first()
        return None
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None


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
        .filter(AbandonedCart.vip_mode.is_(True))
        .filter(AbandonedCart.status == "abandoned")
    )
    if store_row is not None:
        vid = int(store_row.id)
        q = q.filter(
            (AbandonedCart.store_id == vid) | (AbandonedCart.store_id.is_(None))  # type: ignore[union-attr]
        )
    for ac in q.all():
        ac.customer_phone = phone
        n += 1
    return n
