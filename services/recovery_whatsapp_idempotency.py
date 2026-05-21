# -*- coding: utf-8 -*-
"""DB-backed WhatsApp recovery send idempotency — survives retry, restart, and multi-worker races."""
from __future__ import annotations

import re
from typing import Any, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartRecoveryLog

# Successful or in-flight acceptance — not provider failures.
_IDEMPOTENCY_BLOCK_STATUSES = frozenset(
    {
        "sent_real",
        "mock_sent",
        "queued",
    }
)


def _digits_only(phone: Optional[str]) -> str:
    if not phone:
        return ""
    return re.sub(r"\D", "", str(phone).strip())[:32]


def build_whatsapp_recovery_idempotency_key(
    *,
    recovery_key: str,
    step: int,
    reason_tag: Optional[str] = None,
    customer_phone: Optional[str] = None,
    store_slug: Optional[str] = None,
    session_id: Optional[str] = None,
    cart_id: Optional[str] = None,
) -> dict[str, Any]:
    """Stable identity for logs and DB lookup (no Redis)."""
    rk = (recovery_key or "").strip()[:512]
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255] if cart_id else ""
    if not ss and rk and ":" in rk:
        ss = rk.split(":", 1)[0].strip()[:255]
    if not sid and rk and ":" in rk:
        sid = rk.split(":", 1)[1].strip()[:512]
    rt = (reason_tag or "").strip()[:128] or None
    phone_norm = _digits_only(customer_phone)
    return {
        "recovery_key": rk,
        "store_slug": ss,
        "session_id": sid,
        "cart_id": cid,
        "step": int(step),
        "reason_tag": rt,
        "customer_phone_digits": phone_norm or None,
    }


def _log_idempotency(
    tag: str,
    key: dict[str, Any],
    *,
    existing_status: Optional[str] = None,
) -> None:
    try:
        print(f"[WA IDEMPOTENCY {tag}]", flush=True)
        print(f"recovery_key={(key.get('recovery_key') or '-')[:120]}", flush=True)
        print(f"step={key.get('step')}", flush=True)
        rt = key.get("reason_tag")
        print(f"reason_tag={(rt if rt else '-')[:64]}", flush=True)
        pd = key.get("customer_phone_digits")
        print(f"customer_phone_digits={(pd if pd else '-')[:32]}", flush=True)
        if existing_status:
            print(f"existing_status={existing_status[:50]}", flush=True)
    except OSError:
        pass


def _phone_matches_row(row_phone: Optional[str], phone_digits: str) -> bool:
    if not phone_digits:
        return True
    row_d = _digits_only(row_phone)
    if not row_d:
        return True
    return row_d == phone_digits or row_d.endswith(phone_digits) or phone_digits.endswith(row_d)


def find_existing_whatsapp_recovery_send(
    key: dict[str, Any],
) -> Optional[CartRecoveryLog]:
    """Return latest blocking CartRecoveryLog row if an equivalent send already exists."""
    sid = (key.get("session_id") or "").strip()
    cid = (key.get("cart_id") or "").strip()
    ss = (key.get("store_slug") or "").strip()
    if not sid and not cid:
        return None
    try:
        db.create_all()
        conds: list[Any] = []
        if sid:
            conds.append(CartRecoveryLog.session_id == sid)
        if cid:
            conds.append(CartRecoveryLog.cart_id == cid)
        if not conds:
            return None
        q = db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.step == int(key.get("step") or 1),
            CartRecoveryLog.status.in_(sorted(_IDEMPOTENCY_BLOCK_STATUSES)),
            or_(*conds),
        )
        if ss:
            q = q.filter(CartRecoveryLog.store_slug == ss)
        rows = q.order_by(CartRecoveryLog.id.desc()).limit(20).all()
        phone_digits = key.get("customer_phone_digits") or ""
        for row in rows:
            if _phone_matches_row(getattr(row, "phone", None), phone_digits):
                return row
        return None
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return None


def check_whatsapp_recovery_send_idempotency(
    *,
    recovery_key: str,
    step: int,
    reason_tag: Optional[str] = None,
    customer_phone: Optional[str] = None,
    store_slug: Optional[str] = None,
    session_id: Optional[str] = None,
    cart_id: Optional[str] = None,
) -> Tuple[bool, Optional[str], dict[str, Any]]:
    """
    Returns (is_duplicate, existing_status, idempotency_key).
    Logs [WA IDEMPOTENCY CHECK] and HIT or MISS.
    """
    key = build_whatsapp_recovery_idempotency_key(
        recovery_key=recovery_key,
        step=step,
        reason_tag=reason_tag,
        customer_phone=customer_phone,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )
    _log_idempotency("CHECK", key)
    existing = find_existing_whatsapp_recovery_send(key)
    if existing is not None:
        st = (existing.status or "").strip()
        _log_idempotency("HIT", key, existing_status=st)
        return True, st or "unknown", key
    _log_idempotency("MISS", key)
    return False, None, key


def log_whatsapp_recovery_idempotency_recorded(
    *,
    recovery_key: str,
    step: int,
    reason_tag: Optional[str] = None,
    customer_phone: Optional[str] = None,
    store_slug: Optional[str] = None,
    session_id: Optional[str] = None,
    cart_id: Optional[str] = None,
    log_status: str = "mock_sent",
) -> None:
    """After provider acceptance / mock_sent persist — future retries will HIT."""
    key = build_whatsapp_recovery_idempotency_key(
        recovery_key=recovery_key,
        step=step,
        reason_tag=reason_tag,
        customer_phone=customer_phone,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )
    _log_idempotency("RECORDED", key, existing_status=(log_status or "")[:50])
