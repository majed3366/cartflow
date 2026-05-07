# -*- coding: utf-8 -*-
"""Inbound WhatsApp → stop generic sequence; switch to interactive recovery mode (normal carts only)."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from services.behavioral_recovery.state_store import (
    merge_behavioral_state,
    normal_recovery_message_was_sent_for_abandoned,
    utc_now_iso,
)
from services.whatsapp_positive_reply import (
    find_latest_abandoned_cart_for_customer_phone,
    normalize_wa_customer_digits,
)

log = logging.getLogger("cartflow")


def _meaningful_inbound_body(body: Any) -> bool:
    if body is None:
        return False
    return bool(str(body).strip())


def process_inbound_behavioral_recovery(body: Any, from_number: Any) -> None:
    """
    Any non-empty customer reply after a normal recovery send:
    - customer_replied / interactive_mode on AbandonedCart
    - logs [RECOVERY CUSTOMER REPLIED] + [RECOVERY FLOW SWITCHED TO INTERACTIVE]
    VIP carts skipped (VIP flow unchanged).
    """
    if not _meaningful_inbound_body(body):
        return
    phone_key = normalize_wa_customer_digits(from_number)
    if len(phone_key) < 11:
        return
    ac = None
    try:
        db.create_all()
        ac, _store = find_latest_abandoned_cart_for_customer_phone(phone_key)
        if ac is None:
            return
        if bool(getattr(ac, "vip_mode", False)):
            return
        if not normal_recovery_message_was_sent_for_abandoned(ac):
            return
        merge_behavioral_state(
            ac,
            customer_replied=True,
            interactive_mode=True,
            lifecycle_hint="interactive",
            customer_replied_at=utc_now_iso(),
        )
        db.session.add(ac)
        db.session.commit()
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("behavioral inbound recovery: %s", e, exc_info=True)
        return
    if ac is None:
        return
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    cid = (getattr(ac, "zid_cart_id", None) or "").strip()
    line1 = (
        f"[RECOVERY CUSTOMER REPLIED] session_id={sid} cart_id={cid} phone={phone_key}"
    )
    line2 = (
        "[RECOVERY FLOW SWITCHED TO INTERACTIVE] "
        f"session_id={sid} cart_id={cid}"
    )
    print(line1, flush=True)
    print(line2, flush=True)
    log.info("%s", line1)
    log.info("%s", line2)
