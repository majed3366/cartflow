# -*- coding: utf-8 -*-
"""
Merchant-facing WhatsApp / recovery readiness card (read-only interpretation).

Uses existing onboarding readiness evaluation only — no changes to sending,
recovery scheduling, or persistence.
"""
from __future__ import annotations

from typing import Any, Optional

from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

_HREF_SETTINGS = "/dashboard#whatsapp"
_HREF_GENERAL = "/dashboard#settings"


def build_merchant_whatsapp_readiness_card(store: Optional[Any]) -> dict[str, Any]:
    """
    Returns a single card payload: title, descriptions, badge, one action (href + label).

    Merchant-safe Arabic only; no provider names or technical tokens.
    """
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

    # Store not wired into dashboard yet — interpret as incomplete setup (not “disabled”).
    if store is None or "dashboard_not_initialized" in blocking:
        return _payload(
            key="setup",
            title="يلزم إكمال إعداد الواتساب",
            desc="بعض متطلبات التشغيل غير مكتملة بعد.",
            impact="قد لا تعمل رسائل الاسترجاع بالكامل حتى اكتمال الإعداد.",
            badge="يحتاج متابعة",
            badge_class="border-violet-200 bg-violet-50 text-violet-900",
            action_label="متابعة الإعداد",
            action_href=_HREF_GENERAL,
        )

    if not recovery_on or "recovery_disabled" in blocking:
        return _payload(
            key="disabled",
            title="الواتساب غير مفعل",
            desc="استرجاع السلال عبر الواتساب متوقف حاليًا.",
            impact="لن يتم إرسال رسائل استرجاع حتى يتم التفعيل.",
            badge="غير مفعل",
            badge_class="border-stone-200 bg-stone-100 text-stone-800",
            action_label="تفعيل الواتساب",
            action_href=_HREF_SETTINGS,
        )

    if sandbox:
        if not store_ok or not widget_ok:
            return _payload(
                key="setup",
                title="يلزم إكمال إعداد الواتساب",
                desc="بعض متطلبات التشغيل غير مكتملة بعد.",
                impact="قد لا تعمل رسائل الاسترجاع بالكامل حتى اكتمال الإعداد.",
                badge="يحتاج متابعة",
                badge_class="border-violet-200 bg-violet-50 text-violet-900",
                action_label="متابعة الإعداد",
                action_href=_HREF_GENERAL,
            )
        return _payload(
            key="sandbox",
            title="الوضع التجريبي مفعل",
            desc="النظام يعمل حاليًا ضمن وضع تجريبي.",
            impact="قد يكون إرسال رسائل الاسترجاع محدودًا حتى اكتمال التفعيل.",
            badge="تجريبي",
            badge_class="border-amber-200 bg-amber-50 text-amber-950",
            action_label="إكمال التفعيل",
            action_href=_HREF_GENERAL,
        )

    if not store_ok or not widget_ok or not wa_cfg:
        return _payload(
            key="setup",
            title="يلزم إكمال إعداد الواتساب",
            desc="بعض متطلبات التشغيل غير مكتملة بعد.",
            impact="قد لا تصل رسائل الاسترجاع لبعض العملاء حتى اكتمال التفعيل.",
            badge="يحتاج متابعة",
            badge_class="border-violet-200 bg-violet-50 text-violet-900",
            action_label="متابعة الإعداد",
            action_href=_HREF_GENERAL,
        )

    if not prov or "provider_not_ready" in blocking:
        return _payload(
            key="review",
            title="يحتاج مراجعة",
            desc="يوجد إعداد يحتاج مراجعة لضمان عمل الاسترجاع بشكل مستقر.",
            impact="قد لا تصل رسائل الاسترجاع لبعض العملاء حتى يتم توضيح الإعداد.",
            badge="مراجعة",
            badge_class="border-slate-200 bg-slate-100 text-slate-800",
            action_label="فتح إعدادات الواتساب",
            action_href=_HREF_GENERAL,
        )

    if "no_customer_phone_source" in blocking:
        return _payload(
            key="review",
            title="يحتاج مراجعة",
            desc="يوجد إعداد يحتاج مراجعة لضمان عمل الاسترجاع بشكل مستقر.",
            impact="قد لا تصل رسائل الاسترجاع لبعض العملاء حتى يتوفر وسيلة موثوقة لرقم الجوال.",
            badge="مراجعة",
            badge_class="border-slate-200 bg-slate-100 text-slate-800",
            action_label="فتح إعدادات الواتساب",
            action_href=_HREF_GENERAL,
        )

    leftover = set(blocking)
    if leftover:
        return _payload(
            key="review",
            title="يحتاج مراجعة",
            desc="يوجد إعداد يحتاج مراجعة لضمان عمل الاسترجاع بشكل مستقر.",
            impact="قد لا تعمل رسائل الاسترجاع بالكامل حتى تُستكمل الخطوات المناسبة.",
            badge="مراجعة",
            badge_class="border-slate-200 bg-slate-100 text-slate-800",
            action_label="فتح إعدادات الواتساب",
            action_href=_HREF_GENERAL,
        )

    return _payload(
        key="ready",
        title="الواتساب جاهز",
        desc="استرجاع السلال عبر الواتساب يعمل بشكل طبيعي.",
        impact="الاسترجاع يعمل، ويمكن متابعة الأداء من لوحة التحليلات.",
        badge="جاهز",
        badge_class="border-emerald-200 bg-emerald-50 text-emerald-900",
        action_label="فتح الإعدادات",
        action_href=_HREF_SETTINGS,
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
