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
from services.merchant_whatsapp_connection_readiness_v1 import (
    CONNECTION_STATE_CONNECTED,
    READINESS_OVERALL_READY,
)
from services.merchant_whatsapp_mode_v1 import (
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
    normalize_whatsapp_mode,
)
from services.merchant_whatsapp_onboarding_journeys_v1 import (
    JOURNEY_CHANGE_CTA_AR,
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
    journey_description_ar,
    journey_label_ar,
    normalize_whatsapp_onboarding_journey,
)

MERCHANT_SENDING_TITLE_AR = "حالة الإرسال"
MERCHANT_SENDING_STATUS_PREPARING_AR = "قيد التجهيز بواسطة CartFlow"
MERCHANT_SENDING_STATUS_READY_AR = "جاهزة للإرسال"
MERCHANT_SENDING_STATUS_META_NOT_LINKED_AR = "واتساب لم يُربط بمنصة الأعمال بعد"

MERCHANT_COMPLETED_HEADLINE_AR = "تم إكمال إعداد واتساب"
MERCHANT_COMPLETED_SUBTEXT_AR = "تم حفظ رقم واتساب وتفعيل استرجاع الرسائل."
MERCHANT_NO_ACTION_AR = "لا يوجد إجراء مطلوب منك حالياً."
MERCHANT_META_PAIRING_ACTION_TITLE_AR = "إجراء مطلوب: ربط منصة الأعمال"
MERCHANT_META_PAIRING_INSTRUCTION_AR = (
    "افتح تطبيق WhatsApp Business → Settings → Account → Business Platform → "
    "Connect to the Business Platform"
)
MERCHANT_CARTFLOW_PROVISIONING_NEXT_AR = (
    "جاري تجهيز قناة الإرسال للإنتاج بواسطة CartFlow."
)

PENDING_REASON_META_PAIRING_REQUIRED = "meta_pairing_required"
PENDING_REASON_CARTFLOW_PROVISIONING = "cartflow_provisioning"
MERCHANT_CTA_EDIT_SETTINGS_AR = "تعديل إعدادات واتساب"
MERCHANT_PRODUCTION_TITLE_AR = "الإرسال قيد التجهيز"
MERCHANT_READINESS_BADGE_PREPARING_AR = "قيد التجهيز"

MERCHANT_SENDING_EXPLANATION_COMPLETED_AR = (
    "أكملت إعداداتك المطلوبة. سيبدأ الإرسال الفعلي عند اكتمال تجهيز مزود واتساب."
)
MERCHANT_SENDING_EXPLANATION_META_PAIRING_AR = (
    "يلزم إكمال ربط WhatsApp Business Platform قبل الإرسال الفعلي."
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


def _merchant_production_sending_ready(
    readiness: Mapping[str, Any],
    *,
    dims_ready: bool,
) -> bool:
    """Presentation-only: dims may pass while connection/readiness overall still block send."""
    if not dims_ready:
        return False
    return (
        readiness.get("connection_state") == CONNECTION_STATE_CONNECTED
        and readiness.get("readiness_overall") == READINESS_OVERALL_READY
    )


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


def _existing_whatsapp_business_needs_meta_pairing(
    store: Optional[Any],
    journey_key: Optional[str],
) -> bool:
    """Merchant-owned WhatsApp path: pairing is on the merchant, not platform sandbox."""
    if journey_key != JOURNEY_EXISTING_WHATSAPP_BUSINESS:
        return False
    return _store_has_number(store) and _merchant_recovery_enabled(store)


def _cartflow_operator_provisioning_pending(
    onboarding_flags: Optional[Mapping[str, bool]],
) -> bool:
    """True when CartFlow/operator must provision platform credentials (not merchant Meta)."""
    flags = dict(onboarding_flags or {})
    return not flags.get("whatsapp_configured")


def _resolve_sending_pending_reason(
    *,
    sending_ready: bool,
    journey_completed: bool,
    onboarding_flags: Optional[Mapping[str, bool]],
    journey_key: Optional[str] = None,
    store: Optional[Any] = None,
) -> Optional[str]:
    if sending_ready or not journey_completed:
        return None
    if _existing_whatsapp_business_needs_meta_pairing(store, journey_key):
        return PENDING_REASON_META_PAIRING_REQUIRED
    if _cartflow_operator_provisioning_pending(onboarding_flags):
        return PENDING_REASON_CARTFLOW_PROVISIONING
    return PENDING_REASON_META_PAIRING_REQUIRED


def _is_meta_pairing_pending_reason(pending_reason: Optional[str]) -> bool:
    return pending_reason == PENDING_REASON_META_PAIRING_REQUIRED


def _production_sending_block(
    *,
    sending_ready: bool,
    journey_completed: bool,
    pending_reason: Optional[str] = None,
) -> dict[str, Any]:
    if sending_ready:
        return {
            "title_ar": MERCHANT_SENDING_TITLE_AR,
            "status_ar": MERCHANT_SENDING_STATUS_READY_AR,
            "explanation_ar": MERCHANT_SENDING_EXPLANATION_READY_AR,
            "meta_pairing_instruction_ar": "",
            "pending_reason": None,
            "merchant_action_required": False,
            "engine_ready": True,
        }

    if journey_completed:
        if _is_meta_pairing_pending_reason(pending_reason):
            return {
                "title_ar": MERCHANT_SENDING_TITLE_AR,
                "status_ar": MERCHANT_SENDING_STATUS_META_NOT_LINKED_AR,
                "explanation_ar": MERCHANT_SENDING_EXPLANATION_META_PAIRING_AR,
                "meta_pairing_instruction_ar": MERCHANT_META_PAIRING_INSTRUCTION_AR,
                "pending_reason": pending_reason,
                "merchant_action_required": True,
                "engine_ready": False,
            }
        return {
            "title_ar": MERCHANT_SENDING_TITLE_AR,
            "status_ar": MERCHANT_SENDING_STATUS_PREPARING_AR,
            "explanation_ar": MERCHANT_SENDING_EXPLANATION_COMPLETED_AR,
            "meta_pairing_instruction_ar": "",
            "pending_reason": PENDING_REASON_CARTFLOW_PROVISIONING,
            "merchant_action_required": False,
            "engine_ready": False,
        }

    return {
        "title_ar": MERCHANT_SENDING_TITLE_AR,
        "status_ar": "قيد الإعداد",
        "explanation_ar": _EXPLANATION_MERCHANT_IN_PROGRESS_AR,
        "meta_pairing_instruction_ar": "",
        "pending_reason": None,
        "merchant_action_required": False,
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
    no_action_ar: str = "",
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
            "no_action_ar": no_action_ar,
        },
    }


