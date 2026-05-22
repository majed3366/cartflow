# -*- coding: utf-8 -*-
"""
Reply Intent Handling v1 — customer WhatsApp reply → lifecycle intent → decision → action.

Additive classification only: does not send WhatsApp, change delays, schedules, or
recovery execution. Existing ``recovery_reply_intent`` / continuation engine unchanged.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

from services.lifecycle_intelligence import (
    DECISION_FALLBACK,
    DECISION_HANDOFF,
    DECISION_STOP,
)

log = logging.getLogger("cartflow")

INTENT_PURCHASE = "PURCHASE"
INTENT_STOP = "STOP"
INTENT_PRICE = "PRICE"
INTENT_DELIVERY = "DELIVERY"
INTENT_UNKNOWN = "UNKNOWN"

_ACTION_CLOSE_LIFECYCLE = "close_lifecycle"
_ACTION_STOP_RECOVERY = "stop_recovery"
_ACTION_HANDOFF_LATER = "handoff_later"
_ACTION_FALLBACK = "fallback"


class ReplyIntentHandlingResult(TypedDict):
    intent: str
    decision: str
    action: str
    reply_preview: str


def _normalize_reply_text(raw: str) -> str:
    t = (raw or "").strip().lower()
    for a, b in (
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ٱ", "ا"),
        ("ى", "ي"),
        ("ة", "ه"),
        ("ؤ", "و"),
        ("ئ", "ي"),
    ):
        t = t.replace(a, b)
    return " ".join(t.split())


def _contains_phrase(norm: str, phrases: frozenset[str]) -> bool:
    if not norm:
        return False
    for p in phrases:
        pn = _normalize_reply_text(p)
        if not pn:
            continue
        if norm == pn or (len(pn) > 2 and pn in norm):
            return True
    return False


_PURCHASE_PHRASES = frozenset(
    {
        "تم الطلب",
        "تم الشراء",
        "اكملت الطلب",
        "أكملت الطلب",
        "اشتريت",
        "طلبت",
        "تم الدفع",
        "دفعت",
        "order done",
        "purchased",
    }
)

_STOP_PHRASES = frozenset(
    {
        "لا اريد",
        "لا أريد",
        "لا ابغى",
        "لا أبغى",
        "مو مهتم",
        "مش مهتم",
        "لا شكرا",
        "لا شكراً",
        "وقف",
        "اوقف",
        "أوقف",
        "not interested",
        "no thanks",
        "stop",
    }
)

_PRICE_PHRASES = frozenset(
    {
        "غالي",
        "غاليا",
        "السعر",
        "سعره",
        "خصم",
        "تخفيض",
        "expensive",
        "too expensive",
        "price",
    }
)

_DELIVERY_PHRASES = frozenset(
    {
        "متى التوصيل",
        "متى يوصل",
        "متى يصل",
        "موعد التوصيل",
        "وقت التوصيل",
        "يوصل متى",
        "وين الطلب",
        "delivery",
        "when deliver",
    }
)


def classify_reply_lifecycle_intent_v1(reply: str) -> str:
    """Map inbound reply text to a single lifecycle intent (v1 buckets)."""
    norm = _normalize_reply_text(reply)
    if not norm:
        return INTENT_UNKNOWN
    if _contains_phrase(norm, _PURCHASE_PHRASES):
        return INTENT_PURCHASE
    if _contains_phrase(norm, _STOP_PHRASES):
        return INTENT_STOP
    if _contains_phrase(norm, _PRICE_PHRASES):
        return INTENT_PRICE
    if _contains_phrase(norm, _DELIVERY_PHRASES):
        return INTENT_DELIVERY
    return INTENT_UNKNOWN


def lifecycle_decision_for_reply_intent(intent: str) -> tuple[str, str]:
    """Intent → (lifecycle decision, action hint) — no side effects."""
    key = (intent or "").strip().upper()
    if key == INTENT_PURCHASE:
        return DECISION_STOP, _ACTION_CLOSE_LIFECYCLE
    if key == INTENT_STOP:
        return DECISION_STOP, _ACTION_STOP_RECOVERY
    if key in (INTENT_PRICE, INTENT_DELIVERY):
        return DECISION_HANDOFF, _ACTION_HANDOFF_LATER
    return DECISION_FALLBACK, _ACTION_FALLBACK


def log_reply_intent_handling(
    result: ReplyIntentHandlingResult,
    *,
    session_id: str = "",
    cart_id: str = "",
) -> None:
    preview = (result.get("reply_preview") or "").replace("\n", " ")[:200]
    lines = [
        "[REPLY INTENT]",
        f'reply="{preview}"',
        f"intent={result.get('intent', '')}",
        f"decision={result.get('decision', '')}",
        f"action={result.get('action', '')}",
    ]
    sid = (session_id or "").strip()
    if sid:
        lines.append(f"session_id={sid[:80]}")
    cid = (cart_id or "").strip()
    if cid:
        lines.append(f"cart_id={cid[:64]}")
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def handle_customer_reply_lifecycle_intent_v1(
    reply: str,
    *,
    session_id: str = "",
    cart_id: str = "",
) -> ReplyIntentHandlingResult:
    """
    Classify reply, derive lifecycle decision/action, emit ``[REPLY INTENT]`` log.

    Call from inbound WhatsApp path after a normal recovery send exists.
    """
    body = (reply or "").strip()
    intent = classify_reply_lifecycle_intent_v1(body)
    decision, action = lifecycle_decision_for_reply_intent(intent)
    result: ReplyIntentHandlingResult = {
        "intent": intent,
        "decision": decision,
        "action": action,
        "reply_preview": body[:200],
    }
    log_reply_intent_handling(
        result,
        session_id=session_id,
        cart_id=cart_id,
    )
    return result
