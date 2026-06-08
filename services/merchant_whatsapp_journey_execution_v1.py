# -*- coding: utf-8 -*-
"""
WhatsApp Journey Execution Layer V1 — actionable merchant paths (no Meta/send/runtime).

Converts onboarding journey selection into journey-specific CTAs, progress states,
and readiness language. Reserves hooks for future Meta connection (not implemented).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.merchant_whatsapp_onboarding_journeys_v1 import (
    CTA_CHOOSE_JOURNEY_AR,
    JOURNEY_EXISTING_WHATSAPP_BUSINESS,
    JOURNEY_META_READY,
    JOURNEY_NEW_NUMBER,
    JOURNEY_NO_WHATSAPP_BUSINESS,
    JOURNEY_SELECTOR_TITLE_AR,
    CTA_ACTION_OPEN_JOURNEY_SELECTOR,
    journey_label_ar,
    normalize_whatsapp_onboarding_journey,
    onboarding_journey_options_for_api,
)

JOURNEY_STATUS_NOT_STARTED = "not_started"
JOURNEY_STATUS_IN_PROGRESS = "in_progress"
JOURNEY_STATUS_COMPLETED = "completed"

CANONICAL_JOURNEY_STATUSES: frozenset[str] = frozenset(
    {
        JOURNEY_STATUS_NOT_STARTED,
        JOURNEY_STATUS_IN_PROGRESS,
        JOURNEY_STATUS_COMPLETED,
    }
)

CTA_CONTINUE_ACTIVATION_AR = "متابعة التفعيل"
CTA_CREATE_WA_BUSINESS_AR = "إنشاء واتساب أعمال"
CTA_PREPARE_NEW_NUMBER_AR = "تجهيز رقم جديد"
CTA_META_ADVANCED_AR = "الربط المتقدم"
CTA_REVIEW_SETTINGS_AR = "مراجعة الإعدادات"

JOURNEY_COMPLETED_BADGE_AR = "✓ تم إكمال هذا المسار"
JOURNEY_COMPLETED_HEADLINE_AR = "✓ تم إكمال مسار واتساب"
JOURNEY_READINESS_SEPARATION_NOTE_AR = (
    "جاهزية الإنتاج تُعرض أدناه بشكل منفصل عن مسار واتساب."
)

CTA_ACTION_SCROLL_SETTINGS = "scroll_settings"
CTA_ACTION_OPEN_WA_BUSINESS_GUIDE = "open_whatsapp_business_guide"
CTA_ACTION_PREPARE_NEW_NUMBER = "prepare_new_number"
CTA_ACTION_OPEN_META_PLACEHOLDER = "open_meta_advanced_placeholder"

WA_BUSINESS_OFFICIAL_URL = "https://business.whatsapp.com/"

_META_PLACEHOLDER_PRIMARY_AR = "الربط المتقدم قيد التجهيز حالياً."
_META_PLACEHOLDER_SECONDARY_AR = (
    "يمكنك حالياً استخدام CartFlow Managed للتشغيل التجريبي."
)

_STATUS_LABEL_AR: Mapping[str, str] = {
    JOURNEY_STATUS_NOT_STARTED: "لم يبدأ",
    JOURNEY_STATUS_IN_PROGRESS: "قيد التنفيذ",
    JOURNEY_STATUS_COMPLETED: "مكتمل",
}

_STATUS_BADGE_CLASS: Mapping[str, str] = {
    JOURNEY_STATUS_NOT_STARTED: "is-not-started",
    JOURNEY_STATUS_IN_PROGRESS: "is-in-progress",
    JOURNEY_STATUS_COMPLETED: "is-completed",
}

# Part H — reserved for future Meta phases (not implemented)
FUTURE_META_CONNECTION_HOOKS: dict[str, dict[str, Any]] = {
    "embedded_signup": {"status": "reserved", "implemented": False},
    "meta_connection": {"status": "reserved", "implemented": False},
    "business_verification": {"status": "reserved", "implemented": False},
    "phone_verification": {"status": "reserved", "implemented": False},
}

_JOURNEY_EXECUTION: Mapping[str, dict[str, Any]] = {
    JOURNEY_EXISTING_WHATSAPP_BUSINESS: {
        "primary_cta_ar": CTA_CONTINUE_ACTIVATION_AR,
        "cta_action": CTA_ACTION_SCROLL_SETTINGS,
        "highlight_fields": ["store_number", "recovery_enabled"],
        "inline_guidance_ar": "أدخل رقم واتساب الأعمال ثم فعّل استرجاع واتساب واحفظ الإعدادات.",
        "steps_ar": [
            "أدخل رقم واتساب الأعمال.",
            "فعّل استرجاع واتساب.",
            "احفظ الإعدادات.",
        ],
        "remaining_step_ar": "إدخال الرقم وتفعيل الاسترجاع",
        "expected_outcome_ar": (
            "سيصبح CartFlow جاهزاً لاستخدام هذا الرقم عند اكتمال الربط الإنتاجي."
        ),
        "explanation_ar": "",
        "external_url": "",
        "placeholder_ar": "",
        "secondary_note_ar": "",
    },
    JOURNEY_NO_WHATSAPP_BUSINESS: {
        "primary_cta_ar": CTA_CREATE_WA_BUSINESS_AR,
        "cta_action": CTA_ACTION_OPEN_WA_BUSINESS_GUIDE,
        "highlight_fields": [],
        "inline_guidance_ar": "يلزم وجود واتساب أعمال لاستخدام استرجاع واتساب.",
        "steps_ar": [
            "أنشئ حساب واتساب أعمال من الرابط الرسمي.",
            "خصص رقماً للمتجر.",
            "عد إلى CartFlow وأدخل الرقم.",
            "فعّل استرجاع واتساب.",
        ],
        "remaining_step_ar": "إنشاء واتساب أعمال",
        "expected_outcome_ar": (
            "بعد إنشاء واتساب أعمال يمكنك العودة إلى CartFlow لإكمال التفعيل."
        ),
        "explanation_ar": "يلزم وجود واتساب أعمال لاستخدام استرجاع واتساب.",
        "external_url": WA_BUSINESS_OFFICIAL_URL,
        "placeholder_ar": "",
        "secondary_note_ar": "",
    },
    JOURNEY_NEW_NUMBER: {
        "primary_cta_ar": CTA_PREPARE_NEW_NUMBER_AR,
        "cta_action": CTA_ACTION_PREPARE_NEW_NUMBER,
        "highlight_fields": ["store_number", "recovery_enabled"],
        "inline_guidance_ar": (
            "جهّز رقماً مخصصاً للاسترجاع، فعّل عليه واتساب أعمال، ثم أدخله هنا."
        ),
        "steps_ar": [
            "جهّز رقماً مخصصاً للاسترجاع.",
            "فعّل عليه واتساب أعمال.",
            "عد إلى CartFlow وأدخل الرقم.",
        ],
        "remaining_step_ar": "تجهيز الرقم الجديد",
        "expected_outcome_ar": "سيتم استخدام الرقم لرسائل الاسترجاع.",
        "explanation_ar": "",
        "external_url": "",
        "placeholder_ar": "",
        "secondary_note_ar": "",
    },
    JOURNEY_META_READY: {
        "primary_cta_ar": CTA_META_ADVANCED_AR,
        "cta_action": CTA_ACTION_OPEN_META_PLACEHOLDER,
        "highlight_fields": [],
        "inline_guidance_ar": _META_PLACEHOLDER_PRIMARY_AR,
        "steps_ar": [
            "جهّز معلومات أعمالك.",
            "تابع الربط المتقدم عند توفره.",
            "CartFlow سيعرض حالة الجاهزية عند الربط.",
        ],
        "remaining_step_ar": "الربط المتقدم",
        "expected_outcome_ar": "ستظهر حالة الجاهزية في CartFlow عند اكتمال الربط.",
        "explanation_ar": "",
        "external_url": "",
        "placeholder_ar": _META_PLACEHOLDER_PRIMARY_AR,
        "secondary_note_ar": _META_PLACEHOLDER_SECONDARY_AR,
    },
}

_schema_once = False


def normalize_journey_status(raw: Any) -> Optional[str]:
    key = (raw or "").strip().lower() if raw is not None else ""
    if not key:
        return None
    return key if key in CANONICAL_JOURNEY_STATUSES else None


def journey_status_label_ar(status: Optional[str]) -> str:
    if not status:
        return ""
    return _STATUS_LABEL_AR.get(status, status)


def _store_has_number(store: Optional[Any]) -> bool:
    if store is None:
        return False
    return bool((getattr(store, "store_whatsapp_number", None) or "").strip())


def _store_recovery_enabled(store: Optional[Any]) -> bool:
    if store is None:
        return True
    raw = getattr(store, "whatsapp_recovery_enabled", None)
    return True if raw is None else bool(raw)


def compute_journey_status(
    store: Optional[Any],
    journey_key: Optional[str],
) -> Optional[str]:
    """Derive journey progress from store fields + persisted marker."""
    if not journey_key:
        return None

    has_number = _store_has_number(store)
    recovery_on = _store_recovery_enabled(store)
    stored = normalize_journey_status(
        getattr(store, "whatsapp_onboarding_journey_status", None) if store else None
    )

    if journey_key == JOURNEY_META_READY:
        return JOURNEY_STATUS_COMPLETED

    if journey_key == JOURNEY_NO_WHATSAPP_BUSINESS:
        if has_number and recovery_on:
            return JOURNEY_STATUS_COMPLETED
        if stored == JOURNEY_STATUS_IN_PROGRESS:
            return JOURNEY_STATUS_IN_PROGRESS
        return JOURNEY_STATUS_NOT_STARTED

    if journey_key in (
        JOURNEY_EXISTING_WHATSAPP_BUSINESS,
        JOURNEY_NEW_NUMBER,
    ):
        if has_number and recovery_on:
            return JOURNEY_STATUS_COMPLETED

    if journey_key == JOURNEY_EXISTING_WHATSAPP_BUSINESS:
        if has_number or recovery_on or stored == JOURNEY_STATUS_IN_PROGRESS:
            return JOURNEY_STATUS_IN_PROGRESS
        return JOURNEY_STATUS_NOT_STARTED

    if journey_key == JOURNEY_NEW_NUMBER:
        if has_number or stored == JOURNEY_STATUS_IN_PROGRESS:
            return JOURNEY_STATUS_IN_PROGRESS
        return JOURNEY_STATUS_NOT_STARTED

    return JOURNEY_STATUS_NOT_STARTED


def sync_journey_status_on_store(store: Any) -> None:
    """Persist computed status when store settings change."""
    journey_key = normalize_whatsapp_onboarding_journey(
        getattr(store, "whatsapp_onboarding_journey", None)
    )
    if not journey_key:
        store.whatsapp_onboarding_journey_status = None
        return
    store.whatsapp_onboarding_journey_status = compute_journey_status(store, journey_key)


def _journey_completion_summary_ar(
    store: Optional[Any],
    journey_key: str,
) -> list[str]:
    items: list[str] = []
    if journey_key == JOURNEY_META_READY:
        items.append("تم اختيار مسار الربط المتقدم")
        return items
    if _store_has_number(store):
        items.append("رقم واتساب محفوظ")
    if _store_recovery_enabled(store):
        items.append("استرجاع واتساب مفعل")
    return items


def build_journey_completion_ui(
    store: Optional[Any],
    journey_key: Optional[str],
    status: Optional[str],
) -> dict[str, Any]:
    completed = status == JOURNEY_STATUS_COMPLETED
    return {
        "is_completed": completed,
        "badge_ar": JOURNEY_COMPLETED_BADGE_AR if completed else "",
        "headline_ar": JOURNEY_COMPLETED_HEADLINE_AR if completed else "",
        "summary_items_ar": (
            _journey_completion_summary_ar(store, journey_key)
            if completed and journey_key
            else []
        ),
        "readiness_separation_note_ar": (
            JOURNEY_READINESS_SEPARATION_NOTE_AR if completed else ""
        ),
        "review_settings_cta_ar": CTA_REVIEW_SETTINGS_AR if completed else "",
    }


def journey_execution_config(journey_key: Optional[str]) -> dict[str, Any]:
    if not journey_key or journey_key not in _JOURNEY_EXECUTION:
        return {}
    cfg = dict(_JOURNEY_EXECUTION[journey_key])
    cfg["steps_ar"] = list(cfg.get("steps_ar") or [])
    return cfg


def journey_execution_block(store: Optional[Any]) -> dict[str, Any]:
    """Merchant execution payload — actions, progress, guidance."""
    journey_key = normalize_whatsapp_onboarding_journey(
        getattr(store, "whatsapp_onboarding_journey", None) if store else None
    )
    if not journey_key:
        return {
            "journey_key": None,
            "status": None,
            "status_ar": "",
            "execution": None,
            "future_meta_hooks": FUTURE_META_CONNECTION_HOOKS,
        }

    status = compute_journey_status(store, journey_key)
    cfg = journey_execution_config(journey_key)
    remaining = cfg.get("remaining_step_ar") or ""
    completion_ui = build_journey_completion_ui(store, journey_key, status)
    if status == JOURNEY_STATUS_COMPLETED:
        remaining = ""

    return {
        "journey_key": journey_key,
        "journey_label_ar": journey_label_ar(journey_key),
        "status": status,
        "status_ar": journey_status_label_ar(status),
        "status_badge_class": _STATUS_BADGE_CLASS.get(status or "", ""),
        "completion": completion_ui,
        "execution": {
            **cfg,
            "remaining_step_ar": remaining,
            "progress_pct": _progress_pct(status),
        },
        "future_meta_hooks": FUTURE_META_CONNECTION_HOOKS,
    }


def _progress_pct(status: Optional[str]) -> int:
    if status == JOURNEY_STATUS_COMPLETED:
        return 100
    if status == JOURNEY_STATUS_IN_PROGRESS:
        return 50
    if status == JOURNEY_STATUS_NOT_STARTED:
        return 0
    return 0


def journey_execution_fields_for_api(store: Optional[Any]) -> dict[str, Any]:
    block = journey_execution_block(store)
    return {
        "whatsapp_onboarding_journey_status": block.get("status"),
        "whatsapp_onboarding_journey_status_ar": block.get("status_ar") or None,
        "whatsapp_journey_execution": block,
    }


def apply_journey_execution_to_readiness(
    readiness: dict[str, Any],
    store: Optional[Any],
) -> dict[str, Any]:
    """Override action-first CTA/guidance with journey-specific execution paths."""
    out = dict(readiness)
    journeys = dict(out.get("whatsapp_onboarding_journeys") or {})
    journey_key = journeys.get("selected_key")
    exec_block = journey_execution_block(store)
    out["whatsapp_journey_execution"] = exec_block

    readiness_af = dict(out.get("action_first") or {})
    execution = exec_block.get("execution") or {}
    completion = exec_block.get("completion") or {}

    if not journey_key:
        af = dict(readiness_af)
        af["primary_cta_label_ar"] = CTA_CHOOSE_JOURNEY_AR
        af["next_action_ar"] = "اختر المسار الأنسب لمتجرك"
        af["expected_outcome_ar"] = (
            "سيبدأ CartFlow بإرسال رسائل الاسترجاع بعد اختيار المسار وإكمال الخطوات."
        )
        cb = dict(af.get("cta_behavior") or {})
        cb["cta_action"] = CTA_ACTION_OPEN_JOURNEY_SELECTOR
        cb["inline_guidance_ar"] = JOURNEY_SELECTOR_TITLE_AR
        cb["never_silent"] = True
        af["cta_behavior"] = cb
        out["action_first"] = af
        return out

    if not execution:
        out["action_first"] = readiness_af
        return out

    status = exec_block.get("status")

    if status == JOURNEY_STATUS_COMPLETED:
        af = dict(readiness_af)
        af["primary_cta_label_ar"] = CTA_REVIEW_SETTINGS_AR
        af["journey_completed"] = True
        cb = dict(af.get("cta_behavior") or {})
        cb["cta_action"] = CTA_ACTION_SCROLL_SETTINGS
        cb["highlight_fields"] = []
        cb["inline_guidance_ar"] = ""
        cb["journey_completed"] = True
        cb["never_silent"] = True
        af["cta_behavior"] = cb
        out["action_first"] = af
    else:
        af = dict(readiness_af)
        af["primary_cta_label_ar"] = (
            execution.get("primary_cta_ar") or CTA_CONTINUE_ACTIVATION_AR
        )
        af["next_action_ar"] = execution.get("remaining_step_ar") or execution.get(
            "inline_guidance_ar", ""
        )
        if execution.get("expected_outcome_ar"):
            af["expected_outcome_ar"] = execution["expected_outcome_ar"]
        cb = dict(af.get("cta_behavior") or {})
        cb["cta_action"] = execution.get("cta_action") or CTA_ACTION_SCROLL_SETTINGS
        cb["highlight_fields"] = list(execution.get("highlight_fields") or [])
        cb["inline_guidance_ar"] = (execution.get("inline_guidance_ar") or "").strip()
        cb["placeholder_ar"] = (execution.get("placeholder_ar") or "").strip()
        cb["secondary_note_ar"] = (execution.get("secondary_note_ar") or "").strip()
        cb["external_url"] = (execution.get("external_url") or "").strip()
        cb["explanation_ar"] = (execution.get("explanation_ar") or "").strip()
        cb["never_silent"] = True
        af["cta_behavior"] = cb
        out["action_first"] = af

    journeys["guidance"] = {
        "steps_ar": (
            [] if status == JOURNEY_STATUS_COMPLETED else list(execution.get("steps_ar") or [])
        ),
        "next_action_ar": execution.get("remaining_step_ar") or "",
        "expected_outcome_ar": execution.get("expected_outcome_ar") or "",
        "placeholder_ar": execution.get("placeholder_ar") or "",
        "secondary_note_ar": execution.get("secondary_note_ar") or "",
        "explanation_ar": execution.get("explanation_ar") or "",
        "status_ar": exec_block.get("status_ar") or "",
        "status_key": status or "",
        "status_badge_class": exec_block.get("status_badge_class") or "",
        "progress_pct": execution.get("progress_pct", 0),
        "completion": completion,
    }
    out["whatsapp_onboarding_journeys"] = journeys
    return out


def apply_whatsapp_onboarding_journey_status_from_body(
    row: Any,
    body: Mapping[str, Any],
) -> None:
    if "whatsapp_onboarding_journey_status" not in body:
        return
    raw = body.get("whatsapp_onboarding_journey_status")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        row.whatsapp_onboarding_journey_status = None
        return
    normalized = normalize_journey_status(raw)
    row.whatsapp_onboarding_journey_status = normalized


def on_journey_selection_changed(row: Any, new_journey: Optional[str]) -> None:
    """Reset progress when merchant picks a different path."""
    prev = normalize_whatsapp_onboarding_journey(
        getattr(row, "whatsapp_onboarding_journey", None)
    )
    if new_journey != prev:
        row.whatsapp_onboarding_journey_status = JOURNEY_STATUS_NOT_STARTED


def ensure_whatsapp_onboarding_journey_status_column(db: Any) -> None:
    from sqlalchemy import inspect, text
    from sqlalchemy.exc import SQLAlchemyError

    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        cols = {c["name"] for c in insp.get_columns("stores")}
        if "whatsapp_onboarding_journey_status" in cols:
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        if dialect in ("postgresql", "postgres"):
            stmt = (
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                "whatsapp_onboarding_journey_status VARCHAR(32)"
            )
        else:
            stmt = (
                "ALTER TABLE stores ADD COLUMN whatsapp_onboarding_journey_status "
                "VARCHAR(32)"
            )
        db.session.execute(text(stmt))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


def ensure_journey_execution_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    ensure_whatsapp_onboarding_journey_status_column(db)
    _schema_once = True


def reset_journey_execution_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False