def _completed_journey_action_first_copy(
    *,
    sending_ready: bool,
    pending_reason: Optional[str],
) -> tuple[str, str, str]:
    """Return (title_ar, next_action_ar, expected_outcome_ar) for completed journey."""
    if sending_ready:
        return (
            MERCHANT_PRODUCTION_TITLE_AR,
            MERCHANT_NO_ACTION_AR,
            MERCHANT_SENDING_EXPLANATION_READY_AR,
        )
    if pending_reason == PENDING_REASON_META_PAIRING_REQUIRED:
        return (
            MERCHANT_META_PAIRING_ACTION_TITLE_AR,
            MERCHANT_META_PAIRING_INSTRUCTION_AR,
            MERCHANT_SENDING_EXPLANATION_META_PAIRING_AR,
        )
    return (
        MERCHANT_PRODUCTION_TITLE_AR,
        MERCHANT_CARTFLOW_PROVISIONING_NEXT_AR,
        MERCHANT_SENDING_EXPLANATION_COMPLETED_AR,
    )


def _apply_completed_journey_merchant_ux(
    out: dict[str, Any],
    store: Optional[Any],
    *,
    sending_ready: bool,
    journey_key: Optional[str],
    pending_reason: Optional[str],
) -> dict[str, Any]:
    no_action_ar = MERCHANT_NO_ACTION_AR if sending_ready else ""
    checklist = _merchant_completed_checklist(store, out)
    out["merchant_completed_ux"] = {
        "active": True,
        "headline_ar": MERCHANT_COMPLETED_HEADLINE_AR,
        "subtext_ar": MERCHANT_COMPLETED_SUBTEXT_AR,
        "checklist_ar": checklist,
        "no_action_ar": no_action_ar,
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
        no_action_ar=no_action_ar,
    )
    if not sending_ready:
        out["merchant_readiness_badge_ar"] = MERCHANT_READINESS_BADGE_PREPARING_AR

    title_ar, next_action_ar, expected_outcome_ar = _completed_journey_action_first_copy(
        sending_ready=sending_ready,
        pending_reason=pending_reason,
    )
    af = dict(out.get("action_first") or {})
    af["title_ar"] = title_ar
    af["next_action_ar"] = next_action_ar
    af["primary_cta_label_ar"] = MERCHANT_CTA_EDIT_SETTINGS_AR
    af["expected_outcome_ar"] = expected_outcome_ar
    af["journey_completed"] = True
    af["merchant_action_required"] = _is_meta_pairing_pending_reason(pending_reason)
    cb = dict(af.get("cta_behavior") or {})
    cb["cta_action"] = CTA_ACTION_SCROLL_SETTINGS
    cb["highlight_fields"] = []
    cb["inline_guidance_ar"] = (
        MERCHANT_META_PAIRING_INSTRUCTION_AR
        if _is_meta_pairing_pending_reason(pending_reason)
        else ""
    )
    cb["placeholder_ar"] = ""
    cb["journey_completed"] = True
    cb["never_silent"] = True
    cb["merchant_action_required"] = af["merchant_action_required"]
    af["cta_behavior"] = cb
    out["action_first"] = af

    setup = dict(out.get("setup_checklist") or {})
    setup["headline_ar"] = MERCHANT_COMPLETED_HEADLINE_AR
    setup["checklist_ar"] = []
    setup["remaining_title_ar"] = ""
    setup["outcome_ar"] = expected_outcome_ar
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
    dims_ready = _sending_ready_from_dimensions(out)
    sending_ready = _merchant_production_sending_ready(out, dims_ready=dims_ready)
    pending_reason = _resolve_sending_pending_reason(
        sending_ready=sending_ready,
        journey_completed=journey_completed,
        onboarding_flags=onboarding_flags,
        journey_key=journey_key,
        store=store,
    )

    out.pop("readiness_diagnostic_temp", None)

    if journey_completed:
        out = _apply_completed_journey_merchant_ux(
            out,
            store,
            sending_ready=sending_ready,
            journey_key=journey_key,
            pending_reason=pending_reason,
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
        pending_reason=pending_reason,
    )
    out["merchant_presentation_v2"] = True
    return out
