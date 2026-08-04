# -*- coding: utf-8 -*-
"""
Meta recovery template inbound handling V1.

When the customer taps QUICK_REPLY «خدمة العملاء»:
- record a normal customer interaction event with customer_requested_human_support=true
- continue through the existing Conversation inbound pipeline
- do NOT send any automatic AI / WhatsApp reply
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from services.meta_recovery_template_contract_v1 import (
    BUTTON_QUICK_REPLY_TEXT,
    is_customer_support_quick_reply,
)

log = logging.getLogger("cartflow")

EVENT_TYPE_CUSTOMER_INTERACTION = "customer_interaction"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def persist_customer_interaction_event(
    *,
    from_phone: str,
    message_id: Optional[str],
    text: str,
    button_payload: str,
    customer_requested_human_support: bool,
) -> bool:
    """Persist interaction event. Returns True when stored (best-effort)."""
    try:
        from extensions import db
        from models import RecoveryEvent

        db.create_all()
        payload = {
            "event": EVENT_TYPE_CUSTOMER_INTERACTION,
            "from": (from_phone or "")[:40],
            "message_id": (message_id or "")[:128] or None,
            "text": (text or "")[:500],
            "button_payload": (button_payload or "")[:200] or None,
            "customer_requested_human_support": bool(customer_requested_human_support),
            "button_text": BUTTON_QUICK_REPLY_TEXT
            if customer_requested_human_support
            else None,
            "observed_at": _utc_now_iso(),
            "ai_auto_reply": False,
        }
        row = RecoveryEvent(
            event_type=EVENT_TYPE_CUSTOMER_INTERACTION,
            payload=json.dumps(payload, ensure_ascii=False)[:65000],
        )
        db.session.add(row)
        db.session.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[META TPL INBOUND] persist_customer_interaction_failed: %s",
            type(exc).__name__,
        )
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        return False


def continue_conversation_pipeline(*, message: str, from_number: str) -> None:
    """
    Existing Conversation inbound path (same hooks as Twilio webhook).
    Never sends an automatic AI reply from this layer.
    """
    try:
        from services.whatsapp_production_reality_v2 import (
            observe_inbound_whatsapp_message,
        )

        observe_inbound_whatsapp_message(message, from_number)
    except Exception as exc:  # noqa: BLE001
        log.warning("[META TPL INBOUND] observe_failed: %s", type(exc).__name__)

    try:
        from services.behavioral_recovery.inbound_whatsapp import (
            process_inbound_behavioral_recovery,
        )
        from services.reply_intent_handling import run_inbound_whatsapp_reply_intent_hook
        from services.whatsapp_positive_reply import (
            process_inbound_whatsapp_for_positive_intent,
        )

        run_inbound_whatsapp_reply_intent_hook(message, from_number)
        process_inbound_behavioral_recovery(message, from_number)
        process_inbound_whatsapp_for_positive_intent(message, from_number)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[META TPL INBOUND] conversation_pipeline_failed: %s",
            type(exc).__name__,
            exc_info=True,
        )


def handle_meta_inbound_message(inbound: dict[str, Any]) -> dict[str, Any]:
    """
    Process one parsed Meta inbound message.

    Returns a safe summary (no secrets).
    """
    if not isinstance(inbound, dict):
        return {"ok": False, "error": "invalid_inbound"}

    text = str(inbound.get("text") or "").strip()
    payload = str(inbound.get("button_payload") or "").strip()
    from_phone = str(inbound.get("from") or "").strip()
    message_id = str(inbound.get("message_id") or "").strip() or None

    support = is_customer_support_quick_reply(text=text, payload=payload)
    stored = False
    if support:
        stored = persist_customer_interaction_event(
            from_phone=from_phone,
            message_id=message_id,
            text=text or BUTTON_QUICK_REPLY_TEXT,
            button_payload=payload,
            customer_requested_human_support=True,
        )
        log.info(
            "[META TPL INBOUND] customer_requested_human_support=true from=%s stored=%s",
            (from_phone or "-")[:20],
            stored,
        )

    # Always continue Conversation pipeline for inbound (no AI auto-reply here)
    pipeline_message = text or (BUTTON_QUICK_REPLY_TEXT if support else "")
    if from_phone and pipeline_message:
        continue_conversation_pipeline(
            message=pipeline_message,
            from_number=from_phone,
        )

    return {
        "ok": True,
        "customer_requested_human_support": support,
        "interaction_event_stored": stored if support else False,
        "ai_auto_reply": False,
    }


__all__ = [
    "EVENT_TYPE_CUSTOMER_INTERACTION",
    "handle_meta_inbound_message",
    "persist_customer_interaction_event",
    "continue_conversation_pipeline",
]
