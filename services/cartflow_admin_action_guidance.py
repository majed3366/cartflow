# -*- coding: utf-8 -*-
"""
Actionable operational routing for the admin control center.

Reads-only existing operational summary payloads. Proposes titles, meanings,
recommended steps, and placeholder internal routes. Does not compute health
or alter recovery/WhatsApp/runtime/trust logic.
"""
from __future__ import annotations

from typing import Any

from services.cartflow_admin_operational_guidance import (
    PRIORITY_CRITICAL,
    PRIORITY_FOLLOW_UP,
    PRIORITY_INTERVENTION,
    PRIORITY_NORMAL,
)
from services.cartflow_admin_operational_summary import (
    ADMIN_PLATFORM_CATEGORY_DEGRADED,
    ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED,
    ADMIN_PLATFORM_CATEGORY_OPERATIONAL_ATTENTION,
    ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION,
    ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY,
)

# Placeholder admin targets (pages may be added later; safe paths for navigation intent).
HREF_WHATSAPP_SETTINGS = "/admin/settings/whatsapp"
HREF_PRODUCTION_MODE = "/admin/settings/production"
HREF_ONBOARDING = "/admin/onboarding"
HREF_RUNTIME = "/admin/runtime"
HREF_PROVIDERS = "/admin/providers"


def _ts(summary: dict[str, Any]) -> dict[str, Any]:
    v = summary.get("trust_signals_summary")
    return v if isinstance(v, dict) else {}


def _de(summary: dict[str, Any]) -> dict[str, Any]:
    v = summary.get("degradation_flags")
    return v if isinstance(v, dict) else {}


def _rt(summary: dict[str, Any]) -> dict[str, Any]:
    v = summary.get("admin_runtime_summary_reuse")
    return v if isinstance(v, dict) else {}


def _agg(summary: dict[str, Any]) -> dict[str, Any]:
    v = summary.get("aggregate_onboarding")
    return v if isinstance(v, dict) else {}


def _allow_action_cards(summary: dict[str, Any], *, priority_key: str) -> bool:
    """High-value contexts only; avoid spam when everything is calm."""
    if priority_key in (PRIORITY_FOLLOW_UP, PRIORITY_INTERVENTION, PRIORITY_CRITICAL):
        return True
    ts = _ts(summary)
    de = _de(summary)
    rt = _rt(summary)
    pcat = str(summary.get("platform_admin_category") or "").strip()
    agg = _agg(summary)
    blocked_n = int(agg.get("onboarding_blocked_stores") or 0)
    if bool(ts.get("runtime_degraded")):
        return True
    if pcat in (
        ADMIN_PLATFORM_CATEGORY_DEGRADED,
        ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED,
        ADMIN_PLATFORM_CATEGORY_OPERATIONAL_ATTENTION,
    ):
        return True
    if bool(de.get("high_recent_duplicate_anomalies")) or bool(
        de.get("repeated_provider_failures")
    ):
        return True
    if bool(de.get("onboarding_pressure")) or blocked_n > 0:
        return True
    if rt.get("provider_runtime_ok") is False:
        return True
    return False


def _phone_gap_threshold(priority_key: str) -> int:
    return 1 if priority_key != PRIORITY_NORMAL else 3


