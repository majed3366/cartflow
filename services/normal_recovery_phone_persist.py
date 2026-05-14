# -*- coding: utf-8 -*-
"""
تخزين دائم لرقم العميل في دورة الاسترجاع العادي (‎CartRecoveryReason‎ + ‎AbandonedCart‎ غير VIP).
لا يغيّر مسار الإرسال ولا منطق VIP في الواجهات الأخرى.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import or_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import AbandonedCart, CartRecoveryReason
from services.recovery_session_phone import record_recovery_customer_phone
from services.recovery_session_phone import recovery_key_for_reason_session

log = logging.getLogger("cartflow")


def _strip_persist_phone(raw: Optional[str]) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    return s[:100] if s else ""


def log_normal_recovery_phone_line(
    *,
    session_id: str,
    cart_id: Optional[str],
    reason_tag: Optional[str],
    phone: Optional[str],
) -> None:
    sid = (session_id or "").strip()[:512] or "-"
    cid = ((cart_id or "").strip()[:255] or "-") if cart_id else "-"
    rt = (reason_tag or "").strip()[:64] or "-"
    ph = _strip_persist_phone(phone)
    try:
        if ph:
            line = (
                f"[NORMAL RECOVERY PHONE] session_id={sid} cart_id={cid} "
                f"reason_tag={rt} customer_phone={ph}"
            )
        else:
            line = (
                f"[NORMAL RECOVERY NO PHONE] session_id={sid} cart_id={cid} "
                f"reason_tag={rt}"
            )
        log.info(line)
        print(line, flush=True)
    except OSError:
        pass


def apply_normal_recovery_phone_to_session(
    db_session: Session,
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    phone: Optional[str],
    reason_tag: Optional[str] = None,
    phone_record_source: Optional[str] = None,
) -> bool:
    """
    يحدّث ORM في الجلسة الحالية فقط (بدون ‎commit‎).
    يُستدعى قبل ‎commit‎ الأب.
    """
    ph = _strip_persist_phone(phone)
    if not ph:
        return False
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not ss or not sid:
        return False
    cid = (cart_id or "").strip()[:255] or None
    try:
        db_session.execute(
            update(CartRecoveryReason)
            .where(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.session_id == sid,
            )
            .values(customer_phone=ph[:100])
        )
        conds = []
        if sid:
            conds.append(AbandonedCart.recovery_session_id == sid)
        if cid:
            conds.append(AbandonedCart.zid_cart_id == cid)
        if conds:
            db_session.execute(
                update(AbandonedCart)
                .where(
                    AbandonedCart.vip_mode.is_(False),
                    or_(*conds),
                )
                .values(customer_phone=ph[:100])
            )
    except (SQLAlchemyError, OSError, TypeError, ValueError) as exc:
        log.warning("normal_recovery_phone_persist apply failed: %s", exc, exc_info=True)
        return False
    rk = recovery_key_for_reason_session(ss, sid)
    record_recovery_customer_phone(rk, ph, source=phone_record_source)
    return True


def commit_normal_recovery_phone_after_resolved(
    *,
    store_slug: str,
    session_id: str,
    cart_id: Optional[str],
    phone: Optional[str],
    reason_tag: Optional[str] = None,
) -> bool:
    """بعد حل الرقم في مسار التأخير: ‎persist + commit‎ منفصل."""
    from extensions import db

    ph = _strip_persist_phone(phone)
    if not ph:
        return False
    try:
        from main import _ensure_cartflow_api_db_warmed

        _ensure_cartflow_api_db_warmed()
        ok = apply_normal_recovery_phone_to_session(
            db.session,
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone=ph,
            reason_tag=reason_tag,
        )
        if ok:
            db.session.commit()
        return ok
    except SQLAlchemyError:
        db.session.rollback()
        return False
