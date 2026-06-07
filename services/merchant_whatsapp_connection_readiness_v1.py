# -*- coding: utf-8 -*-
"""
WhatsApp Production Strategy Phase 5 — connection architecture & operational readiness.

Architecture and merchant experience only — no Meta, Cloud API, Embedded Signup,
send-path, recovery, billing enforcement, or provider migration.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness
from services.merchant_whatsapp_mode_v1 import (
    CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATUS_NOT_CONNECTED,
    CONNECTION_STATUS_SETUP,
    WHATSAPP_MODE_CARTFLOW_MANAGED,
    WHATSAPP_MODE_MERCHANT_WHATSAPP,
    normalize_whatsapp_mode,
    whatsapp_mode_label_ar,
)

# ── Canonical connection states (Part B) ─────────────────────────────────────

CONNECTION_STATE_NOT_CONNECTED = "not_connected"
CONNECTION_STATE_SETUP_REQUIRED = "setup_required"
CONNECTION_STATE_PENDING_CONFIGURATION = "pending_configuration"
CONNECTION_STATE_CONNECTED = "connected"
CONNECTION_STATE_ACTION_REQUIRED = "action_required"
CONNECTION_STATE_PAUSED = "paused"
CONNECTION_STATE_PROVIDER_ISSUE = "provider_issue"

CANONICAL_CONNECTION_STATES: frozenset[str] = frozenset(
    {
        CONNECTION_STATE_NOT_CONNECTED,
        CONNECTION_STATE_SETUP_REQUIRED,
        CONNECTION_STATE_PENDING_CONFIGURATION,
        CONNECTION_STATE_CONNECTED,
        CONNECTION_STATE_ACTION_REQUIRED,
        CONNECTION_STATE_PAUSED,
        CONNECTION_STATE_PROVIDER_ISSUE,
    }
)

CONNECTION_STATE_LABEL_AR: Mapping[str, str] = {
    CONNECTION_STATE_NOT_CONNECTED: "غير متصل",
    CONNECTION_STATE_SETUP_REQUIRED: "يلزم إعداد",
    CONNECTION_STATE_PENDING_CONFIGURATION: "قيد الإعداد",
    CONNECTION_STATE_CONNECTED: "متصل",
    CONNECTION_STATE_ACTION_REQUIRED: "يلزم إجراء",
    CONNECTION_STATE_PAUSED: "متوقف مؤقتاً",
    CONNECTION_STATE_PROVIDER_ISSUE: "يحتاج متابعة",
}

READINESS_OVERALL_READY = "ready"
READINESS_OVERALL_NOT_READY = "not_ready"

READINESS_OVERALL_LABEL_AR: Mapping[str, str] = {
    READINESS_OVERALL_READY: "جاهز",
    READINESS_OVERALL_NOT_READY: "غير جاهز",
}

# ── Action-first presentation (Readiness UX V2) ──────────────────────────────
# Pure merchant-facing copy per connection state: title + next action + single
# primary CTA + expected outcome. Presentation only — does not change the
# Readiness Engine, connection-state resolution, or production truth.

CONNECTION_STATE_ACTION_FIRST: Mapping[str, dict[str, str]] = {
    CONNECTION_STATE_NOT_CONNECTED: {
        "title_ar": "واتساب غير مرتبط",
        "next_action_ar": "ابدأ ربط واتساب",
        "primary_cta_label_ar": "تفعيل واتساب",
        "outcome_ar": "سيتمكن CartFlow من إرسال رسائل الاسترجاع.",
    },
    CONNECTION_STATE_SETUP_REQUIRED: {
        "title_ar": "يلزم إكمال الإعداد",
        "next_action_ar": "أكمل خطوات الإعداد المطلوبة",
        "primary_cta_label_ar": "استكمال الإعداد",
        "outcome_ar": "سيصبح واتساب جاهزاً للإرسال.",
    },
    CONNECTION_STATE_PENDING_CONFIGURATION: {
        "title_ar": "جاري إعداد الاتصال",
        "next_action_ar": "أكمل خطوة التفعيل الحالية",
        "primary_cta_label_ar": "إكمال التفعيل",
        "outcome_ar": "سيتم تفعيل واتساب للإنتاج.",
    },
    CONNECTION_STATE_CONNECTED: {
        "title_ar": "واتساب جاهز",
        "next_action_ar": "لا يوجد إجراء مطلوب",
        "primary_cta_label_ar": "فتح الإعدادات",
        "outcome_ar": "CartFlow جاهز لإرسال رسائل الاسترجاع.",
    },
    CONNECTION_STATE_ACTION_REQUIRED: {
        "title_ar": "يوجد إجراء مطلوب",
        "next_action_ar": "راجع المتطلبات الظاهرة أدناه",
        "primary_cta_label_ar": "مراجعة المتطلبات",
        "outcome_ar": "سيعود الاتصال للعمل بشكل طبيعي.",
    },
    CONNECTION_STATE_PAUSED: {
        "title_ar": "واتساب متوقف مؤقتاً",
        "next_action_ar": "استئناف التشغيل",
        "primary_cta_label_ar": "استئناف التشغيل",
        "outcome_ar": "سيعود الإرسال والمتابعة للعمل.",
    },
    CONNECTION_STATE_PROVIDER_ISSUE: {
        "title_ar": "توجد مشكلة لدى مزود الخدمة",
        "next_action_ar": "انتظر أو راجع حالة المزود",
        "primary_cta_label_ar": "مراجعة الحالة",
        "outcome_ar": "سيستأنف CartFlow الإرسال عند عودة الخدمة.",
    },
}

# Maps canonical state → legacy pill CSS key (Phase 1 UI)
CONNECTION_STATE_LEGACY_PILL_KEY: Mapping[str, str] = {
    CONNECTION_STATE_NOT_CONNECTED: CONNECTION_STATUS_NOT_CONNECTED,
    CONNECTION_STATE_SETUP_REQUIRED: CONNECTION_STATUS_SETUP,
    CONNECTION_STATE_PENDING_CONFIGURATION: CONNECTION_STATUS_SETUP,
    CONNECTION_STATE_CONNECTED: CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATE_ACTION_REQUIRED: CONNECTION_STATUS_SETUP,
    CONNECTION_STATE_PAUSED: CONNECTION_STATUS_NOT_CONNECTED,
    CONNECTION_STATE_PROVIDER_ISSUE: CONNECTION_STATUS_SETUP,
}

# Part H — Meta future placeholders (display only when implemented)
META_FUTURE_PLACEHOLDERS: tuple[dict[str, str], ...] = (
    {
        "key": "embedded_signup",
        "label_ar": "ربط Meta (Embedded Signup)",
        "status": "not_implemented",
        "status_ar": "قريباً — غير مفعّل بعد",
    },
    {
        "key": "meta_verification",
        "label_ar": "التحقق من Meta Business",
        "status": "not_implemented",
        "status_ar": "قريباً — غير مفعّل بعد",
    },
    {
        "key": "waba_status",
        "label_ar": "حالة WABA",
        "status": "not_implemented",
        "status_ar": "قريباً — غير مفعّل بعد",
    },
    {
        "key": "phone_verification",
        "label_ar": "التحقق من رقم واتساب",
        "status": "not_implemented",
        "status_ar": "قريباً — غير مفعّل بعد",
    },
)

_JOURNEY_MANAGED_REQUIRED_AR: tuple[str, ...] = (
    "اسم النشاط التجاري",
    "رقم واتساب للتواصل",
    "معلومات الجاهزية الأساسية",
)

_JOURNEY_MERCHANT_REQUIRED_AR: tuple[str, ...] = (
    "رقم واتساب المتجر",
    "حالة الاتصال",
    "متطلبات الجاهزية",
)


def meta_future_placeholders_for_api(*, visible: bool = False) -> list[dict[str, str]]:
    """Hidden until future Meta phase — architecture placeholder only."""
    if not visible:
        return []
    return [dict(p) for p in META_FUTURE_PLACEHOLDERS]


def connection_journey_for_mode(mode: str) -> dict[str, Any]:
    """Part A — supported merchant journeys (no Meta terminology)."""
    m = normalize_whatsapp_mode(mode)
    if m == WHATSAPP_MODE_MERCHANT_WHATSAPP:
        return {
            "journey_key": "merchant_whatsapp",
            "journey_label_ar": "Merchant WhatsApp",
            "merchant_provides_ar": list(_JOURNEY_MERCHANT_REQUIRED_AR),
            "merchant_sees_ar": [
                "رقم واتساب",
                "حالة الاتصال",
                "متطلبات الجاهزية",
            ],
            "hidden_from_merchant_ar": [
                "WABA",
                "Tokens",
                "Cloud API",
                "Webhooks",
            ],
        }
    return {
        "journey_key": "cartflow_managed",
        "journey_label_ar": "CartFlow Managed",
        "merchant_provides_ar": list(_JOURNEY_MANAGED_REQUIRED_AR),
        "merchant_sees_ar": [
            "اسم النشاط",
            "رقم واتساب",
            "معلومات الجاهزية",
        ],
        "hidden_from_merchant_ar": [
            "WABA",
            "Tokens",
            "Cloud API",
            "Webhooks",
            "Meta",
        ],
    }


def build_action_first_card(
    connection_state: str,
    *,
    expected_outcome_ar: str = "",
    setup_checklist: Optional[dict[str, Any]] = None,
    action_href: str = "/dashboard#whatsapp",
) -> dict[str, Any]:
    """
    Readiness UX V2 — action-first presentation block.

    Visual priority (consumed by partial + SPA): next action → remaining step →
    outcome → technical status. Always a single primary CTA. Pure presentation;
    no engine/state/truth changes.
    """
    state = connection_state if connection_state in CANONICAL_CONNECTION_STATES else (
        CONNECTION_STATE_SETUP_REQUIRED
    )
    spec = CONNECTION_STATE_ACTION_FIRST.get(
        state, CONNECTION_STATE_ACTION_FIRST[CONNECTION_STATE_SETUP_REQUIRED]
    )

    checklist = dict(setup_checklist or {})
    raw_steps = checklist.get("checklist_ar") or []
    remaining_steps: list[dict[str, Any]] = []
    for item in raw_steps:
        remaining_steps.append(
            {
                "label_ar": item.get("label_ar"),
                "mark_ar": item.get("mark_ar")
                or ("✓" if item.get("complete") else "✗"),
                "complete": bool(item.get("complete")),
            }
        )

    outcome = (expected_outcome_ar or "").strip() or spec["outcome_ar"]
    action_needed = state != CONNECTION_STATE_CONNECTED

    return {
        "connection_state": state,
        "connection_state_ar": CONNECTION_STATE_LABEL_AR.get(state, state),
        "title_ar": spec["title_ar"],
        "next_action_ar": spec["next_action_ar"],
        "primary_cta_label_ar": spec["primary_cta_label_ar"],
        "primary_cta_href": action_href or "/dashboard#whatsapp",
        "expected_outcome_ar": outcome,
        "remaining_steps_ar": remaining_steps,
        "status_headline_ar": checklist.get("headline_ar") or spec["title_ar"],
        "action_needed": action_needed,
        "single_cta": True,
    }


def _plan_eligible_for_store(store: Optional[Any]) -> bool:
    """Read-only plan visibility — no entitlement enforcement."""
    if store is None:
        return False
    try:
        from extensions import db  # noqa: PLC0415
        from models import MerchantUser  # noqa: PLC0415
        from services.merchant_subscription_v1 import (  # noqa: PLC0415
            PLAN_STATUS_ACTIVE,
            PLAN_STATUS_TRIALING,
            normalize_plan_status,
        )

        mid = getattr(store, "merchant_user_id", None)
        if not mid:
            return True
        mu = db.session.get(MerchantUser, int(mid))
        if mu is None:
            return True
        status = normalize_plan_status(getattr(mu, "plan_status", None))
        return status in (PLAN_STATUS_ACTIVE, PLAN_STATUS_TRIALING)
    except Exception:  # noqa: BLE001
        return True


def _readiness_dimensions(
    store: Optional[Any],
    flags: dict[str, bool],
) -> list[dict[str, Any]]:
    widget_ok = bool(flags.get("widget_installed"))
    store_ok = bool(flags.get("store_connected"))
    wa_number = bool(
        store is not None
        and (getattr(store, "store_whatsapp_number", None) or "").strip()
    )
    recovery_on = bool(flags.get("recovery_enabled"))
    sandbox = bool(flags.get("sandbox_mode_active"))
    prov = bool(flags.get("provider_ready"))
    wa_cfg = bool(flags.get("whatsapp_configured"))
    plan_ok = _plan_eligible_for_store(store)

    whatsapp_ok = (
        recovery_on
        and wa_number
        and not sandbox
        and (prov or not flags.get("sandbox_mode_active"))
        and (wa_cfg or sandbox)
    )
    if sandbox and store_ok and widget_ok and wa_number and recovery_on:
        whatsapp_ok = False

    return [
        {
            "key": "store_connected",
            "label_ar": "المتجر مربوط",
            "ready": store_ok,
        },
        {
            "key": "widget_ready",
            "label_ar": "الودجت جاهز",
            "ready": widget_ok,
        },
        {
            "key": "whatsapp_ready",
            "label_ar": "واتساب جاهز",
            "ready": whatsapp_ok,
        },
        {
            "key": "plan_eligible",
            "label_ar": "الباقة مؤهلة",
            "ready": plan_ok,
        },
    ]


def _resolve_connection_state(
    store: Optional[Any],
    flags: dict[str, bool],
    blocking: list[str],
) -> tuple[str, str, dict[str, str]]:
    """Return (state_key, label_ar, production_truth)."""
    truth: dict[str, str] = {
        "why_not_connected_ar": "",
        "why_paused_ar": "",
        "action_required_ar": "",
        "after_completion_ar": "",
    }
    blocking_set = set(blocking or [])
    recovery_on = bool(flags.get("recovery_enabled"))
    sandbox = bool(flags.get("sandbox_mode_active"))
    store_ok = bool(flags.get("store_connected"))
    widget_ok = bool(flags.get("widget_installed"))
    wa_number = bool(
        store is not None
        and (getattr(store, "store_whatsapp_number", None) or "").strip()
    )

    if store is None or "dashboard_not_initialized" in blocking_set:
        truth["why_not_connected_ar"] = "لم يكتمل إعداد المتجر بعد."
        truth["action_required_ar"] = "أكمل ربط المتجر من الإعدادات."
        truth["after_completion_ar"] = "ستظهر خطوات تفعيل واتساب تلقائياً."
        return CONNECTION_STATE_SETUP_REQUIRED, CONNECTION_STATE_LABEL_AR[
            CONNECTION_STATE_SETUP_REQUIRED
        ], truth

    if not recovery_on or "recovery_disabled" in blocking_set:
        truth["why_paused_ar"] = "استرجاع واتساب غير مفعّل حالياً."
        truth["action_required_ar"] = "فعّل استرجاع واتساب من هذه الصفحة."
        truth["after_completion_ar"] = "سيبدأ CartFlow بإعداد مسار رسائل الاسترجاع."
        return CONNECTION_STATE_PAUSED, CONNECTION_STATE_LABEL_AR[
            CONNECTION_STATE_PAUSED
        ], truth

    if sandbox:
        truth["why_not_connected_ar"] = "الوضع التجريبي مفعّل — الإنتاج غير مكتمل بعد."
        truth["action_required_ar"] = "أكمل خطوات التفعيل للإنتاج."
        truth["after_completion_ar"] = "ستُرسل رسائل الاسترجاع للعملاء عبر واتساب."
        if not store_ok or not widget_ok:
            return CONNECTION_STATE_SETUP_REQUIRED, CONNECTION_STATE_LABEL_AR[
                CONNECTION_STATE_SETUP_REQUIRED
            ], truth
        return CONNECTION_STATE_PENDING_CONFIGURATION, CONNECTION_STATE_LABEL_AR[
            CONNECTION_STATE_PENDING_CONFIGURATION
        ], truth

    if not store_ok or not widget_ok or not wa_number:
        missing: list[str] = []
        if not store_ok:
            missing.append("ربط المتجر")
        if not widget_ok:
            missing.append("تفعيل الودجيت")
        if not wa_number:
            missing.append("رقم واتساب المتجر")
        truth["why_not_connected_ar"] = "بعض متطلبات التشغيل غير مكتملة."
        truth["action_required_ar"] = "أكمل: " + " · ".join(missing)
        truth["after_completion_ar"] = (
            "سيبدأ CartFlow بإرسال رسائل الاسترجاع للعملاء."
        )
        return CONNECTION_STATE_SETUP_REQUIRED, CONNECTION_STATE_LABEL_AR[
            CONNECTION_STATE_SETUP_REQUIRED
        ], truth

    if "provider_not_ready" in blocking_set or not flags.get("provider_ready"):
        truth["why_not_connected_ar"] = "قناة واتساب تحتاج متابعة قبل الإنتاج الكامل."
        truth["action_required_ar"] = "راجع إعدادات واتساب وأكمل المتطلبات الناقصة."
        truth["after_completion_ar"] = "ستُرسل رسائل الاسترجاع للعملاء بشكل مستقر."
        return CONNECTION_STATE_PROVIDER_ISSUE, CONNECTION_STATE_LABEL_AR[
            CONNECTION_STATE_PROVIDER_ISSUE
        ], truth

    if "no_customer_phone_source" in blocking_set:
        truth["action_required_ar"] = (
            "تأكد أن الودجت يجمع رقم جوال العميل في السلة."
        )
        truth["after_completion_ar"] = "ستصل رسائل الاسترجاع للعملاء الذين أدخلوا رقمهم."
        return CONNECTION_STATE_ACTION_REQUIRED, CONNECTION_STATE_LABEL_AR[
            CONNECTION_STATE_ACTION_REQUIRED
        ], truth

    leftover = blocking_set - {
        "no_test_cart_seen",
    }
    if leftover:
        truth["action_required_ar"] = "راجع إعدادات المتجر وأكمل الخطوات المتبقية."
        truth["after_completion_ar"] = "سيعمل مسار الاسترجاع بالكامل."
        return CONNECTION_STATE_ACTION_REQUIRED, CONNECTION_STATE_LABEL_AR[
            CONNECTION_STATE_ACTION_REQUIRED
        ], truth

    truth["after_completion_ar"] = (
        "CartFlow يرسل رسائل الاسترجاع للعملاء حسب مراحل المتابعة."
    )
    return CONNECTION_STATE_CONNECTED, CONNECTION_STATE_LABEL_AR[
        CONNECTION_STATE_CONNECTED
    ], truth


def whatsapp_setup_checklist_for_merchant(
    store: Optional[Any],
    dimensions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Part D — merchant setup progression (onboarding style)."""
    remaining: list[str] = []
    done: list[str] = []
    for dim in dimensions:
        label = str(dim.get("label_ar") or "")
        if dim.get("ready"):
            done.append(label)
        else:
            remaining.append(label)

    total = len(dimensions) or 1
    complete = len(done)
    near = complete >= max(1, total - 1) and remaining

    if not remaining:
        headline = "متجرك جاهز للتشغيل الكامل"
        outcome = "سيبدأ CartFlow بإرسال رسائل الاسترجاع للعملاء."
    elif near:
        headline = "متجرك قريب من التشغيل الكامل"
        outcome = "أكمل المتبقي لبدء إرسال رسائل الاسترجاع للعملاء."
    else:
        headline = "أكمل إعداد متجرك"
        outcome = "ستُفعَّل رسائل الاسترجاع بعد اكتمال الخطوات."

    checklist: list[dict[str, Any]] = []
    for dim in dimensions:
        checklist.append(
            {
                "key": dim.get("key"),
                "label_ar": dim.get("label_ar"),
                "complete": bool(dim.get("ready")),
                "mark_ar": "✓" if dim.get("ready") else "✗",
            }
        )

    return {
        "headline_ar": headline,
        "remaining_title_ar": "المتبقي:",
        "checklist_ar": checklist,
        "outcome_ar": outcome,
        "remaining_count": len(remaining),
        "complete_count": complete,
    }


