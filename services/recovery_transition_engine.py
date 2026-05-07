# -*- coding: utf-8 -*-
"""انتقال من أتمتة مجدولة إلى وضع تفاعلي عند رد العميل على واتساب الاسترجاع."""
from __future__ import annotations

import logging
from typing import Any

from models import AbandonedCart

from services.recovery_interaction_state import STATE_ENGAGED, truncate_preview_text
from services.recovery_reply_intent_detector import detect_recovery_reply_intent
from services.recovery_reply_intent_labels import recovery_reply_intent_badge_ar

log = logging.getLogger("cartflow")

_MAX_LATEST_CUSTOMER_MESSAGE_CHARS = 2048


def inbound_patch_for_recovery_reply(inbound_body: str) -> dict[str, Any]:
    """
    حقول ‎cf_behavioral‎ عند رد عميل بعد إرسال استرجاع عادي.
    """
    from services.behavioral_recovery.state_store import utc_now_iso

    body = (inbound_body or "").strip()
    preview = truncate_preview_text(body)
    now = utc_now_iso()
    has_question = "?" in body or "؟" in body
    intent = detect_recovery_reply_intent(body)
    latest_msg = body[:_MAX_LATEST_CUSTOMER_MESSAGE_CHARS]
    patch: dict[str, Any] = {
        "customer_replied": True,
        "interactive_mode": True,
        "lifecycle_hint": "interactive",
        "customer_replied_at": now,
        "recovery_conversation_state": STATE_ENGAGED,
        "last_customer_reply_preview": preview,
        "last_customer_reply_at": now,
        "recovery_reply_intent": intent,
        "latest_customer_message": latest_msg,
        "latest_customer_reply_at": now,
    }
    if has_question:
        patch["waiting_merchant"] = True
    else:
        patch["waiting_merchant"] = False
    return patch


def apply_interactive_transition_from_customer_reply(
    ac: AbandonedCart,
    *,
    inbound_body: str,
    customer_phone_key: str,
) -> None:
    """يحدّث الحمولة السلوكية فقط — الالتزام على المستدعي بـ ‎commit‎."""
    from services.behavioral_recovery.state_store import merge_behavioral_state

    patch = inbound_patch_for_recovery_reply(inbound_body)
    merge_behavioral_state(ac, **patch)
    intent = str(patch.get("recovery_reply_intent") or "").strip()
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    cid = (getattr(ac, "zid_cart_id", None) or "").strip()
    msg_line = truncate_preview_text(inbound_body, max_chars=80)
    print("[RECOVERY CUSTOMER REPLIED]", flush=True)
    print(f"session_id={sid}", flush=True)
    print(f"customer_phone={customer_phone_key}", flush=True)
    print(f"message={msg_line}", flush=True)
    if intent:
        print(f"[RECOVERY REPLY INTENT] intent={intent}", flush=True)
        log.info(
            "[RECOVERY REPLY INTENT] session_id=%s intent=%s label=%s",
            sid,
            intent,
            recovery_reply_intent_badge_ar(intent),
        )
    log.info(
        "[RECOVERY CUSTOMER REPLIED] session_id=%s customer_phone=%s message_len=%s",
        sid,
        customer_phone_key,
        len((inbound_body or "").strip()),
    )
    print("[RECOVERY AUTOMATION STOPPED] reason=customer_replied", flush=True)
    log.info(
        "[RECOVERY AUTOMATION STOPPED] reason=customer_replied session_id=%s cart_id=%s",
        sid,
        cid,
    )
