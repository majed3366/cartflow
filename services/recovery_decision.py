# -*- coding: utf-8 -*-
"""
ربط لوحة التحليلات (CartRecoveryReason) بمنطق استرجاع الرسائل — مرحلة أولى.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func

from extensions import db
from models import CartRecoveryReason, Store
from services.cartflow_whatsapp_mock import REASON_CHOICES


def get_primary_recovery_reason(store_slug: str) -> Optional[str]:
    """
    يعيد أكثر سبب (reason) تكراراً في ‎cart_recovery_reasons‎ لهذا ‎store_slug‎.
    عند التعادل: تفضيل أبجدي لثبات النتيجة.
    """
    ss = (store_slug or "").strip()[:255]
    if not ss:
        return None
    db.create_all()
    rows = (
        db.session.query(
            CartRecoveryReason.reason,
            func.count(CartRecoveryReason.id).label("c"),
        )
        .filter(CartRecoveryReason.store_slug == ss)
        .group_by(CartRecoveryReason.reason)
        .all()
    )
    if not rows:
        return None

    def _sort_key(r: tuple) -> tuple:
        reason = (r[0] or "").strip().lower()
        cnt = int(r[1] or 0)
        return (-cnt, reason)

    rows_sorted = sorted(rows, key=_sort_key)
    top = rows_sorted[0]
    rk = (top[0] or "").strip().lower()
    if rk not in REASON_CHOICES:
        return None
    return rk


def get_primary_recovery_reason_by_store_id(store_id: int) -> Optional[str]:
    """
    نفس ‎get_primary_recovery_reason‎ باستخدام ‎Store.id‎: يُطابق ‎zid_store_id‎ (أو افتراضي) كـ ‎store_slug‎.
    """
    db.create_all()
    row = db.session.query(Store).filter(Store.id == store_id).first()
    if row is None:
        return None
    zid = getattr(row, "zid_store_id", None)
    slug = (str(zid).strip()[:255] if zid is not None and str(zid).strip() else "") or ""
    if not slug:
        return get_primary_recovery_reason("default")
    return get_primary_recovery_reason(slug)


def resolve_auto_whatsapp_reason(
    store_slug: str,
) -> tuple[str, Optional[str], str, bool]:
    """
    عند طلب ‎reason=auto‎: يحدد (reason, sub_category) للرسالة.

    يعيد:
    - reason, sub_category المُمرَّرة لـ ‎build_mock_whatsapp_message‎
    - ‎primary_log‎: سلسلة للسجلات/الواجهة (أو ‎default_price_discount‎)
    - ‎used_analytics‎: ‎True‎ إذا وُجدت بيانات في ‎CartRecoveryReason‎
    """
    primary = get_primary_recovery_reason(store_slug)
    if primary is None:
        return ("price", "price_discount_request", "default_price_discount", False)
    if primary == "price":
        # تركيز الاسترجاع على خصم عندما يكون السعر هو الأغلب (لوحة القرار)
        return ("price", "price_discount_request", primary, True)
    return (primary, None, primary, True)
