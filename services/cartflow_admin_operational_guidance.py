# -*- coding: utf-8 -*-
"""
Presentation-only operational guidance for the admin dashboard.

Maps existing `build_admin_operational_summary_readonly()` output to Arabic copy,
priority labels, and suggested actions. Does not compute health, trust, or
provider readiness — only interprets fields already present.
"""
from __future__ import annotations

from typing import Any

from services.cartflow_admin_operational_summary import (
    ADMIN_PLATFORM_CATEGORY_DEGRADED,
    ADMIN_PLATFORM_CATEGORY_HEALTHY,
    ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED,
    ADMIN_PLATFORM_CATEGORY_OPERATIONAL_ATTENTION,
    ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION,
    ADMIN_PLATFORM_CATEGORY_RUNTIME_WARNING,
    ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY,
)

PRIORITY_NORMAL = "normal"
PRIORITY_FOLLOW_UP = "follow_up"
PRIORITY_INTERVENTION = "intervention"
PRIORITY_CRITICAL = "critical"

_PRIORITY_LABEL_AR = {
    PRIORITY_NORMAL: "طبيعي",
    PRIORITY_FOLLOW_UP: "يحتاج متابعة",
    PRIORITY_INTERVENTION: "يحتاج تدخل",
    PRIORITY_CRITICAL: "خطر تشغيلي",
}

_PRIORITY_BADGE_CLASS = {
    PRIORITY_NORMAL: "bg-emerald-50 text-emerald-900 ring-emerald-200",
    PRIORITY_FOLLOW_UP: "bg-amber-50 text-amber-950 ring-amber-200",
    PRIORITY_INTERVENTION: "bg-orange-50 text-orange-950 ring-orange-200",
    PRIORITY_CRITICAL: "bg-rose-50 text-rose-950 ring-rose-200",
}


def _any_degradation(de: dict[str, Any]) -> bool:
    keys = (
        "repeated_provider_failures",
        "high_recent_duplicate_anomalies",
        "repeated_lifecycle_pressure",
        "dashboard_payload_pressure",
        "stale_session_signals",
        "duplicate_guard_pressure",
        "onboarding_pressure",
        "impossible_transition_pressure",
    )
    return any(bool(de.get(k)) for k in keys)