def evaluate_whatsapp_connection_readiness(
    store: Optional[Any],
    *,
    onboarding: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Operational readiness model — read-only."""
    ob = onboarding if onboarding is not None else evaluate_onboarding_readiness(store)
    flags = dict(ob.get("flags") or {})
    blocking = list(ob.get("blocking_steps") or [])

    mode = normalize_whatsapp_mode(
        getattr(store, "whatsapp_mode", None) if store is not None else None
    )
    state_key, state_label, production_truth = _resolve_connection_state(
        store, flags, blocking
    )
    dimensions = _readiness_dimensions(store, flags)
    all_ready = all(d.get("ready") for d in dimensions)
    connected = state_key == CONNECTION_STATE_CONNECTED
    overall = (
        READINESS_OVERALL_READY
        if all_ready and connected
        else READINESS_OVERALL_NOT_READY
    )

    missing: list[str] = [
        str(d["label_ar"]) for d in dimensions if not d.get("ready")
    ]
    if state_key != CONNECTION_STATE_CONNECTED:
        action = production_truth.get("action_required_ar") or ""
        if action and action not in missing:
            missing.insert(0, action)

    required_actions: list[str] = []
    if production_truth.get("action_required_ar"):
        required_actions.append(production_truth["action_required_ar"])
    for m in missing[:4]:
        if m not in required_actions:
            required_actions.append(m)

    journey = connection_journey_for_mode(mode)
    setup = whatsapp_setup_checklist_for_merchant(store, dimensions)

    expected_outcome = setup["outcome_ar"]
    if state_key == CONNECTION_STATE_CONNECTED:
        expected_outcome = production_truth.get("after_completion_ar") or expected_outcome

    return {
        "architecture_only": True,
        "no_meta_implementation": True,
        "no_runtime_send_changes": True,
        "whatsapp_mode": mode,
        "whatsapp_mode_label_ar": whatsapp_mode_label_ar(mode),
        "connection_state": state_key,
        "connection_state_ar": state_label,
        "connection_state_legacy_pill_key": CONNECTION_STATE_LEGACY_PILL_KEY.get(
            state_key, CONNECTION_STATUS_NOT_CONNECTED
        ),
        "readiness_overall": overall,
        "readiness_overall_ar": READINESS_OVERALL_LABEL_AR.get(
            overall, overall
        ),
        "readiness_dimensions": dimensions,
        "required_actions_ar": required_actions[:5],
        "expected_outcome_ar": expected_outcome,
        "production_truth": production_truth,
        "setup_checklist": setup,
        "connection_journey": journey,
        "missing_requirements_ar": missing,
        "meta_future_placeholders": meta_future_placeholders_for_api(
            visible=False
        ),
    }


def connection_readiness_for_merchant_api(
    store: Optional[Any],
) -> dict[str, Any]:
    ev = dict(evaluate_whatsapp_connection_readiness(store))
    ev["action_first"] = build_action_first_card(
        ev.get("connection_state") or CONNECTION_STATE_NOT_CONNECTED,
        expected_outcome_ar=ev.get("expected_outcome_ar") or "",
        setup_checklist=ev.get("setup_checklist") or {},
    )
    return ev


def connection_readiness_for_admin_row(
    store: Optional[Any],
) -> dict[str, Any]:
    """Admin operational slice — Part G."""
    ev = evaluate_whatsapp_connection_readiness(store)
    notes: list[str] = []
    pt = ev.get("production_truth") or {}
    for key in (
        "why_not_connected_ar",
        "why_paused_ar",
        "action_required_ar",
    ):
        val = (pt.get(key) or "").strip()
        if val:
            notes.append(val)
    mode = ev.get("whatsapp_mode") or WHATSAPP_MODE_CARTFLOW_MANAGED
    return {
        "connection_state": ev.get("connection_state"),
        "connection_state_ar": ev.get("connection_state_ar"),
        "readiness_state": ev.get("readiness_overall"),
        "readiness_state_ar": ev.get("readiness_overall_ar"),
        "whatsapp_mode": mode,
        "whatsapp_mode_label_ar": ev.get("whatsapp_mode_label_ar"),
        "missing_requirements_ar": ev.get("missing_requirements_ar") or [],
        "operational_notes_ar": notes,
        "readiness_dimensions": ev.get("readiness_dimensions") or [],
        "meta_future_placeholders": meta_future_placeholders_for_api(
            visible=False
        ),
    }
