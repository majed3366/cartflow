# -*- coding: utf-8 -*-
"""تصنيف «خامل» لعرض التاجر — قراءة فقط؛ بدون حذف أو إخفاء عشوائي."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog

from services.normal_recovery_merchant_view_config import (
    normal_recovery_merchant_stale_config,
)


def _cart_recovery_log_conds_for_abandoned(ac: AbandonedCart) -> list[Any]:
    """نفس منطق ‎main._cart_recovery_log_filters_for_abandoned_cart‎ (بدون استيراد دائري)."""
    sess = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
    zid = (getattr(ac, "zid_cart_id", None) or "").strip()[:255]
    conds: list[Any] = []
    if sess:
        conds.append(CartRecoveryLog.session_id == sess)
    if zid:
        conds.append(CartRecoveryLog.cart_id == zid)
        conds.append(CartRecoveryLog.session_id == zid)
    return conds


def _group_activity_utc(
    grp_sorted: list[AbandonedCart],
    activity_map: dict[int, datetime],
) -> datetime:
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    ts = [
        activity_map.get(int(getattr(ac, "id", 0) or 0), epoch)
        for ac in grp_sorted
        if ac is not None
    ]
    return max(ts) if ts else epoch


def _has_recent_queued_followup(
    grp_sorted: list[AbandonedCart],
    *,
    store_slug: str,
    since_utc: datetime,
) -> bool:
    ss = (store_slug or "").strip()[:255]
    if not ss or not grp_sorted:
        return False
    ac0 = grp_sorted[0]
    conds = _cart_recovery_log_conds_for_abandoned(ac0)
    if not conds:
        return False
    try:
        db.create_all()
        row = (
            db.session.query(CartRecoveryLog.id)
            .filter(
                CartRecoveryLog.store_slug == ss,
                CartRecoveryLog.status == "queued",
                CartRecoveryLog.created_at >= since_utc,
                or_(*conds),
            )
            .first()
        )
        return row is not None
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return False


def merchant_group_stale_meta(
    grp_sorted: list[AbandonedCart],
    *,
    store_slug: str,
    activity_map: dict[int, datetime],
    coarse: str,
    now_utc: Optional[datetime] = None,
) -> tuple[bool, dict[str, Any]]:
    """
    خامل تجاري: ‎pending/sent‎ + تجاوز النافذة + لا ‎queued‎ بعد آخر نشاط معنٍ.
    يُمرَّر ‎coarse‎ من محرك اللوحة (نفس ‎_normal_recovery_coarse_status‎).
    """
    meta: dict[str, Any] = {
        "stale": False,
        "stale_reason": "",
        "age_minutes": None,
        "last_activity_at": None,
        "merchant_stale_hint_ar": "",
        "merchant_stale_surface": "",
    }
    cfg = normal_recovery_merchant_stale_config()
    if not cfg.get("stale_archive_enabled"):
        return False, meta
    if not grp_sorted:
        return False, meta

    cr = (coarse or "").strip().lower()
    if cr not in ("pending", "sent"):
        return False, meta

    now = now_utc or datetime.now(timezone.utc)
    last_act = _group_activity_utc(grp_sorted, activity_map)
    if last_act.tzinfo is None:
        last_act = last_act.replace(tzinfo=timezone.utc)
    else:
        last_act = last_act.astimezone(timezone.utc)
    meta["last_activity_at"] = last_act.isoformat()
    age_min = max(0.0, (now - last_act).total_seconds() / 60.0)
    meta["age_minutes"] = round(age_min, 1)

    win = (
        int(cfg["active_pending_window_minutes"])
        if cr == "pending"
        else int(cfg["active_sent_window_minutes"])
    )
    if age_min <= float(win):
        return False, meta

    since = last_act - timedelta(minutes=2)
    if _has_recent_queued_followup(grp_sorted, store_slug=store_slug, since_utc=since):
        meta["stale_reason"] = "queued_followup_present"
        return False, meta

    meta["stale"] = True
    if cr == "pending":
        meta["stale_reason"] = "stale_pending_no_activity"
        meta["merchant_stale_surface"] = "expired_waiting"
        meta["merchant_stale_hint_ar"] = (
            "لم يتفاعل العميل بعد — تم نقلها إلى السجل."
        )
    else:
        meta["stale_reason"] = "stale_sent_no_customer_signal"
        meta["merchant_stale_surface"] = "stale_active"
        meta["merchant_stale_hint_ar"] = (
            "لم يظهر تفاعل بعد آخر رسالة — تم نقلها إلى السجل."
        )
    return True, meta