def derive_admin_operational_guidance(summary: dict[str, Any]) -> dict[str, Any]:
    """Deterministic copy from an operational summary dict; safe for HTML only."""
    ts = summary.get("trust_signals_summary") if isinstance(summary.get("trust_signals_summary"), dict) else {}
    de = summary.get("degradation_flags") if isinstance(summary.get("degradation_flags"), dict) else {}
    rt = summary.get("admin_runtime_summary_reuse") if isinstance(summary.get("admin_runtime_summary_reuse"), dict) else {}
    agg = summary.get("aggregate_onboarding") if isinstance(summary.get("aggregate_onboarding"), dict) else {}
    hints = summary.get("admin_operational_hints_ar") if isinstance(summary.get("admin_operational_hints_ar"), list) else []
    pcat = str(summary.get("platform_admin_category") or "").strip()

    degraded_runtime = bool(ts.get("runtime_degraded"))
    warn_runtime = bool(ts.get("runtime_warning"))
    any_de = _any_degradation(de)
    has_hints = bool(hints)

    scanned = int(agg.get("total_stores_scanned") or 0)
    blocked_n = int(agg.get("onboarding_blocked_stores") or 0)
    sandbox_n = int(agg.get("sandbox_mode_stores") or 0)
    phone_gap = int(summary.get("stores_missing_phone_coverage_estimate") or 0)
    tb = agg.get("trust_bucket_counts") if isinstance(agg.get("trust_bucket_counts"), dict) else {}
    unstableish = int(tb.get("degraded", 0)) + int(tb.get("unstable", 0))

    # --- Priority (ordered rules) ---
    priority = PRIORITY_NORMAL
    if degraded_runtime or pcat == ADMIN_PLATFORM_CATEGORY_DEGRADED or bool(
        de.get("impossible_transition_pressure")
    ):
        priority = PRIORITY_CRITICAL
    elif (
        pcat == ADMIN_PLATFORM_CATEGORY_OPERATIONAL_ATTENTION
        or pcat == ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED
        or bool(de.get("repeated_provider_failures"))
        or bool(de.get("duplicate_guard_pressure"))
        or (
            pcat == ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION
            and rt.get("provider_runtime_ok") is False
        )
    ):
        priority = PRIORITY_INTERVENTION
    elif (
        warn_runtime
        or pcat
        in (
            ADMIN_PLATFORM_CATEGORY_RUNTIME_WARNING,
            ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION,
            ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY,
        )
        or any_de
        or has_hints
    ):
        priority = PRIORITY_FOLLOW_UP

    summary_strip: list[str] = []
    if priority == PRIORITY_CRITICAL:
        summary_strip.append("توجد إشارات تدهور تشغيلي تحتاج مراجعة فورية.")
    elif priority == PRIORITY_INTERVENTION:
        summary_strip.append("هناك حالات تحتاج تدخّلاً تشغيلياً موجهاً.")
    elif priority == PRIORITY_FOLLOW_UP:
        summary_strip.append("الوضع مقبول عموماً مع نقاط تستحق متابعة.")
    else:
        summary_strip.append("المنصة تبدو ضمن نطاق طبيعي حسب المؤشرات الحالية.")

    if sandbox_n > 0 and scanned > 0:
        summary_strip.append("هناك متاجر تعمل في وضع Sandbox فقط.")
    if blocked_n > 0:
        summary_strip.append("بعض المتاجر لم تكمل التهيئة بعد أو تواجه عوائق إعداد.")
    if unstableish > 0:
        summary_strip.append("بعض المتاجر لا تزال غير جاهزة تشغيلياً.")

    # Dedup while preserving order
    seen: set[str] = set()
    summary_strip = [x for x in summary_strip if not (x in seen or seen.add(x))][:4]

    platform_interpretation = ""
    if degraded_runtime:
        platform_interpretation = (
            "مؤشرات الثقة العامة تشير إلى تدهور في الاستقرار التشغيلي — راجع المزود والهوية والتكامل."
        )
    elif pcat == ADMIN_PLATFORM_CATEGORY_HEALTHY and not any_de and not has_hints:
        platform_interpretation = "لا توجد مؤشرات خطر عالية حاليًا ضمن ملخص المنصة."
    elif pcat == ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY:
        platform_interpretation = (
            "غالبية المتاجر الممسوحة في وضع تجريبي — الإنتاج الحقيقي يتطلب إكمال المزود والإعداد."
        )
    elif pcat == ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED:
        platform_interpretation = (
            "نسبة المتاجر ذات عوائق الإعداد مرتفعة — أولوية العمل هي إزالة العوائق التشغيلية للمتاجر."
        )
    elif pcat == ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION:
        platform_interpretation = (
            "جاهزية المزود على مستوى المنصة تحتاج انتباهاً لتفادي تأثر الإرسال."
        )
    else:
        platform_interpretation = (
            "الوضع مزيج من مؤشرات الإعداد والتشغيل — راجع التحذيرات أدناه لمعرفة الأولوية."
        )

    critical_attention: list[str] = []
    if priority in (PRIORITY_CRITICAL, PRIORITY_INTERVENTION):
        critical_attention.append(
            "هذه الفقرة تلخص أهم ما يستحق الانتباه قبل التفاصيل."
        )
    if degraded_runtime or bool(de.get("impossible_transition_pressure")):
        critical_attention.append(
            "تم رصد تدهور أو تعارض في مسار التشغيل — تعامل معه كأولوية قبل التوسع."
        )
    if bool(de.get("repeated_provider_failures")):
        critical_attention.append(
            "تكرار مشكلات المزود قد يعني اعتمادات أو قوالب أو حدود إرسال — راجع حساب واتساب."
        )
    if bool(de.get("high_recent_duplicate_anomalies")):
        critical_attention.append(
            "ارتفعت محاولات التكرار أو منع الإزعاج — راجع سجل الأتمتة لضمان تجربة عملاء سليمة."
        )
    if blocked_n > 0 and scanned > 0:
        critical_attention.append("بعض المتاجر بحاجة لاستكمال الإعداد قبل الاعتماد على الأتمتة.")

    if not critical_attention and priority == PRIORITY_NORMAL:
        critical_attention.append("لا توجد مشاكل تشغيلية بارزة في ملخص الأولوية الحالي.")

    actions: list[dict[str, str]] = []
    if bool(de.get("repeated_provider_failures")) or (
        pcat == ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION and not rt.get("provider_runtime_ok", True)
    ):
        actions.append(
            {
                "meaning_ar": "قد يتأثر إرسال الاسترجاع للمتاجر المعتمدة على المزود.",
                "step_ar": "راجع إعدادات واتساب للمتاجر المتأثرة والقوالب المعتمدة.",
            }
        )
    if phone_gap > 0:
        actions.append(
            {
                "meaning_ar": "بيانات العملاء قد لا تتضمن أرقماً موثوقة للتواصل.",
                "step_ar": "تحقق من مصدر أرقام العملاء والودجت وجمع الحقول في المتجر.",
            }
        )
    if blocked_n > 0:
        actions.append(
            {
                "meaning_ar": "متاجر لم تُكمِل بعد مسار التهيئة التشغيلية.",
                "step_ar": "أكمل إعداد المتجر أو راجع لوحة التاجر لإزالة العوائق.",
            }
        )
    if sandbox_n > 0 and scanned >= 2:
        actions.append(
            {
                "meaning_ar": "عدد من المتاجر ما زال في وضع التجربة فقط.",
                "step_ar": "خطط للانتقال إلى الإنتاج عند جاهزية المزود والسياسات.",
            }
        )

    onboarding_interpretation = (
        f"{blocked_n} متجراً بعوائق إعداد ضمن {scanned} ممسوحاً — "
        "النسبة تعكس الضغط التشغيلي وليس جودة المنتج."
        if scanned
        else "لم يُمسح متجر بعد — أضف متاجراً أو تحقق من الاتصال بقاعدة البيانات."
    )

    prov_ok = bool(rt.get("provider_runtime_ok", True))
    rec_ok = bool(rt.get("recovery_runtime_ok", True))
    id_ok = bool(rt.get("identity_runtime_ok", True))
    dash_ok = bool(rt.get("dashboard_runtime_ok", True))

    if prov_ok and pcat != ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION:
        provider_line = "مزود المنصة يبدو ضمن المؤشرات المقبولة."
    else:
        provider_line = (
            "مزود المنصة يشير إلى حاجة لمراجعة الربط أو الاعتمادات أو القوالب المعتمدة."
        )

    runtime_bits: list[str] = []
    if rec_ok and id_ok and dash_ok:
        runtime_bits.append("مسارات الاسترجاع والهوية واللوحة ضمن المؤشرات الحالية.")
    else:
        if not rec_ok:
            runtime_bits.append("مسار الاسترجاع يحتاج متابعة.")
        if not id_ok:
            runtime_bits.append("اتساق الهوية يحتاج متابعة.")
        if not dash_ok:
            runtime_bits.append("اتساق لوحة التحكم يحتاج متابعة.")

    provider_runtime_interpretation = (provider_line + " " + " ".join(runtime_bits)).strip()

    trends_interpretation = ""
    if any_de:
        trends_interpretation = (
            "هناك ضغط تشغيلي مُعلَن في نافذة الرصد — استعمل التفاصيل كمؤشر اتجاه وليس حكماً نهائياً."
        )
    else:
        trends_interpretation = "لم يُرصد تدهور تشغيلي مُعلَن في مجموعة الضغط الحالية."

    degradation_empty_ar = (
        "لا توجد إشارات تعارض أو ضغط مُفعّل في هذه اللحظة — مؤشر جيد للتشغيل اليومي."
        if not any_de
        else ""
    )
    counts = (
        summary.get("anomaly_visibility", {}).get("recent_type_counts")
        if isinstance(summary.get("anomaly_visibility"), dict)
        else None
    )
    if not isinstance(counts, dict):
        counts = {}
    anomaly_empty_ar = (
        "لا توجد أعداد شذوذ حديثة في الذاكرة المؤقتة — لا يعني غياباً كاملاً للأحداث."
        if not counts
        else "الأعداد أدناه معلوماتية؛ راجع السياق التشغيلي عند المتابعة."
    )

    cards_zero_messages = {
        "onboarding_blocked": "لا متاجر بحالة عائق إعداد ضمن المسح الحالي.",
        "phone_gap": "لا متاجر مُعلَنة بسلّة دون تغطية أرقام في هذا التقدير.",
        "trust_low": "لا متاجر ضعيفة/غير مستقرة ضمن المسح الحالي.",
    }

    return {
        "priority_key": priority,
        "priority_label_ar": _PRIORITY_LABEL_AR[priority],
        "priority_badge_class": _PRIORITY_BADGE_CLASS[priority],
        "summary_strip": summary_strip,
        "platform_interpretation_ar": platform_interpretation,
        "critical_attention_ar": critical_attention[:6],
        "action_guidance_ar": actions[:5],
        "onboarding_interpretation_ar": onboarding_interpretation,
        "provider_runtime_interpretation_ar": provider_runtime_interpretation.strip(),
        "trends_interpretation_ar": trends_interpretation,
        "degradation_empty_message_ar": degradation_empty_ar,
        "anomaly_empty_message_ar": anomaly_empty_ar,
        "cards_zero_messages_ar": cards_zero_messages,
        "has_operational_hints": has_hints,
    }


__all__ = [
    "PRIORITY_CRITICAL",
    "PRIORITY_FOLLOW_UP",
    "PRIORITY_INTERVENTION",
    "PRIORITY_NORMAL",
    "derive_admin_operational_guidance",
]
