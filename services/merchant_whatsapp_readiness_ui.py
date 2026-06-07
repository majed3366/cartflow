# -*- coding: utf-8 -*-
"""
Merchant-facing WhatsApp / recovery readiness card (read-only interpretation).

Phase 5: enriches card with connection state, mode, required actions, and
expected outcome — no send/runtime changes.
"""
from __future__ import annotations

from typing import Any, Optional

from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

_HREF_SETTINGS = "/dashboard#whatsapp"
_HREF_GENERAL = "/dashboard#settings"


def build_merchant_whatsapp_readiness_card(store: Optional[Any]) -> dict[str, Any]:
    """
    Returns card payload: title, descriptions, badge, actions, and Phase 5
    connection/readiness truth fields.
    """
    from services.merchant_whatsapp_connection_readiness_v1 import (  # noqa: PLC0415
        CONNECTION_STATE_CONNECTED,
        CONNECTION_STATE_PAUSED,
        CONNECTION_STATE_PENDING_CONFIGURATION,
        CONNECTION_STATE_PROVIDER_ISSUE,
        CONNECTION_STATE_SETUP_REQUIRED,
        READINESS_OVERALL_READY,
        evaluate_whatsapp_connection_readiness,
    )
    from services.wa_readiness_step_profiler import (
        wa_readiness_profile_begin,
        wa_readiness_profile_end,
        wa_readiness_step_profiling_enabled,
    )

    _wa_prof_run = wa_readiness_step_profiling_enabled()
    if _wa_prof_run:
        wa_readiness_profile_begin()
    try:
        ob = evaluate_onboarding_readiness(store)
        conn = evaluate_whatsapp_connection_readiness(store, onboarding=ob)
    finally:
        if _wa_prof_run:
            wa_readiness_profile_end()

    flags: dict[str, Any] = dict(ob.get("flags") or {})
    blocking: set[str] = set(ob.get("blocking_steps") or [])

    recovery_on = bool(flags.get("recovery_enabled"))
    sandbox = bool(flags.get("sandbox_mode_active"))
    store_ok = bool(flags.get("store_connected"))
    widget_ok = bool(flags.get("widget_installed"))
    wa_cfg = bool(flags.get("whatsapp_configured"))
    prov = bool(flags.get("provider_ready"))

    state_key = conn.get("connection_state") or CONNECTION_STATE_SETUP_REQUIRED
    mode_label = conn.get("whatsapp_mode_label_ar") or "CartFlow Managed"
    required_actions = list(conn.get("required_actions_ar") or [])
    expected_outcome = conn.get("expected_outcome_ar") or ""
    production_truth = dict(conn.get("production_truth") or {})
    setup_checklist = dict(conn.get("setup_checklist") or {})

    def _enrich(base: dict[str, Any]) -> dict[str, Any]:
        base["connection_state"] = state_key
        base["connection_state_ar"] = conn.get("connection_state_ar") or ""
        base["whatsapp_mode"] = conn.get("whatsapp_mode")
        base["whatsapp_mode_label_ar"] = mode_label
        base["readiness_overall"] = conn.get("readiness_overall")
        base["readiness_overall_ar"] = conn.get("readiness_overall_ar")
        base["required_actions_ar"] = required_actions
        base["expected_outcome_ar"] = expected_outcome
        base["production_truth"] = production_truth
        base["setup_checklist"] = setup_checklist
        base["readiness_dimensions"] = conn.get("readiness_dimensions") or []
        return base

    if store is None or "dashboard_not_initialized" in blocking:
        return _enrich(
            _payload(
                key="setup",
                title="يلزم إكمال إعداد الواتساب",
                desc=production_truth.get("why_not_connected_ar")
                or "بعض متطلبات التشغيل غير مكتملة بعد.",
                impact=expected_outcome
                or "قد لا تعمل رسائل الاسترجاع بالكامل حتى اكتمال الإعداد.",
                badge="يحتاج متابعة",
                badge_class="border-violet-200 bg-violet-50 text-violet-900",
                action_label="متابعة الإعداد",
                action_href=_HREF_GENERAL,
            )
        )

    if not recovery_on or "recovery_disabled" in blocking:
        return _enrich(
            _payload(
                key="disabled",
                title="الواتساب غير مفعل",
                desc=production_truth.get("why_paused_ar")
                or "استرجاع السلال عبر الواتساب متوقف حاليًا.",
                impact=expected_outcome
                or "لن يتم إرسال رسائل استرجاع حتى يتم التفعيل.",
                badge="غير مفعل",
                badge_class="border-stone-200 bg-stone-100 text-stone-800",
                action_label="تفعيل الواتساب",
                action_href=_HREF_SETTINGS,
            )
        )

    if state_key == CONNECTION_STATE_CONNECTED and conn.get("readiness_overall") == READINESS_OVERALL_READY:
        return _enrich(
            _payload(
                key="ready",
                title="الواتساب جاهز",
                desc="استرجاع السلال عبر الواتساب يعمل بشكل طبيعي.",
                impact=expected_outcome
                or "الاسترجاع يعمل، ويمكن متابعة الأداء من لوحة التحليلات.",
                badge="جاهز",
                badge_class="border-emerald-200 bg-emerald-50 text-emerald-900",
                action_label="فتح الإعدادات",
                action_href=_HREF_SETTINGS,
            )
        )

    if sandbox:
        if not store_ok or not widget_ok:
            return _enrich(
                _payload(
                    key="setup",
                    title="يلزم إكمال إعداد الواتساب",
                    desc=production_truth.get("why_not_connected_ar")
                    or "بعض متطلبات التشغيل غير مكتملة بعد.",
                    impact=expected_outcome,
                    badge="يحتاج متابعة",
                    badge_class="border-violet-200 bg-violet-50 text-violet-900",
                    action_label="متابعة الإعداد",
                    action_href=_HREF_GENERAL,
                )
            )
        return _enrich(
            _payload(
                key="sandbox",
                title="الوضع التجريبي مفعل",
                desc=production_truth.get("why_not_connected_ar")
                or "النظام يعمل حاليًا ضمن وضع تجريبي.",
                impact=expected_outcome
                or "قد يكون إرسال رسائل الاسترجاع محدودًا حتى اكتمال التفعيل.",
                badge="تجريبي",
                badge_class="border-amber-200 bg-amber-50 text-amber-950",
                action_label="إكمال التفعيل",
                action_href=_HREF_GENERAL,
            )
        )

    if state_key == CONNECTION_STATE_PENDING_CONFIGURATION:
        return _enrich(
            _payload(
                key="pending",
                title="قيد الإعداد",
                desc=production_truth.get("why_not_connected_ar")
                or "إعداد واتساب قيد الإكمال.",
                impact=expected_outcome,
                badge="قيد الإعداد",
                badge_class="border-amber-200 bg-amber-50 text-amber-950",
                action_label="متابعة الإعداد",
                action_href=_HREF_SETTINGS,
            )
        )

    if state_key == CONNECTION_STATE_PROVIDER_ISSUE:
        return _enrich(
            _payload(
                key="review",
                title="يحتاج متابعة",
                desc=production_truth.get("why_not_connected_ar")
                or "يوجد إعداد يحتاج متابعة لضمان عمل الاسترجاع بشكل مستقر.",
                impact=expected_outcome,
                badge="مراجعة",
                badge_class="border-slate-200 bg-slate-100 text-slate-800",
                action_label="فتح إعدادات الواتساب",
                action_href=_HREF_SETTINGS,
            )
        )

    if not store_ok or not widget_ok or not wa_cfg:
        return _enrich(
            _payload(
                key="setup",
                title="يلزم إكمال إعداد الواتساب",
                desc=production_truth.get("why_not_connected_ar")
                or "بعض متطلبات التشغيل غير مكتملة بعد.",
                impact=expected_outcome
                or "قد لا تصل رسائل الاسترجاع لبعض العملاء حتى اكتمال التفعيل.",
                badge="يحتاج متابعة",
                badge_class="border-violet-200 bg-violet-50 text-violet-900",
                action_label="متابعة الإعداد",
                action_href=_HREF_GENERAL,
            )
        )

    if not prov or "provider_not_ready" in blocking:
        return _enrich(
            _payload(
                key="review",
                title="يحتاج متابعة",
                desc=production_truth.get("why_not_connected_ar")
                or "يوجد إعداد يحتاج متابعة لضمان عمل الاسترجاع بشكل مستقر.",
                impact=expected_outcome,
                badge="مراجعة",
                badge_class="border-slate-200 bg-slate-100 text-slate-800",
                action_label="فتح إعدادات الواتساب",
                action_href=_HREF_SETTINGS,
            )
        )

    if "no_customer_phone_source" in blocking:
        return _enrich(
            _payload(
                key="review",
                title="يحتاج متابعة",
                desc=production_truth.get("action_required_ar")
                or "يوجد إعداد يحتاج مراجعة لضمان عمل الاسترجاع بشكل مستقر.",
                impact=expected_outcome,
                badge="مراجعة",
                badge_class="border-slate-200 bg-slate-100 text-slate-800",
                action_label="فتح إعدادات الواتساب",
                action_href=_HREF_SETTINGS,
            )
        )

    leftover = set(blocking)
    if leftover:
        return _enrich(
            _payload(
                key="review",
                title="يحتاج متابعة",
                desc=production_truth.get("action_required_ar")
                or "يوجد إعداد يحتاج مراجعة لضمان عمل الاسترجاع بشكل مستقر.",
                impact=expected_outcome,
                badge="مراجعة",
                badge_class="border-slate-200 bg-slate-100 text-slate-800",
                action_label="فتح إعدادات الواتساب",
                action_href=_HREF_SETTINGS,
            )
        )

    return _enrich(
        _payload(
            key="ready",
            title="الواتساب جاهز",
            desc="استرجاع السلال عبر الواتساب يعمل بشكل طبيعي.",
            impact=expected_outcome,
            badge="جاهز",
            badge_class="border-emerald-200 bg-emerald-50 text-emerald-900",
            action_label="فتح الإعدادات",
            action_href=_HREF_SETTINGS,
        )
    )


def _payload(
    *,
    key: str,
    title: str,
    desc: str,
    impact: str,
    badge: str,
    badge_class: str,
    action_label: str,
    action_href: str,
) -> dict[str, Any]:
    return {
        "state_key": key,
        "title_ar": title,
        "description_ar": desc,
        "impact_ar": impact,
        "badge_ar": badge,
        "badge_class": badge_class,
        "action_label_ar": action_label,
        "action_href": action_href,
    }