def derive_actionable_operational_items(
    summary: dict[str, Any],
    *,
    priority_key: str,
) -> list[dict[str, Any]]:
    """
    Deterministic actionable rows for the admin UI. Same summary in → same list out.
    """
    if not _allow_action_cards(summary, priority_key=priority_key):
        return []

    ts = _ts(summary)
    de = _de(summary)
    rt = _rt(summary)
    agg = _agg(summary)
    pcat = str(summary.get("platform_admin_category") or "").strip()
    scanned = int(agg.get("total_stores_scanned") or 0)
    blocked_n = int(agg.get("onboarding_blocked_stores") or 0)
    sandbox_ratio = float(agg.get("sandbox_store_ratio") or 0.0)
    phone_gap = int(summary.get("stores_missing_phone_coverage_estimate") or 0)
    phone_thr = _phone_gap_threshold(priority_key)

    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    def push(code: str, row: dict[str, Any]) -> None:
        if code in seen:
            return
        seen.add(code)
        items.append({"code": code, **row})

    if bool(ts.get("runtime_degraded")) or pcat == ADMIN_PLATFORM_CATEGORY_DEGRADED:
        push(
            "runtime_degraded",
            {
                "title_ar": "توجد إشارات تدهور تشغيلي",
                "meaning_ar": "تدهور الثقة أو تصنيف المنصة يعني أن عدة مسارات قد تتأثر في الوقت نفسه.",
                "recommended_action_ar": "راجع الصحة التشغيلية للمنصة والمزود وهوية المتاجر.",
                "href": f"{HREF_RUNTIME}#overview",
                "link_label_ar": "صفحة التشغيل",
            },
        )

    prov_issue = (
        bool(de.get("repeated_provider_failures"))
        or rt.get("provider_runtime_ok") is False
        or pcat == ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION
    )
    if prov_issue:
        push(
            "provider_not_ready",
            {
                "title_ar": "واتساب / المزود يحتاج انتباه",
                "meaning_ar": "قد يتأثر الإرسال أو الجاهزية للمتاجر المعتمدة على المزود.",
                "recommended_action_ar": "راجع إعدادات مزود واتساب والقوالب المعتمدة.",
                "href": HREF_WHATSAPP_SETTINGS,
                "link_label_ar": "إعدادات واتساب",
            },
        )

    if bool(de.get("high_recent_duplicate_anomalies")) or bool(
        de.get("duplicate_guard_pressure")
    ):
        push(
            "duplicate_spike",
            {
                "title_ar": "ارتفاع محاولات التكرار أو الحماية منها",
                "meaning_ar": "زيادة محاولات الإرسال المكررة أو تدخل حارس التكرار يشير إلى ضغط على التدفق.",
                "recommended_action_ar": "راجع تدفق السلال والأحداث الأخيرة دون تعطيل التجربة.",
                "href": f"{HREF_RUNTIME}#duplicates",
                "link_label_ar": "تفاصيل التكرار",
            },
        )

    onboarding_press = (
        bool(de.get("onboarding_pressure"))
        or blocked_n > 0
        or pcat == ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED
    )
    if onboarding_press:
        push(
            "onboarding_blocked",
            {
                "title_ar": "المتجر لم يكمل التهيئة أو بعوائق إعداد",
                "meaning_ar": "متاجر بدون مسار تهيئة مكتمل قد لا تستفيد من الأتمتة بثقة.",
                "recommended_action_ar": "راجع خطوات التهيئة الأساسية ولوحة التاجر.",
                "href": HREF_ONBOARDING,
                "link_label_ar": "مسار الإعداد",
            },
        )

    if phone_gap >= phone_thr:
        push(
            "missing_phone_coverage",
            {
                "title_ar": "نسبة سلال بلا تغطية أرقام مرتفعة",
                "meaning_ar": "بيانات العملاء قد لا تتضمن أرقاماً موثوقة للتواصل.",
                "recommended_action_ar": "راجع مصدر أرقام العملاء أو طرق الالتقاط والودجت.",
                "href": f"{HREF_ONBOARDING}#capture",
                "link_label_ar": "التقاط البيانات",
            },
        )

    sandbox_signal = (
        pcat == ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY
        or (sandbox_ratio >= 0.4 and scanned >= 2)
    )
    if sandbox_signal:
        push(
            "sandbox_only",
            {
                "title_ar": "المتجر أو المنصة في وضع Sandbox",
                "meaning_ar": "الإرسال أو السياسات قد تبقى ضمن حدود التجربة وليس الإنتاج الكامل.",
                "recommended_action_ar": "فعّل الوضع الإنتاجي واستكمل المزود قبل التشغيل الحقيقي.",
                "href": HREF_PRODUCTION_MODE,
                "link_label_ar": "الإنتاج والمزود",
            },
        )

    if bool(de.get("repeated_lifecycle_pressure")):
        push(
            "lifecycle_pressure",
            {
                "title_ar": "ضغط على دورة حياة الاسترجاع",
                "meaning_ar": "تعارضات التوقيت أو الحالات قد تعطل تجربة متسقة للعميل.",
                "recommended_action_ar": "راجع التوقيت والقوالب وسجل الاسترجاع حديثاً.",
                "href": f"{HREF_RUNTIME}#lifecycle",
                "link_label_ar": "دورة الحياة",
            },
        )

    if bool(de.get("stale_session_signals")):
        push(
            "session_inconsistency",
            {
                "title_ar": "إشارات اتساق جلسة",
                "meaning_ar": "البيانات بين اللوحة والجلسة قد لا تتماشى بشكل مثالي.",
                "recommended_action_ar": "راجع مؤشرات الجلسة في لوحة التشغيل.",
                "href": f"{HREF_RUNTIME}#sessions",
                "link_label_ar": "الجلسات",
            },
        )

    if bool(de.get("impossible_transition_pressure")):
        push(
            "transition_conflict",
            {
                "title_ar": "تعارض في انتقال الحالات",
                "meaning_ar": "انتقالات غير متسقة قد تحتاج تدقيق تشغيلي سريع.",
                "recommended_action_ar": "افتح ملخص التشغيل وراجع الأحداث الأخيرة.",
                "href": f"{HREF_RUNTIME}#integrity",
                "link_label_ar": "تكامل الحالات",
            },
        )

    if bool(de.get("dashboard_payload_pressure")):
        push(
            "dashboard_payload",
            {
                "title_ar": "ضغط على بيانات اللوحة",
                "meaning_ar": "حمل غير متسق بين الواجهة والخلفية قد يربك التشخيص.",
                "recommended_action_ar": "راجع اتساق لوحة التحكم والمزامنة.",
                "href": f"{HREF_RUNTIME}#dashboard",
                "link_label_ar": "لوحة التشغيل",
            },
        )

    return items[:6]


def actionable_panel_meta(
    summary: dict[str, Any],
    *,
    priority_key: str,
    action_items: list[dict[str, Any]],
) -> dict[str, str]:
    """Copy for empty / calm states next to the actionable list."""
    if action_items:
        return {
            "empty_title_ar": "",
            "empty_subtitle_ar": "",
        }
    if not _allow_action_cards(summary, priority_key=priority_key):
        return {
            "empty_title_ar": "لا توجد إجراءات مطلوبة حاليًا.",
            "empty_subtitle_ar": "المنصة تعمل بشكل مستقر حسب الملخص التشغيلي.",
        }
    return {
        "empty_title_ar": "لا مسارات إجراء مُنشأة لهذا المزيج من المؤشرات.",
        "empty_subtitle_ar": "راجع الأقسام الأخرى أو انتظر بيانات أحدث.",
    }


__all__ = [
    "HREF_ONBOARDING",
    "HREF_PRODUCTION_MODE",
    "HREF_PROVIDERS",
    "HREF_RUNTIME",
    "HREF_WHATSAPP_SETTINGS",
    "actionable_panel_meta",
    "derive_actionable_operational_items",
]
