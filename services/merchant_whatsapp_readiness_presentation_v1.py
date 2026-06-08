# -*- coding: utf-8 -*-
"""
Merchant-facing readiness presentation — separates merchant setup from production sending.

Does not change readiness engine truth (whatsapp_ok, dimensions, connection states).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.merchant_whatsapp_journey_execution_v1 import (
    CTA_ACTION_SCROLL_SETTINGS,
    JOURNEY_STATUS_COMPLETED,
    compute_journey_status,
)
from services.merchant_whatsapp_mode_v1 import (
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
    normalize_whatsapp_mode,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_CHANGE_CTA_AR,
    journey_description_ar,
    journey_label_ar,
    normalize_whatsapp_onboarding_journey,
)

MERCHANT_SENDING_TITLE_AR = "حالة الإرسال"
MERCHANT_SENDING_STATUS_PREPARING_AR = "قيد التجهيز بواسطة CartFlow"
MERCHANT_SENDING_STATUS_READY_AR = "جاهزة للإرسال"

MERCHANT_COMPLETED_HEADLINE_AR = "تم إكمال إعداد واتساب"
MERCHANT_COMPLETED_SUBTEXT_AR = "تم حفظ رقم واتساب وتفعيل استرجاع الرسائل."
MERCHANT_NO_ACTION_AR = "لا يوجد إجراء مطلوب منك حالياً."
MERCHANT_CTA_EDIT_SETTINGS_AR = "تعديل إعدادات واتساب"
MERCHANT_PRODUCTION_TITLE_AR = "الإرسال قيد التجهيز"
MERCHANT_READINESS_BADGE_PREPARING_AR = "قيد التجهيز"

MERCHANT_SENDING_EXPLANATION_COMPLETED_AR = (
    "أكملت إعداداتك المطلوبة. سيبدأ الإرسال الفعلي عند اكتمال تجهيز مزود واتساب."
)
MERCHANT_SENDING_EXPLANATION_READY_AR = (
    "CartFlow جاهز لإرسال رسائل الاسترجاع عبر واتساب."
)

MERCHANT_JOURNEY_CURRENT_SECTION_TITLE_AR = "مسار واتساب الحالي"
MERCHANT_JOURNEY_CURRENT_CONTEXT_AR = (
    "هذا هو المسار الحالي المستخدم لمتابعة العملاء المترددين."
)
MERCHANT_JOURNEY_STATUS_SECTION_TITLE_AR = "حالة المسار"
MERCHANT_JOURNEY_STATUS_BADGE_COMPLETED_AR = "✓ مكتمل"
MERCHANT_JOURNEY_STATUS_DESC_COMPLETED_AR = (
    "تم إكمال إعداد هذا المسار ويمكنك تعديله في أي وقت."
)
MERCHANT_PATH_MANAGEMENT_SECTION_TITLE_AR = "إدارة المسار"
MERCHANT_MODE_LINE_AR: Mapping[str, str] = {
    WHATSAPP_MODE_CARTFLOW_MANAGED: "متابعة العملاء عبر واتساب CartFlow",
    WHATSAPP_MODE_MERCHANT_WHATSAPP: "متابعة العملاء عبر واتساب المتجر",
}
MERCHANT_SANDBOX_MODE_LINE_AR = "وضع التجربة (Sandbox)"
_EXPLANATION_MERCHANT_IN_PROGRESS_AR = (
    "أكمل خطوات مسار واتساب أولاً. بعدها يعمل CartFlow على تجهيز الإرسال."
)

_DIM_LABEL_AR: Mapping[str, str] = {
    "store_connected": "المتجر مربوط",
    "widget_ready": "الودجت جاهز",
    "plan_eligible": "الباقة مؤهلة",
}


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


def _dim_ready_map(readiness: Mapping[str, Any]) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for dim in readiness.get("readiness_dimensions") or []:
        key = str(dim.get("key") or "")
        if key:
            out[key] = bool(dim.get("ready"))
    return out


def _merchant_completed_checklist(
    store: Optional[Any],
    readiness: Mapping[str, Any],
) -> list[dict[str, str]]:
    dims = _dim_ready_map(readiness)
    rows: list[tuple[str, bool]] = [
        ("رقم واتساب محفوظ", _store_has_number(store)),
        ("استرجاع واتساب مفعل", _merchant_recovery_enabled(store)),
        (_DIM_LABEL_AR["store_connected"], dims.get("store_connected", False)),
        (_DIM_LABEL_AR["widget_ready"], dims.get("widget_ready", False)),
        (_DIM_LABEL_AR["plan_eligible"], dims.get("plan_eligible", False)),
    ]
    return [
        {"mark_ar": "✓" if ok else "◐", "label_ar": label}
        for label, ok in rows
    ]


def _production_sending_block(
    *,
    sending_ready: bool,
    journey_completed: bool,
) -> dict[str, Any]:
    if sending_ready:
        return {
            "title_ar": MERCHANT_SENDING_TITLE_AR,
            "status_ar": MERCHANT_SENDING_STATUS_READY_AR,
            "explanation_ar": MERCHANT_SENDING_EXPLANATION_READY_AR,
            "engine_ready": True,
        }

    if journey_completed:
        return {
            "title_ar": MERCHANT_SENDING_TITLE_AR,
            "status_ar": MERCHANT_SENDING_STATUS_PREPARING_AR,
            "explanation_ar": MERCHANT_SENDING_EXPLANATION_COMPLETED_AR,
            "engine_ready": False,
        }

    return {
        "title_ar": MERCHANT_SENDING_TITLE_AR,
        "status_ar": "قيد الإعداد",
        "explanation_ar": _EXPLANATION_MERCHANT_IN_PROGRESS_AR,
        "engine_ready": False,
    }


def _merchant_checklist_items(
    checklist: list[dict[str, Any]],
    *,
    sending_ready: bool,
    journey_completed: bool,
) -> list[dict[str, Any]]:
    if journey_completed:
        return []
    out: list[dict[str, Any]] = []
    for item in checklist:
        key = item.get("key")
        if key == "whatsapp_ready":
            if sending_ready:
                out.append(
                    {
                        **item,
                        "label_ar": "جاهزية الإرسال",
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
                        "label_ar": "جاهزية الإرسال",
                        "status_ar": "قيد الإعداد",
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


def _mode_line_ar(readiness: Mapping[str, Any], store: Optional[Any]) -> str:
    provider = (
        (getattr(store, "whatsapp_provider_mode", None) or "").strip().lower()
        if store
        else ""
    )
    if provider in ("sandbox", "test"):
        return MERCHANT_SANDBOX_MODE_LINE_AR
    mode = normalize_whatsapp_mode(readiness.get("whatsapp_mode"))
    return MERCHANT_MODE_LINE_AR.get(
        mode, str(readiness.get("whatsapp_mode_label_ar") or "")
    )


def _merchant_journey_visibility_block(
    *,
    journey_key: Optional[str],
    readiness: Mapping[str, Any],
    store: Optional[Any],
) -> dict[str, Any]:
    return {
        "active": True,
        "current_journey": {
            "title_ar": MERCHANT_JOURNEY_CURRENT_SECTION_TITLE_AR,
            "path_label_ar": journey_label_ar(journey_key) if journey_key else "",
            "path_description_ar": journey_description_ar(journey_key)
            if journey_key
            else "",
            "context_ar": MERCHANT_JOURNEY_CURRENT_CONTEXT_AR,
            "mode_line_ar": _mode_line_ar(readiness, store),
        },
        "journey_status": {
            "title_ar": MERCHANT_JOURNEY_STATUS_SECTION_TITLE_AR,
            "badge_ar": MERCHANT_JOURNEY_STATUS_BADGE_COMPLETED_AR,
            "description_ar": MERCHANT_JOURNEY_STATUS_DESC_COMPLETED_AR,
        },
        "path_management": {
            "title_ar": MERCHANT_PATH_MANAGEMENT_SECTION_TITLE_AR,
            "change_journey_cta_ar": JOURNEY_CHANGE_CTA_AR,
            "edit_settings_cta_ar": MERCHANT_CTA_EDIT_SETTINGS_AR,
            "no_action_ar": MERCHANT_NO_ACTION_AR,
        },
    }


def _apply_completed_journey_merchant_ux(
    out: dict[str, Any],
    store: Optional[Any],
    *,
    sending_ready: bool,
    journey_key: Optional[str],
) -> dict[str, Any]:
    checklist = _merchant_completed_checklist(store, out)
    out["merchant_completed_ux"] = {
        "active": True,
        "headline_ar": MERCHANT_COMPLETED_HEADLINE_AR,
        "subtext_ar": MERCHANT_COMPLETED_SUBTEXT_AR,
        "checklist_ar": checklist,
        "no_action_ar": MERCHANT_NO_ACTION_AR,
    }
    out["merchant_setup_completion"] = {
        "headline_ar": MERCHANT_COMPLETED_HEADLINE_AR,
        "subtext_ar": MERCHANT_COMPLETED_SUBTEXT_AR,
        "items_ar": [f"{i['mark_ar']} {i['label_ar']}" for i in checklist],
        "journey_status": JOURNEY_STATUS_COMPLETED,
    }
    out["merchant_journey_visibility"] = _merchant_journey_visibility_block(
        journey_key=journey_key,
        readiness=out,
        store=store,
    )
    if not sending_ready:
        out["merchant_readiness_badge_ar"] = MERCHANT_READINESS_BADGE_PREPARING_AR

    af = dict(out.get("action_first") or {})
    af["title_ar"] = MERCHANT_PRODUCTION_TITLE_AR
    af["next_action_ar"] = MERCHANT_NO_ACTION_AR
    af["primary_cta_label_ar"] = MERCHANT_CTA_EDIT_SETTINGS_AR
    af["expected_outcome_ar"] = MERCHANT_SENDING_EXPLANATION_COMPLETED_AR
    af["journey_completed"] = True
    cb = dict(af.get("cta_behavior") or {})
    cb["cta_action"] = CTA_ACTION_SCROLL_SETTINGS
    cb["highlight_fields"] = []
    cb["inline_guidance_ar"] = ""
    cb["placeholder_ar"] = ""
    cb["journey_completed"] = True
    cb["never_silent"] = True
    af["cta_behavior"] = cb
    out["action_first"] = af

    setup = dict(out.get("setup_checklist") or {})
    setup["headline_ar"] = MERCHANT_COMPLETED_HEADLINE_AR
    setup["checklist_ar"] = []
    setup["remaining_title_ar"] = ""
    setup["outcome_ar"] = MERCHANT_SENDING_EXPLANATION_COMPLETED_AR
    setup["merchant_presentation"] = True
    out["setup_checklist"] = setup
    return out


def apply_merchant_readiness_presentation(
    readiness: dict[str, Any],
    store: Optional[Any],
    *,
    onboarding_flags: Optional[Mapping[str, bool]] = None,
) -> dict[str, Any]:
    """Merchant API presentation layer — engine truth unchanged in dimensions."""
    out = dict(readiness)
    journey_key = normalize_whatsapp_onboarding_journey(
        getattr(store, "whatsapp_onboarding_journey", None) if store else None
    )
    journey_status = compute_journey_status(store, journey_key) if journey_key else None
    journey_completed = journey_status == JOURNEY_STATUS_COMPLETED
    sending_ready = _sending_ready_from_dimensions(out)

    out.pop("readiness_diagnostic_temp", None)

    if journey_completed:
        out = _apply_completed_journey_merchant_ux(
            out,
            store,
            sending_ready=sending_ready,
            journey_key=journey_key,
        )
    else:
        setup = dict(out.get("setup_checklist") or {})
        raw_checklist = list(setup.get("checklist_ar") or [])
        setup["checklist_ar"] = _merchant_checklist_items(
            raw_checklist,
            sending_ready=sending_ready,
            journey_completed=False,
        )
        setup["merchant_presentation"] = True
        out["setup_checklist"] = setup

    out["production_sending_readiness"] = _production_sending_block(
        sending_ready=sending_ready,
        journey_completed=journey_completed,
    )
    out["merchant_presentation_v2"] = True
    return out
