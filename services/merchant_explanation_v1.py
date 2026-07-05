# -*- coding: utf-8 -*-
"""
Merchant Explanation v1 — unified merchant-facing cart lifecycle/recovery copy.

Single presentation layer for cart detail explanations. Internal lifecycle/recovery
state keys and diagnostics never reach merchant UI through this module.

Does not mint Truth, schedule recovery, or alter Decision Layer behavior.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Optional

EXPLANATION_VERSION = "v1"

VISIBILITY_MERCHANT = "merchant_dashboard"
SURFACE_CART_DETAIL = "cart_detail"
SURFACE_CART_ROW = "cart_row_chip"

ATTENTION_NONE = "none"
ATTENTION_INFORMATIONAL = "informational"
ATTENTION_NEEDS_REVIEW = "attention"
ATTENTION_URGENT = "urgent"

# Internal state keys — never merchant-visible.
_STATE_ACTIVE = "active"
_STATE_WAITING_FIRST_SEND = "waiting_first_send"
_STATE_WAITING_CUSTOMER_REPLY = "waiting_customer_reply"
_STATE_CUSTOMER_ENGAGED = "customer_engaged"
_STATE_CUSTOMER_REPLY = "customer_reply"
_STATE_RETURN_TO_SITE = "return_to_site"
_STATE_WAITING_PURCHASE_WINDOW = "waiting_purchase_window"
_STATE_WAITING_NEXT_SCHEDULED = "waiting_next_scheduled"
_STATE_NEEDS_INTERVENTION = "needs_intervention"
_STATE_COMPLETED = "completed"
_STATE_ARCHIVED = "archived"
_STATE_RECOVERY_FOLLOWUP_COMPLETE = "recovery_followup_complete"
_STATE_UNAVAILABLE = "lifecycle_unavailable"

_EXPLANATION_ID_UNAVAILABLE = "lifecycle_unavailable"

_FORBIDDEN_MERCHANT_PATTERNS = re.compile(
    r"(?i)"
    r"(waiting_[a-z_]+|return_to_site|needs_intervention|lifecycle_unavailable|"
    r"customer_engaged|recovery_followup|mock_sent|sent_real|whatsapp_failed|"
    r"purchase_truth|provider_truth|lifecycle_truth|recovery_truth|"
    r"حالة المسار|قبول المزود|سجل إرسال|Purchase Truth|Lifecycle Truth)"
)

_EXPLANATION_CATALOG: dict[str, dict[str, Any]] = {
    _STATE_ACTIVE: {
        "explanation_id": "cart_active",
        "knowledge_event_type": "cart_active",
        "status_label_ar": "السلة نشطة",
        "what_happened_ar": "العميل ترك سلّة في متجرك.",
        "system_did_ar": "CartFlow يراقب السلة وفق إعدادات الاسترجاع.",
        "what_next_ar": "قد تُرسل رسالة استرجاع عند حلول وقت الإرسال.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_WAITING_FIRST_SEND: {
        "explanation_id": "waiting_first_send",
        "knowledge_event_type": "recovery_scheduled",
        "status_label_ar": "بانتظار الإرسال",
        "what_happened_ar": "تُركت سلّة دون إتمام الشراء.",
        "system_did_ar": "CartFlow جهّز مسار الاسترجاع وينتظر وقت الإرسال.",
        "what_next_ar": "ستُرسل رسالة واتساب تلقائياً عند حلول المهلة — لا يلزم إجراء منك.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_WAITING_CUSTOMER_REPLY: {
        "explanation_id": "waiting_customer_reply",
        "knowledge_event_type": "message_sent_waiting_reply",
        "status_label_ar": "بانتظار تفاعل العميل",
        "what_happened_ar": "أُرسلت رسالة استرجاع للعميل.",
        "system_did_ar": "CartFlow أرسل رسالة واتساب وفق سبب التردد.",
        "what_next_ar": "ننتظر تفاعل العميل — سيتابع CartFlow تلقائياً.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_CUSTOMER_REPLY: {
        "explanation_id": "customer_replied",
        "knowledge_event_type": "customer_replied",
        "status_label_ar": "ردّ العميل",
        "what_happened_ar": "ردّ العميل على رسالة الاسترجاع.",
        "system_did_ar": "CartFlow سجّل الرد — المتابعة التلقائية تبدأ عند الحاجة.",
        "what_next_ar": "نراقب هل يكمّل الطلب أو يرد مرة أخرى.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_CUSTOMER_ENGAGED: {
        "explanation_id": "customer_engaged",
        "knowledge_event_type": "customer_engaged_continuation",
        "status_label_ar": "تفاعل العميل — أرسل CartFlow متابعة",
        "what_happened_ar": "ردّ العميل بعد رسالة الاسترجاع.",
        "system_did_ar": "CartFlow أرسل متابعة الاعتراض تلقائياً.",
        "what_next_ar": "لا حاجة لرسائل إرسال إضافية — المتابعة آلية.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_RETURN_TO_SITE: {
        "explanation_id": "customer_returned",
        "knowledge_event_type": "customer_returned_to_site",
        "status_label_ar": "عاد العميل للمتجر",
        "what_happened_ar": "عاد العميل إلى المتجر.",
        "system_did_ar": "CartFlow أوقف المتابعة مؤقتًا حتى لا يزعج العميل.",
        "what_next_ar": "لا حاجة لإجراء منك — CartFlow يراقب ما إذا أكمل الشراء.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_WAITING_PURCHASE_WINDOW: {
        "explanation_id": "return_without_purchase",
        "knowledge_event_type": "return_after_message_waiting_purchase",
        "status_label_ar": "عاد العميل — نراقب إكمال الشراء",
        "what_happened_ar": "عاد العميل إلى المتجر بعد رسالة الاسترجاع.",
        "system_did_ar": (
            "CartFlow أوقف المتابعة مؤقتًا حتى لا يزعج العميل "
            "أثناء احتمالية الشراء."
        ),
        "what_next_ar": (
            "إذا لم يكتمل الشراء خلال فترة الانتظار، "
            "سيواصل CartFlow المتابعة حسب الإعدادات."
        ),
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_WAITING_NEXT_SCHEDULED: {
        "explanation_id": "waiting_next_message",
        "knowledge_event_type": "followup_scheduled",
        "status_label_ar": "بانتظار المتابعة التالية",
        "what_happened_ar": "العميل لم يرد على الرسالة السابقة بعد.",
        "system_did_ar": "CartFlow أرسل الرسالة السابقة وفق القالب.",
        "what_next_ar": "المتابعة التالية مجدولة — سيتابع CartFlow تلقائياً.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_NEEDS_INTERVENTION: {
        "explanation_id": "needs_merchant_attention",
        "knowledge_event_type": "recovery_needs_attention",
        "status_label_ar": "تحتاج مراجعة",
        "what_happened_ar": "تعذّر على CartFlow إكمال مسار الاسترجاع آلياً.",
        "system_did_ar": "CartFlow أوقف الإرسال الآلي أو تعذّر إكماله.",
        "what_next_ar": "راجع بيانات التواصل أو قناة واتساب ثم حدّث الصفحة.",
        "attention_level": ATTENTION_URGENT,
        "action_required": True,
    },
    _STATE_COMPLETED: {
        "explanation_id": "purchase_confirmed",
        "knowledge_event_type": "purchase_confirmed",
        "status_label_ar": "تمت الاستعادة",
        "what_happened_ar": "أكمل العميل الشراء.",
        "system_did_ar": "CartFlow أكد الشراء — انتهت مهمة الاسترجاع.",
        "what_next_ar": "لا حاجة لرسائل استرجاع إضافية.",
        "attention_level": ATTENTION_NONE,
        "action_required": False,
    },
    _STATE_ARCHIVED: {
        "explanation_id": "cart_archived",
        "knowledge_event_type": "cart_archived",
        "status_label_ar": "مؤرشفة",
        "what_happened_ar": "أُرشفت هذه السلة من قائمة المتابعة النشطة.",
        "system_did_ar": "CartFlow أوقف العرض النشط — السجل محفوظ.",
        "what_next_ar": "يمكنك إعادة فتحها من لوحة السلال إن رغبت.",
        "attention_level": ATTENTION_NONE,
        "action_required": False,
    },
    _STATE_RECOVERY_FOLLOWUP_COMPLETE: {
        "explanation_id": "recovery_followup_complete",
        "knowledge_event_type": "recovery_sequence_complete",
        "status_label_ar": "انتهت متابعة CartFlow",
        "what_happened_ar": "تم إرسال جميع رسائل المتابعة ولم يحدث تفاعل.",
        "system_did_ar": "CartFlow أكمل جميع خطوات الاسترجاع الآلية.",
        "what_next_ar": "لا توجد رسائل مجدولة — يمكنك المراجعة يدوياً إن رغبت.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
    _STATE_UNAVAILABLE: {
        "explanation_id": _EXPLANATION_ID_UNAVAILABLE,
        "knowledge_event_type": "lifecycle_unavailable",
        "status_label_ar": "— لا تتوفر حالة واضحة بعد —",
        "what_happened_ar": "لم تكتمل معلومات حالة هذه السلة بعد.",
        "system_did_ar": "CartFlow يعيد تحميل الحالة — حدّث الصفحة بعد لحظات.",
        "what_next_ar": "إذا استمرت المشكلة، تواصل مع الدعم.",
        "attention_level": ATTENTION_INFORMATIONAL,
        "action_required": False,
    },
}

# Merchant lifecycle primary keys → explanation when lifecycle state absent.
_PRIMARY_KEY_ALIASES: dict[str, str] = {
    "customer_returned_after_message": _STATE_WAITING_PURCHASE_WINDOW,
    "customer_returned": _STATE_RETURN_TO_SITE,
    "purchase_complete": _STATE_COMPLETED,
    "customer_replied": _STATE_CUSTOMER_REPLY,
    "needs_phone": _STATE_NEEDS_INTERVENTION,
    "channel_failed": _STATE_NEEDS_INTERVENTION,
    "needs_reason": _STATE_NEEDS_INTERVENTION,
    "delay_waiting": _STATE_WAITING_FIRST_SEND,
    "awaiting_customer_after_send": _STATE_WAITING_CUSTOMER_REPLY,
    "attempts_exhausted": _STATE_RECOVERY_FOLLOWUP_COMPLETE,
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _merchant_safe(text: str) -> bool:
    s = _norm(text)
    if not s:
        return False
    if _FORBIDDEN_MERCHANT_PATTERNS.search(s):
        return False
    if "_" in s and re.search(r"[a-z]{3,}_[a-z]", s, re.I):
        return False
    return True


def _pick_merchant_line(*candidates: str, fallback: str) -> str:
    for raw in candidates:
        s = _norm(raw)
        if s and _merchant_safe(s):
            return s
    return fallback


def _yes_no_to_ar(value: Any) -> str:
    v = _norm_lower(value)
    if v in ("نعم", "yes", "true", "1"):
        return "نعم"
    if v in ("لا", "no", "false", "0"):
        return "لا"
    return _norm(value)


def _resolve_state_key(
    *,
    lifecycle_state: str,
    merchant_lifecycle_primary_key: str = "",
    purchase_truth: bool = False,
) -> str:
    if purchase_truth:
        return _STATE_COMPLETED
    sk = _norm_lower(lifecycle_state)
    if sk in _EXPLANATION_CATALOG:
        return sk
    pk = _norm_lower(merchant_lifecycle_primary_key)
    if pk in _PRIMARY_KEY_ALIASES:
        return _PRIMARY_KEY_ALIASES[pk]
    return _STATE_UNAVAILABLE if not sk else _STATE_UNAVAILABLE


def build_merchant_explanation_v1(
    *,
    lifecycle_state: str = "",
    lifecycle_label_ar: str = "",
    what_happened_ar: str = "",
    system_did_ar: str = "",
    what_next_ar: str = "",
    followup_line_ar: str = "",
    merchant_needed_ar: str = "",
    merchant_lifecycle_primary_key: str = "",
    purchase_truth: bool = False,
    completed_variant: str = "",
    diagnostic_lifecycle_state: str = "",
    diagnostic_proof_summary_ar: str = "",
) -> dict[str, Any]:
    """Build unified merchant explanation payload (presentation only)."""
    state_key = _resolve_state_key(
        lifecycle_state=lifecycle_state,
        merchant_lifecycle_primary_key=merchant_lifecycle_primary_key,
        purchase_truth=purchase_truth,
    )
    base = dict(_EXPLANATION_CATALOG.get(state_key, _EXPLANATION_CATALOG[_STATE_UNAVAILABLE]))

    if state_key == _STATE_COMPLETED and _norm_lower(completed_variant) == "purchased":
        base = dict(base)
        base["status_label_ar"] = "تم الشراء"
        base["what_happened_ar"] = "أكمل العميل الشراء."
        base["system_did_ar"] = "CartFlow أكد الشراء — انتهت مهمة الاسترجاع."

    status_label = _pick_merchant_line(
        lifecycle_label_ar,
        fallback=str(base.get("status_label_ar") or ""),
    )
    what_happened = _pick_merchant_line(
        what_happened_ar,
        fallback=str(base.get("what_happened_ar") or ""),
    )
    system_did = _pick_merchant_line(
        system_did_ar,
        fallback=str(base.get("system_did_ar") or ""),
    )
    what_next = _pick_merchant_line(
        what_next_ar,
        fallback=str(base.get("what_next_ar") or ""),
    )
    followup = _pick_merchant_line(followup_line_ar, fallback="")

    action_required = bool(base.get("action_required"))
    needed = _yes_no_to_ar(merchant_needed_ar)
    if needed == "نعم":
        action_required = True

    attention = _norm(base.get("attention_level")) or ATTENTION_INFORMATIONAL
    if action_required and attention == ATTENTION_INFORMATIONAL:
        attention = ATTENTION_NEEDS_REVIEW

    merchant_action = "لا حاجة لإجراء — CartFlow يتابع تلقائياً."
    if action_required:
        merchant_action = what_next or "يلزم مراجعة منك لهذه السلة."

    diagnostic: dict[str, Any] = {
        "lifecycle_state": _norm(diagnostic_lifecycle_state or lifecycle_state),
        "merchant_lifecycle_primary_key": _norm(merchant_lifecycle_primary_key),
        "source_fields_used": {
            "lifecycle_label_ar": _norm(lifecycle_label_ar),
            "what_happened_ar": _norm(what_happened_ar),
            "system_did_ar": _norm(system_did_ar),
            "what_next_ar": _norm(what_next_ar),
        },
    }
    if diagnostic_proof_summary_ar:
        diagnostic["proof_summary_diagnostic_ar"] = _norm(diagnostic_proof_summary_ar)

    return {
        "version": EXPLANATION_VERSION,
        "explanation_id": _norm(base.get("explanation_id")),
        "knowledge_event_type": _norm(base.get("knowledge_event_type")),
        "merchant_visibility": VISIBILITY_MERCHANT,
        "eligible_surfaces": [SURFACE_CART_DETAIL, SURFACE_CART_ROW],
        "status_label_ar": status_label,
        "what_happened_ar": what_happened,
        "system_did_ar": system_did,
        "what_next_ar": what_next,
        "followup_line_ar": followup or None,
        "merchant_action_needed_ar": merchant_action,
        "action_required": action_required,
        "attention_level": attention,
        "diagnostic_internal": diagnostic,
    }


def sync_merchant_explanation_to_lifecycle_fields(row: dict[str, Any]) -> None:
    """Mirror unified explanation into legacy merchant-visible lifecycle text fields."""
    expl = row.get("merchant_explanation_v1")
    if not isinstance(expl, dict):
        return
    row["customer_lifecycle_label_ar"] = _norm(expl.get("status_label_ar"))
    row["customer_lifecycle_what_happened_ar"] = _norm(expl.get("what_happened_ar"))
    row["customer_lifecycle_system_did_ar"] = _norm(expl.get("system_did_ar"))
    row["customer_lifecycle_what_next_ar"] = _norm(expl.get("what_next_ar"))
    followup = _norm(expl.get("followup_line_ar"))
    if followup:
        row["customer_lifecycle_next_followup_line_ar"] = followup
    needed = "نعم" if expl.get("action_required") else "لا"
    row["customer_lifecycle_merchant_needed_ar"] = needed
    if expl.get("status_label_ar"):
        row["merchant_status_label_ar"] = _norm(expl.get("status_label_ar"))


def attach_merchant_explanation_v1(
    target: Mapping[str, Any] | dict[str, Any],
    *,
    purchase_truth: bool = False,
) -> None:
    """Attach unified merchant explanation to a normal-carts row (additive)."""
    if not isinstance(target, dict):
        return
    proof = target.get("merchant_proof_surface_v1")
    proof_diag = ""
    if isinstance(proof, dict):
        proof_diag = _norm(proof.get("why_we_know_diagnostic_ar"))

    expl = build_merchant_explanation_v1(
        lifecycle_state=str(target.get("customer_lifecycle_state") or ""),
        lifecycle_label_ar=str(target.get("customer_lifecycle_label_ar") or ""),
        what_happened_ar=str(target.get("customer_lifecycle_what_happened_ar") or ""),
        system_did_ar=str(target.get("customer_lifecycle_system_did_ar") or ""),
        what_next_ar=str(target.get("customer_lifecycle_what_next_ar") or ""),
        followup_line_ar=str(target.get("customer_lifecycle_next_followup_line_ar") or ""),
        merchant_needed_ar=str(target.get("customer_lifecycle_merchant_needed_ar") or ""),
        merchant_lifecycle_primary_key=str(
            target.get("merchant_lifecycle_primary_key") or ""
        ),
        purchase_truth=bool(
            purchase_truth
            or target.get("customer_lifecycle_completed_variant") == "purchased"
        ),
        completed_variant=str(target.get("customer_lifecycle_completed_variant") or ""),
        diagnostic_lifecycle_state=str(target.get("customer_lifecycle_state") or ""),
        diagnostic_proof_summary_ar=proof_diag,
    )
    target["merchant_explanation_v1"] = expl
    from services.knowledge_producer_metadata_v1 import (  # noqa: PLC0415
        enrich_explanation_knowledge_metadata_v1,
    )

    enrich_explanation_knowledge_metadata_v1(
        expl,
        store_slug=str(target.get("store_slug") or target.get("store") or ""),
        recovery_key=str(target.get("recovery_key") or ""),
        abandoned_cart_id=target.get("abandoned_cart_id") or target.get("id"),
        proof=target.get("merchant_proof_surface_v1"),
        lifecycle_state=str(target.get("customer_lifecycle_state") or ""),
    )
    sync_merchant_explanation_to_lifecycle_fields(target)

    # Keep legacy merchant lifecycle narrative aligned when present.
    if target.get("merchant_lifecycle_customer_behavior_ar") is not None:
        target["merchant_lifecycle_customer_behavior_ar"] = expl.get("what_happened_ar")
        target["merchant_lifecycle_system_outcome_ar"] = expl.get("system_did_ar")
        target["merchant_lifecycle_next_action_ar"] = expl.get("merchant_action_needed_ar")


def validate_merchant_explanation_merchant_safe(expl: Mapping[str, Any]) -> list[str]:
    """Return forbidden token hits in merchant-visible explanation fields."""
    errors: list[str] = []
    for key in (
        "status_label_ar",
        "what_happened_ar",
        "system_did_ar",
        "what_next_ar",
        "followup_line_ar",
        "merchant_action_needed_ar",
    ):
        val = _norm(expl.get(key))
        if val and not _merchant_safe(val):
            errors.append(key)
    return errors


__all__ = [
    "EXPLANATION_VERSION",
    "attach_merchant_explanation_v1",
    "build_merchant_explanation_v1",
    "sync_merchant_explanation_to_lifecycle_fields",
    "validate_merchant_explanation_merchant_safe",
]
