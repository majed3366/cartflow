# -*- coding: utf-8 -*-
"""
Merchant Onboarding Reality v1 — audit + readiness foundation (read-only).

Answers: can a new merchant reach production_ready without manual ops?
Evaluates dimensions and emits [MERCHANT READINESS] logs; no recovery/send changes.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

log = logging.getLogger("cartflow")

LEVEL_NOT_STARTED = "not_started"
LEVEL_SANDBOX_ONLY = "sandbox_only"
LEVEL_PARTIAL = "partial"
LEVEL_PRODUCTION_READY = "production_ready"

TEMPLATE_APPROVED_UNKNOWN = "unknown"
TEMPLATE_APPROVED_PARTIAL = "partial"
TEMPLATE_APPROVED_READY = "ready"
TEMPLATE_APPROVED_NONE = "none"


@dataclass
class MerchantOnboardingReality:
    store_slug: str = ""
    onboarding_state: str = LEVEL_NOT_STARTED
    provider_connected: bool = False
    delivery_truth_ready: bool = False
    window_24h_ready: bool = False
    template_routing_ready: bool = False
    store_whatsapp_number_set: bool = False
    recovery_enabled: bool = False
    delays_configured: bool = False
    widget_enabled: bool = False
    store_connected: bool = False
    templates_present: bool = False
    templates_approved: str = TEMPLATE_APPROVED_UNKNOWN
    queue_ready: bool = False
    restart_survival_ready: bool = False
    missing: list[str] = field(default_factory=list)
    next_action_ar: str = ""
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _store_slug(store: Optional[Any]) -> str:
    if store is None:
        return ""
    for attr in ("slug", "zid_store_id"):
        v = getattr(store, attr, None)
        if isinstance(v, str) and v.strip():
            return v.strip()[:255]
    return ""


def _platform_queue_foundation_ready() -> bool:
    try:
        import services.whatsapp_queue  # noqa: F401
        from models import RecoverySchedule  # noqa: F401

        _ = RecoverySchedule.__tablename__
        return True
    except Exception:  # noqa: BLE001
        return False


def _platform_restart_survival_foundation_ready() -> bool:
    try:
        from services.recovery_restart_survival import (
            repair_stale_running_recovery_schedules,
        )

        return callable(repair_stale_running_recovery_schedules)
    except Exception:  # noqa: BLE001
        return False


def _platform_window_template_foundation_ready() -> tuple[bool, bool]:
    try:
        from services.whatsapp_production_reality_v2 import (
            decide_template_routing,
            evaluate_conversation_window,
        )

        return callable(evaluate_conversation_window), callable(decide_template_routing)
    except Exception:  # noqa: BLE001
        return False, False


def _templates_present(store: Optional[Any]) -> bool:
    if store is None:
        return False
    for attr in ("reason_templates_json", "trigger_templates_json"):
        raw = getattr(store, attr, None)
        if isinstance(raw, str) and raw.strip() and raw.strip() not in ("{}", "[]"):
            return True
    return False


def _delays_configured(store: Optional[Any]) -> bool:
    if store is None:
        return False
    try:
        d1 = int(getattr(store, "recovery_delay_minutes", 0) or 0)
    except (TypeError, ValueError):
        d1 = 0
    try:
        d2 = int(getattr(store, "recovery_second_attempt_delay_minutes", 0) or 0)
    except (TypeError, ValueError):
        d2 = 0
    return d1 > 0 or d2 > 0


def _templates_approved_status(store: Optional[Any], templates_present: bool) -> str:
    """No Meta sync in v1 — never claim full provider approval."""
    if not templates_present:
        return TEMPLATE_APPROVED_NONE
    return TEMPLATE_APPROVED_UNKNOWN


def evaluate_merchant_onboarding_reality(
    store: Optional[Any] = None,
    *,
    emit_log: bool = True,
) -> MerchantOnboardingReality:
    """
    Read-only composite readiness for one store (or platform when store is None).
    """
    from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

    slug = _store_slug(store)
    ob = evaluate_onboarding_readiness(store)
    flags = dict(ob.get("flags") or {})
    blocking = list(ob.get("blocking_steps") or [])
    milestones = dict(ob.get("milestones") or {})
    sandbox = bool(flags.get("sandbox_mode_active"))

    missing: list[str] = []
    evidence: list[str] = []

    queue_ready = _platform_queue_foundation_ready()
    restart_survival_ready = _platform_restart_survival_foundation_ready()
    win_foundation, tpl_foundation = _platform_window_template_foundation_ready()

    provider_connected = bool(flags.get("provider_ready")) and bool(
        flags.get("whatsapp_configured")
    )
    if sandbox:
        provider_connected = False

    delivery_truth_ready = False
    wa_v2_level = LEVEL_PARTIAL
    try:
        from services.whatsapp_production_reality_v2 import (
            evaluate_store_whatsapp_production_readiness,
        )

        wa = evaluate_store_whatsapp_production_readiness(store)
        delivery_truth_ready = bool(wa.delivery_truth_ready)
        wa_v2_level = wa.merchant_readiness_level
        evidence.extend(list(wa.evidence or [])[:6])
    except Exception:  # noqa: BLE001
        evidence.append("wa_v2_eval_failed")

    templates_present = _templates_present(store)
    templates_approved = _templates_approved_status(store, templates_present)

    store_whatsapp_number_set = bool(
        store is not None
        and str(getattr(store, "store_whatsapp_number", None) or "").strip()
    )
    recovery_enabled = bool(flags.get("recovery_enabled"))
    delays_configured = _delays_configured(store)
    widget_enabled = bool(flags.get("widget_installed"))
    store_connected = bool(flags.get("store_connected"))

    window_24h_ready = bool(
        win_foundation
        and (
            milestones.get("first_reply_received")
            or milestones.get("first_whatsapp_sent")
        )
    )
    template_routing_ready = bool(tpl_foundation and templates_present)

    if store is None or "dashboard_not_initialized" in blocking:
        state = LEVEL_NOT_STARTED
        if "dashboard_not_initialized" in blocking:
            missing.append("dashboard_not_initialized")
    elif sandbox:
        state = LEVEL_SANDBOX_ONLY
        if not store_connected:
            missing.append("store_not_connected")
        if not widget_enabled:
            missing.append("widget_not_installed")
        if not recovery_enabled:
            missing.append("recovery_disabled")
        missing.append("production_mode_off_or_twilio_missing")
    else:
        state = LEVEL_PARTIAL
        if provider_connected:
            evidence.append("provider_connected")
        else:
            missing.append("provider_not_connected")
        if not delivery_truth_ready:
            missing.append("delivery_truth_callback")
        if not templates_present:
            missing.append("templates_not_configured")
        if templates_approved == TEMPLATE_APPROVED_UNKNOWN and templates_present:
            missing.append("templates_not_provider_approved")
        if not store_whatsapp_number_set:
            missing.append("store_whatsapp_number")
        if not recovery_enabled:
            missing.append("recovery_disabled")
        if not delays_configured:
            missing.append("recovery_delays")
        if not widget_enabled:
            missing.append("widget_not_installed")
        if not store_connected:
            missing.append("store_not_connected")
        if not queue_ready:
            missing.append("queue_foundation")
        if not restart_survival_ready:
            missing.append("restart_survival_foundation")
        if not window_24h_ready:
            missing.append("24h_window_evidence")
        if not template_routing_ready:
            missing.append("template_routing")

        production_dims = (
            provider_connected
            and delivery_truth_ready
            and templates_present
            and recovery_enabled
            and widget_enabled
            and store_connected
            and delays_configured
            and queue_ready
            and restart_survival_ready
            and template_routing_ready
        )
        if production_dims and wa_v2_level == LEVEL_PRODUCTION_READY:
            state = LEVEL_PRODUCTION_READY
            missing = [m for m in missing if m not in (
                "provider_not_connected",
                "delivery_truth_callback",
                "templates_not_configured",
                "recovery_delays",
                "template_routing",
            )]

    next_action_ar = str(ob.get("recommended_next_step_ar") or "").strip()
    if not next_action_ar and missing:
        next_action_ar = _missing_to_action_ar(missing[0])

    reality = MerchantOnboardingReality(
        store_slug=slug or "(platform)",
        onboarding_state=state,
        provider_connected=provider_connected,
        delivery_truth_ready=delivery_truth_ready,
        window_24h_ready=window_24h_ready,
        template_routing_ready=template_routing_ready,
        store_whatsapp_number_set=store_whatsapp_number_set,
        recovery_enabled=recovery_enabled,
        delays_configured=delays_configured,
        widget_enabled=widget_enabled,
        store_connected=store_connected,
        templates_present=templates_present,
        templates_approved=templates_approved,
        queue_ready=queue_ready,
        restart_survival_ready=restart_survival_ready,
        missing=missing,
        next_action_ar=next_action_ar,
        evidence=evidence,
    )

    if emit_log:
        _log_merchant_readiness(reality)

    return reality


def _missing_to_action_ar(code: str) -> str:
    mapping = {
        "dashboard_not_initialized": "أنشئ أو اربط سجل المتجر من لوحة التحكم.",
        "store_not_connected": "أكمل ربط زد أو اعتماد المتجر.",
        "provider_not_connected": "اضبط Twilio ووضع الإنتاج على الخادم.",
        "delivery_truth_callback": "اضبط CARTFLOW_PUBLIC_BASE_URL أو TWILIO_STATUS_CALLBACK_URL.",
        "templates_not_configured": "أكمل قوالب الاسترجاع من إعدادات الواتساب.",
        "templates_not_provider_approved": "قدّم قوالب واتساب للاعتماد لدى المزود (يدوي).",
        "store_whatsapp_number": "أضف رقم واتساب المتجر في الإعدادات.",
        "recovery_disabled": "فعّل الاسترجاع وعدد المحاولات.",
        "recovery_delays": "اضبط تأخير المحاولة الأولى/الثانية.",
        "widget_not_installed": "فعّل ودجت CartFlow على المتجر.",
        "production_mode_off_or_twilio_missing": "للإنتاج: فعّل PRODUCTION_MODE وTwilio.",
        "24h_window_evidence": "انتظر رد عميل أو اختبر عبر /dev/whatsapp-window-simulate.",
    }
    return mapping.get(code, "راجع إعدادات المتجر والواتساب.")


def _log_merchant_readiness(reality: MerchantOnboardingReality) -> None:
    missing_s = ",".join(reality.missing[:12]) if reality.missing else "-"
    line = (
        f"[MERCHANT READINESS] store_slug={reality.store_slug} "
        f"level={reality.onboarding_state} missing={missing_s}"
    )
    print(line, flush=True)
    log.info("%s", line)


def build_merchant_onboarding_admin_card(
    store: Optional[Any] = None,
) -> dict[str, Any]:
    """Admin card: جاهزية المتجر — current level, missing, next action."""
    from services.admin_operational_health_language import (
        build_operations_center_decision,
    )

    r = evaluate_merchant_onboarding_reality(store, emit_log=False)
    level_ar = {
        LEVEL_NOT_STARTED: "لم يبدأ",
        LEVEL_SANDBOX_ONLY: "تجريبي فقط",
        LEVEL_PARTIAL: "جزئي",
        LEVEL_PRODUCTION_READY: "جاهز للإنتاج",
    }.get(r.onboarding_state, r.onboarding_state)

    missing_ar = "؛ ".join(r.missing[:6]) if r.missing else "لا يوجد"
    detail_lines = [
        f"المستوى: {level_ar}",
        f"المزود متصل: {'نعم' if r.provider_connected else 'لا'}",
        f"حقيقة التسليم: {'نعم' if r.delivery_truth_ready else 'لا'}",
        f"قوالب محلية: {'نعم' if r.templates_present else 'لا'} (اعتماد المزود: {r.templates_approved})",
        f"ناقص: {missing_ar}",
        f"التالي: {r.next_action_ar or '—'}",
    ]
    tier = "ok" if r.onboarding_state == LEVEL_PRODUCTION_READY else (
        "watch" if r.onboarding_state == LEVEL_PARTIAL else "action"
    )
    return {
        "title": "merchant_onboarding",
        "title_ar": "جاهزية المتجر",
        "onboarding_state": r.onboarding_state,
        "store_slug": r.store_slug,
        "reality": r.to_dict(),
        "operational": build_operations_center_decision(
            title_ar="جاهزية المتجر",
            problem_ar=f"المستوى الحالي: {level_ar}",
            impact_ar="يحدد إمكانية استرجاع واتساب إنتاجي بلا تدخل يدوي",
            affected_stores_ar=r.store_slug,
            affected_customers_ar="—",
            urgency_ar="متوسطة" if tier == "watch" else ("عالية" if tier == "action" else "منخفضة"),
            suggested_action_ar=r.next_action_ar or "—",
            verification_lines=detail_lines[:4],
            status_tier=tier,
        ),
        "technical_detail_lines": detail_lines,
        "detail_lines": detail_lines,
    }


def audit_can_self_serve_to_production_ready() -> dict[str, Any]:
    """
    Platform-level audit verdict for docs/tests (no mutations).
    """
    gaps = [
        "Twilio/Meta credentials and status callback URL are server env — not self-serve in dashboard",
        "WhatsApp template provider approval has no Meta sync — manual",
        "Sandbox recipient join is manual in Twilio console",
        "Zid OAuth / store connection requires merchant action",
        "PRODUCTION_MODE is deployment-level, not per-store toggle in UI",
    ]
    return {
        "verdict": "PARTIAL",
        "self_serve_to_production_ready": False,
        "automation_gaps": gaps,
        "foundation_present": True,
        "notes": "Readiness dimensions and logs exist; merchant still needs ops/env steps.",
    }
