# -*- coding: utf-8 -*-
"""
WhatsApp Onboarding Journeys UI V1 — merchant-facing paths (no Meta/send/runtime).

Persists whatsapp_onboarding_journey on Store; enriches readiness card + admin visibility.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

JOURNEY_EXISTING_WHATSAPP_BUSINESS = "existing_whatsapp_business"
JOURNEY_NO_WHATSAPP_BUSINESS = "no_whatsapp_business"
JOURNEY_META_READY = "meta_ready"
JOURNEY_NEW_NUMBER = "new_number"

CANONICAL_ONBOARDING_JOURNEYS: frozenset[str] = frozenset(
    {
        JOURNEY_EXISTING_WHATSAPP_BUSINESS,
        JOURNEY_NO_WHATSAPP_BUSINESS,
        JOURNEY_META_READY,
        JOURNEY_NEW_NUMBER,
    }
)

JOURNEY_SELECTOR_TITLE_AR = "كيف تريد استخدام واتساب؟"
JOURNEY_CURRENT_PATH_LABEL_AR = "مسار واتساب الحالي:"
JOURNEY_CHANGE_CTA_AR = "تغيير مسار واتساب"
JOURNEY_CHANGE_SAFETY_AR = (
    "تغيير المسار لا يحذف إعداداتك الحالية. قد تحتاج فقط إلى إكمال خطوات مختلفة حسب المسار الجديد."
)
JOURNEY_OPTION_CURRENT_BADGE_AR = "المسار الحالي"

CTA_CHOOSE_JOURNEY_AR = "اختيار مسار واتساب"
CTA_CONTINUE_ACTIVATION_AR = "متابعة التفعيل"

CTA_ACTION_OPEN_JOURNEY_SELECTOR = "open_journey_selector"

_META_PLACEHOLDER_AR = (
    "الربط المتقدم قيد التجهيز. يمكنك حالياً استخدام CartFlow Managed للتشغيل التجريبي."
)

_JOURNEY_OPTIONS: tuple[dict[str, str], ...] = (
    {
        "key": JOURNEY_EXISTING_WHATSAPP_BUSINESS,
        "label_ar": "لدي واتساب أعمال",
        "description_ar": "أستخدم رقم واتساب أعمال حالياً وأريد ربطه مع CartFlow.",
    },
    {
        "key": JOURNEY_NO_WHATSAPP_BUSINESS,
        "label_ar": "لا أملك واتساب أعمال",
        "description_ar": "أحتاج خطوات بسيطة لإنشاء واتساب أعمال قبل التفعيل.",
    },
    {
        "key": JOURNEY_META_READY,
        "label_ar": "لدي إعدادات Meta جاهزة",
        "description_ar": "لدي إعدادات أعمال جاهزة وأريد متابعة الربط المتقدم.",
    },
    {
        "key": JOURNEY_NEW_NUMBER,
        "label_ar": "أريد رقماً جديداً",
        "description_ar": "أريد استخدام رقم جديد مخصص للاسترجاع.",
    },
)

_JOURNEY_GUIDANCE: Mapping[str, dict[str, Any]] = {
    JOURNEY_EXISTING_WHATSAPP_BUSINESS: {
        "steps_ar": [
            "أدخل رقم واتساب أعمال.",
            "تأكد أن الرقم يستقبل الرسائل.",
            "فعّل استرجاع واتساب.",
            "سيبدأ CartFlow بإرسال رسائل الاسترجاع عند الجاهزية.",
        ],
        "next_action_ar": "أدخل رقم واتساب أعمال ثم فعّل استرجاع واتساب.",
        "expected_outcome_ar": (
            "سيبدأ CartFlow بإرسال رسائل الاسترجاع للعملاء عند اكتمال الجاهزية."
        ),
        "placeholder_ar": "",
    },
    JOURNEY_NO_WHATSAPP_BUSINESS: {
        "steps_ar": [
            "أنشئ حساب واتساب أعمال.",
            "خصص رقماً للمتجر.",
            "عد إلى CartFlow وأدخل الرقم.",
            "فعّل استرجاع واتساب.",
        ],
        "next_action_ar": "أنشئ واتساب أعمال ثم أدخل الرقم داخل CartFlow.",
        "expected_outcome_ar": (
            "سيبدأ CartFlow بإرسال رسائل الاسترجاع للعملاء بعد إدخال الرقم والتفعيل."
        ),
        "placeholder_ar": "",
    },
    JOURNEY_META_READY: {
        "steps_ar": [
            "جهّز معلومات أعمالك.",
            "تابع الربط المتقدم عند توفره.",
            "CartFlow سيعرض حالة الجاهزية عند الربط.",
        ],
        "next_action_ar": "راجع خطوات الربط المتقدم عند توفره.",
        "expected_outcome_ar": "ستظهر حالة الجاهزية في CartFlow عند اكتمال الربط.",
        "placeholder_ar": _META_PLACEHOLDER_AR,
    },
    JOURNEY_NEW_NUMBER: {
        "steps_ar": [
            "اختر رقماً مخصصاً للاسترجاع.",
            "فعّل عليه واتساب أعمال.",
            "أدخل الرقم داخل CartFlow.",
            "فعّل استرجاع واتساب.",
        ],
        "next_action_ar": "فعّل واتساب أعمال على الرقم الجديد ثم أدخله هنا.",
        "expected_outcome_ar": (
            "سيبدأ CartFlow بإرسال رسائل الاسترجاع للعملاء بعد إدخال الرقم والتفعيل."
        ),
        "placeholder_ar": "",
    },
}

_schema_once = False


def normalize_whatsapp_onboarding_journey(raw: Any) -> Optional[str]:
    key = (raw or "").strip().lower() if raw is not None else ""
    if not key:
        return None
    return key if key in CANONICAL_ONBOARDING_JOURNEYS else None


def journey_label_ar(key: Optional[str]) -> str:
    if not key:
        return ""
    for opt in _JOURNEY_OPTIONS:
        if opt["key"] == key:
            return opt["label_ar"]
    return key


def journey_description_ar(key: Optional[str]) -> str:
    if not key:
        return ""
    for opt in _JOURNEY_OPTIONS:
        if opt["key"] == key:
            return (opt.get("description_ar") or "").strip()
    return ""


def journey_guidance_for_key(key: Optional[str]) -> dict[str, Any]:
    if not key or key not in _JOURNEY_GUIDANCE:
        return {
            "steps_ar": [],
            "next_action_ar": "",
            "expected_outcome_ar": "",
            "placeholder_ar": "",
        }
    g = dict(_JOURNEY_GUIDANCE[key])
    g["steps_ar"] = list(g.get("steps_ar") or [])
    return g


def onboarding_journey_options_for_api() -> list[dict[str, str]]:
    return [dict(o) for o in _JOURNEY_OPTIONS]


def onboarding_journeys_ui_block(store: Optional[Any]) -> dict[str, Any]:
    """Merchant UI block — selector + guidance."""
    selected = normalize_whatsapp_onboarding_journey(
        getattr(store, "whatsapp_onboarding_journey", None) if store else None
    )
    guidance = journey_guidance_for_key(selected) if selected else None
    return {
        "title_ar": JOURNEY_SELECTOR_TITLE_AR,
        "selected_key": selected,
        "selected_label_ar": journey_label_ar(selected) if selected else "",
        "selected_description_ar": journey_description_ar(selected) if selected else "",
        "options": onboarding_journey_options_for_api(),
        "guidance": guidance,
        "journey_required": selected is None,
        "current_path_label_ar": JOURNEY_CURRENT_PATH_LABEL_AR,
        "change_journey_cta_ar": JOURNEY_CHANGE_CTA_AR,
        "change_journey_safety_ar": JOURNEY_CHANGE_SAFETY_AR,
        "option_current_badge_ar": JOURNEY_OPTION_CURRENT_BADGE_AR,
    }


def onboarding_journey_fields_for_api(store: Optional[Any]) -> dict[str, Any]:
    from services.merchant_whatsapp_journey_execution_v1 import (  # noqa: PLC0415
        journey_execution_fields_for_api,
    )

    block = onboarding_journeys_ui_block(store)
    payload = {
        "whatsapp_onboarding_journey": block["selected_key"],
        "whatsapp_onboarding_journey_ar": block["selected_label_ar"] or None,
        "whatsapp_onboarding_journeys": block,
    }
    payload.update(journey_execution_fields_for_api(store))
    return payload


def enrich_readiness_with_onboarding_journey(
    readiness: dict[str, Any],
    store: Optional[Any],
) -> dict[str, Any]:
    """Enrich connection readiness payload — does not change engine state logic."""
    out = dict(readiness)
    out["whatsapp_onboarding_journeys"] = onboarding_journeys_ui_block(store)
    from services.merchant_whatsapp_journey_execution_v1 import (  # noqa: PLC0415
        journey_execution_fields_for_api,
        apply_journey_execution_to_readiness,
    )

    out.update(journey_execution_fields_for_api(store))
    return apply_journey_execution_to_readiness(out, store)


def apply_whatsapp_onboarding_journey_from_body(
    row: Any,
    body: Mapping[str, Any],
) -> None:
    if "whatsapp_onboarding_journey" not in body:
        return
    raw = body.get("whatsapp_onboarding_journey")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        from services.merchant_whatsapp_journey_execution_v1 import (  # noqa: PLC0415
            on_journey_selection_changed,
        )

        on_journey_selection_changed(row, None)
        row.whatsapp_onboarding_journey = None
        row.whatsapp_onboarding_journey_status = None
        return
    normalized = normalize_whatsapp_onboarding_journey(raw)
    from services.merchant_whatsapp_journey_execution_v1 import (  # noqa: PLC0415
        JOURNEY_STATUS_NOT_STARTED,
        on_journey_selection_changed,
    )

    on_journey_selection_changed(row, normalized)
    row.whatsapp_onboarding_journey = normalized
    if getattr(row, "whatsapp_onboarding_journey_status", None) is None:
        row.whatsapp_onboarding_journey_status = JOURNEY_STATUS_NOT_STARTED


def ensure_whatsapp_onboarding_journey_column(db: Any) -> None:
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import SQLAlchemyError

    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        cols = {c["name"] for c in insp.get_columns("stores")}
        if "whatsapp_onboarding_journey" in cols:
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        if dialect in ("postgresql", "postgres"):
            stmt = (
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                "whatsapp_onboarding_journey VARCHAR(64)"
            )
        else:
            stmt = (
                "ALTER TABLE stores ADD COLUMN whatsapp_onboarding_journey "
                "VARCHAR(64)"
            )
        db.session.execute(text(stmt))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


def ensure_whatsapp_onboarding_journey_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    ensure_whatsapp_onboarding_journey_column(db)
    _schema_once = True


def reset_whatsapp_onboarding_journey_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False
