# -*- coding: utf-8 -*-
"""
Continuation Layer Stabilization v1 — safe behavior-only auto-replies.

Uses lifecycle intent buckets from ``reply_intent_handling`` (read-only).
No product intelligence / cheaper-alternative suggestions.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from services.reply_intent_handling import (
    INTENT_DELIVERY,
    INTENT_PRICE,
    INTENT_PURCHASE,
    INTENT_STOP,
    INTENT_UNKNOWN,
    classify_reply_lifecycle_intent_v1,
)

if TYPE_CHECKING:
    from services.cartflow_reply_intent_engine import ContinuationDecision

log = logging.getLogger("cartflow")

CONTINUATION_TYPE_REASSURANCE = "reassurance"
CONTINUATION_TYPE_CLARIFYING_QUESTION = "clarifying_question"
CONTINUATION_TYPE_SHIPPING_REASSURANCE = "shipping_reassurance"
CONTINUATION_TYPE_STOPPED = "stopped"
CONTINUATION_TYPE_FALLBACK = "fallback"

PRICE_REASSURANCE_MESSAGE_AR = (
    "أفهمك 👍 أحيانًا توضيح القيمة يساعد باتخاذ القرار."
)
PRICE_CLARIFYING_MESSAGE_AR = "أفهمك 👍 هل السعر هو السبب الرئيسي؟"
DELIVERY_SAFE_REASSURANCE_AR = (
    "أكيد 👍 التوصيل يعتمد على عنوانك وطريقة الشحن المتاحة.\n"
    "نقدر نوضح الخيارات بدون التزام بموعد محدد قبل ما تكمل الطلب."
)
FALLBACK_SAFE_MESSAGE_AR = (
    "شكراً لتواصلك 👍\n"
    "إذا حاب توضيح بسيط عن السلة أو الإكمال، أنا هنا."
)


def log_continuation_decision(
    *,
    lifecycle_intent: str,
    continuation_type: str,
    session_id: str = "",
) -> None:
    lines = [
        "[CONTINUATION DECISION]",
        f"intent={lifecycle_intent}",
        f"continuation_type={continuation_type}",
    ]
    sid = (session_id or "").strip()
    if sid:
        lines.append(f"session_id={sid[:80]}")
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def _price_continuation_type(base_intent: str) -> str:
    if (base_intent or "").strip() == "asks_price":
        return CONTINUATION_TYPE_CLARIFYING_QUESTION
    return CONTINUATION_TYPE_REASSURANCE


def _price_safe_message(base_intent: str) -> str:
    if _price_continuation_type(base_intent) == CONTINUATION_TYPE_CLARIFYING_QUESTION:
        return PRICE_CLARIFYING_MESSAGE_AR
    return PRICE_REASSURANCE_MESSAGE_AR


def apply_continuation_stabilization_v1(
    inbound_body: str,
    decision: ContinuationDecision,
    *,
    base_intent: str,
    session_id: str = "",
) -> ContinuationDecision:
    """
    Override continuation actions/messages for v1 safe paths.

    Never emits ``send_cheaper_alternative``.
    """
    from services.cartflow_reply_intent_engine import (
        CONTINUATION_ACTION_EXPLAIN_SHIPPING,
        CONTINUATION_ACTION_GRACEFUL_EXIT,
        CONTINUATION_ACTION_REASSURANCE,
        CONTINUATION_ACTION_SEND_CHEAPER,
        CONTINUATION_ACTION_WAIT,
        continuation_state_key,
        dashboard_summary_ar,
    )

    lifecycle_intent = classify_reply_lifecycle_intent_v1(inbound_body)
    sid = (session_id or "").strip()

    if lifecycle_intent == INTENT_PURCHASE:
        log_continuation_decision(
            lifecycle_intent=lifecycle_intent,
            continuation_type=CONTINUATION_TYPE_STOPPED,
            session_id=sid,
        )
        return replace(
            decision,
            action=CONTINUATION_ACTION_WAIT,
            message_to_send="",
            should_send=False,
            continuation_state="recovery_closing",
            summary_ar="العميل أكمل الطلب — إيقاف المتابعة الآلية",
            lifecycle_intent=lifecycle_intent,
            continuation_type=CONTINUATION_TYPE_STOPPED,
            stop_continuation=True,
        )

    if lifecycle_intent == INTENT_STOP:
        log_continuation_decision(
            lifecycle_intent=lifecycle_intent,
            continuation_type=CONTINUATION_TYPE_STOPPED,
            session_id=sid,
        )
        return replace(
            decision,
            action=CONTINUATION_ACTION_GRACEFUL_EXIT,
            message_to_send="",
            should_send=False,
            continuation_state="recovery_closing",
            summary_ar="العميل أنهى المحادثة — إيقاف الاسترجاع الآلي",
            lifecycle_intent=lifecycle_intent,
            continuation_type=CONTINUATION_TYPE_STOPPED,
            stop_continuation=True,
        )

    if lifecycle_intent == INTENT_PRICE or decision.action == CONTINUATION_ACTION_SEND_CHEAPER:
        ctype = _price_continuation_type(base_intent)
        msg = _price_safe_message(base_intent)
        log_continuation_decision(
            lifecycle_intent=INTENT_PRICE,
            continuation_type=ctype,
            session_id=sid,
        )
        ctx = decision.contextual_intent or "asks_price_detail"
        act = CONTINUATION_ACTION_REASSURANCE
        return replace(
            decision,
            action=act,
            message_to_send=msg,
            should_send=bool(msg.strip()),
            continuation_state=continuation_state_key(ctx, act),
            summary_ar="العميل يتحدث عن السعر — طمأنة بدون بديل وهمي",
            lifecycle_intent=INTENT_PRICE,
            continuation_type=ctype,
            stop_continuation=False,
        )

    if lifecycle_intent == INTENT_DELIVERY:
        log_continuation_decision(
            lifecycle_intent=lifecycle_intent,
            continuation_type=CONTINUATION_TYPE_SHIPPING_REASSURANCE,
            session_id=sid,
        )
        ctx = decision.contextual_intent or "asks_delivery_detail"
        act = CONTINUATION_ACTION_EXPLAIN_SHIPPING
        msg = DELIVERY_SAFE_REASSURANCE_AR
        return replace(
            decision,
            action=act,
            message_to_send=msg,
            should_send=bool(msg.strip()),
            continuation_state=continuation_state_key(ctx, act),
            summary_ar="العميل يسأل عن التوصيل — طمأنة بدون وعود محددة",
            lifecycle_intent=lifecycle_intent,
            continuation_type=CONTINUATION_TYPE_SHIPPING_REASSURANCE,
            stop_continuation=False,
        )

    if lifecycle_intent == INTENT_UNKNOWN:
        if decision.action == CONTINUATION_ACTION_SEND_CHEAPER:
            ctype = _price_continuation_type(base_intent)
            msg = _price_safe_message(base_intent)
            log_continuation_decision(
                lifecycle_intent=INTENT_UNKNOWN,
                continuation_type=ctype,
                session_id=sid,
            )
            act = CONTINUATION_ACTION_REASSURANCE
            return replace(
                decision,
                action=act,
                message_to_send=msg,
                should_send=bool(msg.strip()),
                summary_ar="رد آمن — بدون بديل منتج",
                lifecycle_intent=lifecycle_intent,
                continuation_type=ctype,
                stop_continuation=False,
            )
        log_continuation_decision(
            lifecycle_intent=lifecycle_intent,
            continuation_type=CONTINUATION_TYPE_FALLBACK,
            session_id=sid,
        )
        if decision.action == CONTINUATION_ACTION_WAIT and not decision.message_to_send:
            return replace(
                decision,
                lifecycle_intent=lifecycle_intent,
                continuation_type=CONTINUATION_TYPE_FALLBACK,
                stop_continuation=False,
            )
        return replace(
            decision,
            lifecycle_intent=lifecycle_intent,
            continuation_type=CONTINUATION_TYPE_FALLBACK,
            stop_continuation=False,
        )

    return decision
