# -*- coding: utf-8 -*-
"""ردود واتساب الواردة: كشف النية الإيجابية وإنشاء إجراء متابعة للتاجر."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryReason, MerchantFollowupAction, MessageLog, Store

log = logging.getLogger("cartflow")

STATUS_NEEDS_MERCHANT_FOLLOWUP = "needs_merchant_followup"
REASON_CUSTOMER_REPLIED_YES = "customer_replied_yes"

_POSITIVE_EXACT = frozenset(
    {
        "نعم",
        "ايه",
        "ابغى",
        "ابغي",
        "مهتم",
        "اهتمام",
    }
)


def _digits_only(raw: str) -> str:
    return "".join(c for c in (raw or "") if c.isdigit())


def _normalize_reply_text(s: str) -> str:
    t = (s or "").strip().lower()
    for a, b in (
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ى", "ي"),
        ("ة", "ه"),
        ("ٱ", "ا"),
    ):
        t = t.replace(a, b)
    return " ".join(t.split())


def is_positive_recovery_reply(body: Any) -> bool:
    if body is None:
        return False
    s = str(body).strip()
    if not s:
        return False
    n = _normalize_reply_text(s)
    if n in _POSITIVE_EXACT:
        return True
    if "احتاج مساعده" in n or "ابغي اكمل" in n or "ابغى اكمل" in n:
        return True
    return False


def normalize_wa_customer_digits(from_raw: Any) -> str:
    """
    من ‎whatsapp:+9665…‎ أو أرقام عادية إلى مفتاح ‎9665XXXXXXXX‎ عند الإمكان.
    """
    if from_raw is None:
        return ""
    s = str(from_raw).strip()
    if ":" in s:
        s = s.split(":", 1)[-1].strip()
    d = _digits_only(s)
    while d.startswith("00"):
        d = d[2:]
    if len(d) == 10 and d.startswith("05"):
        d = "966" + d[1:]
    elif len(d) == 9 and d.startswith("5"):
        d = "966" + d
    return d[:20]


def _phone_key_matches(ac_phone: Optional[str], target_key: str) -> bool:
    if not ac_phone or not target_key:
        return False
    cand = normalize_wa_customer_digits(ac_phone)
    return bool(cand) and cand == target_key


def find_latest_abandoned_cart_for_customer_phone(
    phone_key: str,
) -> Tuple[Optional[AbandonedCart], Optional[Store]]:
    if len(phone_key) < 11:
        return None, None
    try:
        db.create_all()
        rows = (
            db.session.query(AbandonedCart)
            .order_by(AbandonedCart.last_seen_at.desc())
            .limit(450)
            .all()
        )
        for ac in rows:
            if _phone_key_matches(getattr(ac, "customer_phone", None), phone_key):
                return ac, _store_for_abandoned_cart(ac)
        rr = (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.customer_phone.isnot(None))
            .order_by(CartRecoveryReason.updated_at.desc())
            .limit(220)
            .all()
        )
        for row in rr:
            if not _phone_key_matches(getattr(row, "customer_phone", None), phone_key):
                continue
            sid = (getattr(row, "session_id", None) or "").strip()[:512]
            if not sid:
                continue
            ac = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.recovery_session_id == sid)
                .order_by(AbandonedCart.last_seen_at.desc())
                .first()
            )
            if ac is not None:
                return ac, _store_for_abandoned_cart(ac)
        mlogs = (
            db.session.query(MessageLog)
            .filter(MessageLog.channel == "whatsapp")
            .order_by(MessageLog.created_at.desc())
            .limit(220)
            .all()
        )
        for ml in mlogs:
            if not _phone_key_matches(getattr(ml, "phone", None), phone_key):
                continue
            aid = getattr(ml, "abandoned_cart_id", None)
            if aid is not None:
                ac = db.session.get(AbandonedCart, int(aid))
                if ac is not None:
                    return ac, _store_for_abandoned_cart(ac)
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
    return None, None


def _store_for_abandoned_cart(ac: AbandonedCart) -> Optional[Store]:
    raw = getattr(ac, "store_id", None)
    if raw is None:
        return None
    try:
        return db.session.get(Store, int(raw))
    except (TypeError, ValueError, SQLAlchemyError):
        db.session.rollback()
        return None


def upsert_merchant_followup_after_positive_reply(
    *,
    customer_phone_key: str,
    inbound_body: str,
    abandoned_cart: Optional[AbandonedCart],
) -> MerchantFollowupAction:
    """ينشئ أو يحدّث صفاً بحالة ‎needs_merchant_followup‎ لنفس الرقم."""
    now = datetime.now(timezone.utc)
    key = (customer_phone_key or "").strip()[:100]
    msg = (inbound_body or "").strip()[:512]
    row = (
        db.session.query(MerchantFollowupAction)
        .filter(
            MerchantFollowupAction.customer_phone == key,
            MerchantFollowupAction.status == STATUS_NEEDS_MERCHANT_FOLLOWUP,
        )
        .order_by(MerchantFollowupAction.updated_at.desc())
        .first()
    )
    store_id: Optional[int] = None
    cart_id: Optional[int] = None
    if abandoned_cart is not None:
        cart_id = int(abandoned_cart.id)
        sid = getattr(abandoned_cart, "store_id", None)
        if sid is not None:
            try:
                store_id = int(sid)
            except (TypeError, ValueError):
                store_id = None
    if row is not None:
        row.reason = REASON_CUSTOMER_REPLIED_YES
        row.inbound_message = msg
        row.updated_at = now
        if cart_id is not None:
            row.abandoned_cart_id = cart_id
        if store_id is not None:
            row.store_id = store_id
        return row
    new_row = MerchantFollowupAction(
        store_id=store_id,
        abandoned_cart_id=cart_id,
        customer_phone=key,
        status=STATUS_NEEDS_MERCHANT_FOLLOWUP,
        reason=REASON_CUSTOMER_REPLIED_YES,
        inbound_message=msg,
        created_at=now,
        updated_at=now,
    )
    db.session.add(new_row)
    return new_row


def process_inbound_whatsapp_for_positive_intent(
    body: Any,
    from_number: Any,
) -> None:
    """
    يُستدعى من ‎POST /webhook/whatsapp‎ — بدون رد تلقائي للعميل.
    """
    if not is_positive_recovery_reply(body):
        return
    print("[WA POSITIVE REPLY RECEIVED]", flush=True)
    log.info("[WA POSITIVE REPLY RECEIVED] from=%s", from_number)
    phone_key = normalize_wa_customer_digits(from_number)
    if len(phone_key) < 11:
        log.warning(
            "[WA POSITIVE REPLY] skip merchant action: could not normalize phone from=%s",
            from_number,
        )
        return
    try:
        db.create_all()
        ac, _store = find_latest_abandoned_cart_for_customer_phone(phone_key)
        upsert_merchant_followup_after_positive_reply(
            customer_phone_key=phone_key,
            inbound_body=str(body or "").strip(),
            abandoned_cart=ac,
        )
        db.session.commit()
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("positive wa reply merchant action failed: %s", e, exc_info=True)
        return
    print(
        "[MERCHANT ACTION CREATED]\n"
        f"customer_phone={phone_key}\n"
        f"reason={REASON_CUSTOMER_REPLIED_YES}",
        flush=True,
    )
    log.info(
        "[MERCHANT ACTION CREATED] customer_phone=%s reason=%s",
        phone_key,
        REASON_CUSTOMER_REPLIED_YES,
    )
