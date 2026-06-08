# -*- coding: utf-8 -*-
"""
Merchant-facing readiness presentation — separates merchant setup from production sending.

Does not change readiness engine truth (whatsapp_ok, dimensions, connection states).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.merchant_whatsapp_journey_execution_v1 import (
    JOURNEY_STATUS_COMPLETED,
    compute_journey_status,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    normalize_whatsapp_onboarding_journey,
)

MERCHANT_SENDING_READINESS_LABEL_AR = "جاهزية الإرسال"
MERCHANT_SENDING_STATUS_PENDING_AR = "قيد الإعداد"
MERCHANT_SENDING_STATUS_CARTFLOW_SETUP_AR = "جاري إعداد الاتصال بواسطة CartFlow"
MERCHANT_SENDING_STATUS_READY_AR = "جاهزة للإرسال"

MERCHANT_SETUP_COMPLETION_HEADLINE_AR = "✓ تم إكمال مسار واتساب"

_EXPLANATION_JOURNEY_DONE_SANDBOX_AR = (
    "أكملت إعداداتك المطلوبة. الإرسال الإنتاجي غير مفعل حالياً. "
    "سيتم تفعيل الإرسال عند اكتمال إعداد مزود واتساب."
)
_EXPLANATION_JOURNEY_DONE_PRODUCTION_AR = (
    "أكملت إعداداتك المطلوبة. يعمل CartFlow على تجهيز الاتصال للإرسال الفعلي."
)
_EXPLANATION_MERCHANT_IN_PROGRESS_AR = (
    "أكمل خطوات مسار واتساب أولاً. بعدها يعمل CartFlow على تجهيز الإرسال."
)


def _store_has_number(store: Optional[Any]) -> bool:
    if store is None:
        return False
    return bool((getattr(store, "store_whatsapp_number", None) or "").strip())


def _merchant_recovery_enabled(store: Optional[Any]) -> bool:
    if store is None:
        return False
    raw = getattr(store, "whatsapp_recovery_enabled", None)
    return True if raw is None else bool(raw)


def _sending_ready_from_dimensions(readiness: Mapping[str, Any]) -> bool:
    for dim in readiness.get("readiness_dimensions") or []:
        if dim.get("key") == "whatsapp_ready":
            return bool(dim.get("ready"))
    return False


def _merchant_setup_completion_items(store: Optional[Any]) -> list[str]:
    items: list[str] = []
    if _store_has_number(store):
        items.append("✓ رقم واتساب محفوظ")
    if _merchant_recovery_enabled(store):
        items.append("✓ استرجاع واتساب مفعل")
    return items


def _production_sending_block(
    *,
    sending_ready: bool,
    journey_completed: bool,
    sandbox: bool,
) -> dict[str, Any]:
    if sending_ready:
        return {
            "title_ar": "حالة الإرسال الحالية",
            "status_ar": MERCHANT_SENDING_STATUS_READY_AR,
            "label_ar": MERCHANT_SENDING_READINESS_LABEL_AR,
            "explanation_ar": "CartFlow جاهز لإرسال رسائل الاسترجاع عبر واتساب.",
            "engine_ready": True,
        }

    if journey_completed:
        status_ar = (
            MERCHANT_SENDING_STATUS_CARTFLOW_SETUP_AR
            if sandbox
            else MERCHANT_SENDING_STATUS_PENDING_AR
        )
        explanation = (
            _EXPLANATION_JOURNEY_DONE_SANDBOX_AR
            if sandbox
            else _EXPLANATION_JOURNEY_DONE_PRODUCTION_AR
        )
    else:
        status_ar = MERCHANT_SENDING_STATUS_PENDING_AR
        explanation = _EXPLANATION_MERCHANT_IN_PROGRESS_AR

    return {
        "title_ar": "حالة الإرسال الحالية",
        "status_ar": status_ar,
        "label_ar": MERCHANT_SENDING_READINESS_LABEL_AR,
        "explanation_ar": explanation,
        "engine_ready": False,
    }


def _merchant_checklist_items(
    checklist: list[dict[str, Any]],
    *,
    sending_ready: bool,
    journey_completed: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in checklist:
        key = item.get("key")
        if key == "whatsapp_ready":
            if journey_completed and not sending_ready:
                continue
            if sending_ready:
                out.append(
                    {
                        **item,
                        "label_ar": MERCHANT_SENDING_READINESS_LABEL_AR,
                        "status_ar": MERCHANT_SENDING_STATUS_READY_AR,
                        "mark_ar": "✓",
                        "complete": True,
                        "merchant_presentation": True,
                        "engine_key": "whatsapp_ready",
                    }
                )
            else:
                out.append(
                    {
                        **item,
                        "label_ar": MERCHANT_SENDING_READINESS_LABEL_AR,
                        "status_ar": MERCHANT_SENDING_STATUS_PENDING_AR,
                        "mark_ar": "◐",
                        "complete": False,
                        "merchant_presentation": True,
                        "engine_key": "whatsapp_ready",
                        "engine_ready": False,
                    }
                )
            continue
        out.append(dict(item))
    return out


def apply_merchant_readiness_presentation(
    readiness: dict[str, Any],
    store: Optional[Any],
    *,
    onboarding_flags: Optional[Mapping[str, bool]] = None,
) -> dict[str, Any]:
    """Merchant API presentation layer — engine truth unchanged in dimensions/diagnostic."""
    out = dict(readiness)
    flags = dict(onboarding_flags or {})
    sandbox = bool(flags.get("sandbox_mode_active"))
    journey_key = normalize_whatsapp_onboarding_journey(
        getattr(store, "whatsapp_onboarding_journey", None) if store else None
    )
    journey_status = compute_journey_status(store, journey_key) if journey_key else None
    journey_completed = journey_status == JOURNEY_STATUS_COMPLETED
    sending_ready = _sending_ready_from_dimensions(out)

    setup = dict(out.get("setup_checklist") or {})
    raw_checklist = list(setup.get("checklist_ar") or [])
    merchant_checklist = _merchant_checklist_items(
        raw_checklist,
        sending_ready=sending_ready,
        journey_completed=journey_completed,
    )
    setup["checklist_ar"] = merchant_checklist
    setup["merchant_presentation"] = True
    if journey_completed:
        setup["remaining_title_ar"] = "متطلبات التشغيل الإضافية:"
    out["setup_checklist"] = setup

    if journey_completed:
        out["merchant_setup_completion"] = {
            "headline_ar": MERCHANT_SETUP_COMPLETION_HEADLINE_AR,
            "items_ar": _merchant_setup_completion_items(store),
            "journey_status": journey_status,
        }

    out["production_sending_readiness"] = _production_sending_block(
        sending_ready=sending_ready,
        journey_completed=journey_completed,
        sandbox=sandbox,
    )
    return out
