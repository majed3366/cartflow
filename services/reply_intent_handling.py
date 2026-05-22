# -*- coding: utf-8 -*-
"""
Reply Intent Handling v1 — customer WhatsApp reply → lifecycle intent → decision → action.

Additive classification only: does not send WhatsApp, change delays, schedules, or
recovery execution. Existing ``recovery_reply_intent`` / continuation engine unchanged.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict  # noqa: TC003 — Any for ORM rows in hook

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
    _emit_reply_intent_lines(lines)


def _emit_reply_intent_lines(lines: list[str]) -> None:
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def log_reply_intent_skipped(*, reason: str, detail: str = "", from_phone: str = "") -> None:
    lines = ["[REPLY INTENT SKIPPED]", f"reason={reason}"]
    if detail:
        lines.append(f"detail={detail[:120]}")
    fp = (from_phone or "").strip()
    if fp:
        lines.append(f"from_phone={fp[:40]}")
    _emit_reply_intent_lines(lines)


def _recovery_key_for_abandoned_cart(ac: Any, store: Any) -> str:
    from main import _normalize_store_slug, _recovery_key_from_payload

    slug = _normalize_store_slug(
        {"store": getattr(store, "zid_store_id", None) or "default"}
    )
    pl = {
        "store": slug,
        "session_id": (getattr(ac, "recovery_session_id", None) or "").strip(),
        "cart_id": (getattr(ac, "zid_cart_id", None) or "").strip(),
    }
    return _recovery_key_from_payload(pl)


def run_inbound_whatsapp_reply_intent_hook(body: Any, from_number: Any) -> None:
    """
    Webhook entry: always logs hook + context; classifies or skips with explicit reason.

    Does not send WhatsApp or mutate recovery schedules.
    """
    from sqlalchemy.exc import SQLAlchemyError

    from extensions import db
    from services.behavioral_recovery.state_store import (
        normal_recovery_message_was_sent_for_abandoned,
    )
    from services.whatsapp_positive_reply import (
        find_latest_abandoned_cart_for_customer_phone,
        normalize_wa_customer_digits,
    )

    raw_body = str(body or "").strip()
    from_raw = str(from_number or "").strip()
    phone_key = normalize_wa_customer_digits(from_number)

    _emit_reply_intent_lines(
        [
            "[REPLY INTENT HOOK]",
            "received=true",
            f"from_phone={from_raw[:48] or '-'}",
            f"body={raw_body[:200] or '-'}",
        ]
    )

    if not raw_body:
        log_reply_intent_skipped(
            reason="empty_body",
            from_phone=from_raw,
        )
        return

    if len(phone_key) < 11:
        log_reply_intent_skipped(
            reason="invalid_phone",
            detail=phone_key or "missing",
            from_phone=from_raw,
        )
        return

    ac = None
    store = None
    try:
        db.create_all()
        ac, store = find_latest_abandoned_cart_for_customer_phone(phone_key)
    except (SQLAlchemyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log_reply_intent_skipped(
            reason="no_recovery_context",
            detail=f"lookup_error:{type(exc).__name__}",
            from_phone=from_raw,
        )
        return

    if ac is None:
        _emit_reply_intent_lines(
            [
                "[REPLY INTENT CONTEXT]",
                "found=false",
                f"phone_key={phone_key[:20]}",
            ]
        )
        log_reply_intent_skipped(
            reason="no_recovery_context",
            detail="no_abandoned_cart",
            from_phone=from_raw,
        )
        return

    session_id = (getattr(ac, "recovery_session_id", None) or "").strip()
    cart_id = (getattr(ac, "zid_cart_id", None) or "").strip()
    recovery_key = _recovery_key_for_abandoned_cart(ac, store)

    _emit_reply_intent_lines(
        [
            "[REPLY INTENT CONTEXT]",
            "found=true",
            f"session_id={session_id[:80] or '-'}",
            f"cart_id={cart_id[:64] or '-'}",
            f"recovery_key={recovery_key[:120]}",
            f"phone_key={phone_key[:20]}",
        ]
    )

    if bool(getattr(ac, "vip_mode", False)):
        log_reply_intent_skipped(
            reason="no_recovery_context",
            detail="vip_cart",
            from_phone=from_raw,
        )
        return

    if not normal_recovery_message_was_sent_for_abandoned(ac):
        log_reply_intent_skipped(
            reason="no_recovery_context",
            detail="no_prior_recovery_send",
            from_phone=from_raw,
        )
        return

    ri_result = handle_customer_reply_lifecycle_intent_v1(
        raw_body,
        session_id=session_id,
        cart_id=cart_id,
    )
    from services.purchase_lifecycle_closure import (
        record_purchase_lifecycle_closure_from_reply_intent,
    )

    record_purchase_lifecycle_closure_from_reply_intent(
        ri_result,
        recovery_key=recovery_key,
        session_id=session_id,
        cart_id=cart_id,
        ac=ac,
    )


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
