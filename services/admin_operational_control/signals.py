# -*- coding: utf-8 -*-
"""Derive active operational issues from existing read-only signals."""
from __future__ import annotations

from services.admin_operational_control.context import OperationalControlContext, OperationalIssue

_TIER_POTENTIAL = "potential"
_TIER_ACTUAL = "actual"

_IMPACT_NONE_AR = "لا يوجد أثر حالي"


def _count_degraded_stores(ctx: OperationalControlContext) -> int:
    summary = ctx.admin_summary
    rows = summary.get("store_operational_rows")
    if not isinstance(rows, list):
        return 0
    n = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        bucket = str(row.get("trust_bucket") or "")
        if bucket in ("degraded", "unstable"):
            n += 1
    return n


def _sandbox_active(ctx: OperationalControlContext) -> bool:
    ob = ctx.admin_summary.get("onboarding_runtime")
    if isinstance(ob, dict) and ob.get("sandbox_mode_active"):
        return True
    agg = ctx.admin_summary.get("aggregate_onboarding") or {}
    try:
        ratio = float(agg.get("sandbox_store_ratio") or 0)
        return ratio >= 0.85
    except (TypeError, ValueError):
        return False


def _provider_not_configured(ctx: OperationalControlContext) -> bool:
    prov = ctx.admin_rt.get("provider") if isinstance(ctx.admin_rt.get("provider"), dict) else {}
    return not bool(prov.get("configured"))


def build_operational_issues(ctx: OperationalControlContext) -> list[OperationalIssue]:
    issues: list[OperationalIssue] = []
    degraded_n = _count_degraded_stores(ctx)
    wa_fail = int(ctx.whatsapp_failed_24h or 0)

    if ctx.cart.get("slow_warning") or ctx.slow_cart_event_count > 0:
        aff = degraded_n if degraded_n > 0 else 0
        issues.append(
            OperationalIssue(
                code="cart_event_slow",
                active=True,
                tier=_TIER_ACTUAL,
                problem_ar="ارتفاع زمن cart-event",
                impact_ar="قد تتأخر رسائل الاسترداد وجدولة المتابعة",
                if_ignored_ar="تتراكم السلال في الانتظار دون إرسال في الوقت المناسب",
                affected_stores=aff,
                urgency="high" if ctx.slow_cart_event_count >= 3 else "medium",
                action_ar="راجع ضغط قاعدة البيانات ومسار cart-event",
                why_ar="رُصد بطء في معالجة cart-event في هذه العملية",
                detail_href="/admin/operational-health#issue-cart-event",
                detail_anchor="cart-event",
            )
        )

    if ctx.pool_timeout_count > 0:
        aff = degraded_n if degraded_n > 0 else 0
        issues.append(
            OperationalIssue(
                code="db_pool_timeout",
                active=True,
                tier=_TIER_ACTUAL,
                problem_ar="ضغط على مسبح الاتصالات (QueuePool)",
                impact_ar="قد تتعطل طلبات API واللوحة مؤقتاً",
                if_ignored_ar="اختناق عام يصل للتاجر كبطء أو فشل صامت",
                affected_stores=aff,
                urgency="high" if ctx.pool_timeout_count >= 2 else "medium",
                action_ar="راجع ضغط قاعدة البيانات",
                why_ar=f"رُصدت {ctx.pool_timeout_count} حالة انتهاء مهلة للمسبح",
                detail_href="/admin/operational-health#issue-db-pool",
                detail_anchor="db-pool",
            )
        )

    if ctx.background_failure_count > 0:
        aff = degraded_n if degraded_n > 0 else 0
        issues.append(
            OperationalIssue(
                code="background_task_failure",
                active=True,
                tier=_TIER_ACTUAL,
                problem_ar="إشارات فشل في المهام الخلفية أو الجدولة",
                impact_ar="قد لا تُرسَل رسائل الاسترداد المؤجلة",
                if_ignored_ar="فجوة بين نية النظام والتنفيذ الفعلي",
                affected_stores=aff,
                urgency="medium",
                action_ar="افحص سجل الأتمتة والمهام المؤجلة",
                why_ar=f"رُصد {ctx.background_failure_count} خطأ مهام خلفية في الذاكرة",
                detail_href="/admin/operations",
                detail_anchor="runtime",
            )
        )

    if wa_fail > 0:
        aff = max(degraded_n, 1) if degraded_n > 0 else 1
        issues.append(
            OperationalIssue(
                code="whatsapp_failure",
                active=True,
                tier=_TIER_ACTUAL,
                problem_ar="فشل إرسال واتساب",
                impact_ar="التجار لا يصلهم استرداد عبر القناة الرئيسية",
                if_ignored_ar="خسارة فرص استرداد مباشرة على السلال النشطة",
                affected_stores=aff,
                urgency="high" if wa_fail >= 3 else "medium",
                action_ar="تحقق من إعدادات المزود وافحص أخطاء WhatsApp",
                why_ar=f"هناك {wa_fail} فشل إرسال مسجّل خلال 24 ساعة"
                + (f" أثر على {aff} متجر (تقدير)" if aff > 0 else ""),
                detail_href="/admin/operations",
                detail_anchor="provider",
            )
        )

    if ctx.provider_unstable and wa_fail == 0:
        why = "رُصد عدم استقرار بالمزود لكن لم تظهر رسائل فاشلة حالياً"
        if _provider_not_configured(ctx):
            why = "المزود غير مُهيّأ بالكامل — وضع تجريبي أو إعداد ناقص"
        issues.append(
            OperationalIssue(
                code="provider_instability",
                active=True,
                tier=_TIER_POTENTIAL,
                problem_ar="عدم استقرار مزود واتساب (إشارة)",
                impact_ar=_IMPACT_NONE_AR,
                if_ignored_ar="قد يتحول لاحقاً إلى فشل إرسال فعلي",
                affected_stores=0,
                urgency="low",
                action_ar="تحقق من إعدادات المزود",
                why_ar=why,
                detail_href="/admin/operations",
                detail_anchor="provider",
            )
        )

    if not bool(ctx.admin_rt.get("recovery_runtime_ok")):
        issues.append(
            OperationalIssue(
                code="recovery_runtime_down",
                active=True,
                tier=_TIER_ACTUAL,
                problem_ar="مسار الاسترداد غير نشط",
                impact_ar="لا تُجدول رسائل استرداد جديدة",
                if_ignored_ar="توقف عملي لاسترداد السلال",
                affected_stores=max(degraded_n, 1),
                urgency="high",
                action_ar="تحقق من اتصال القاعدة وبيئة التشغيل",
                why_ar="مسار الاسترداد لا يمرّ فحص الجاهزية — راجع القاعدة والبيئة",
                detail_href="/admin/operations",
                detail_anchor="platform",
            )
        )

    trust = ctx.admin_summary.get("trust_signals_summary") or {}
    if trust.get("runtime_degraded"):
        issues.append(
            OperationalIssue(
                code="runtime_degraded",
                active=True,
                tier=_TIER_POTENTIAL,
                problem_ar="تدهور إشارات ثقة التشغيل",
                impact_ar=_IMPACT_NONE_AR,
                if_ignored_ar="قرارات تشغيل على معلومات غير موثوقة",
                affected_stores=0,
                urgency="low",
                action_ar="راجع مركز التشغيل — فئة المنصة والثقة",
                why_ar="إشارات الثقة التشغيلية ضعيفة دون فشل إرسال مُثبت بعد",
                detail_href="/admin/operations",
                detail_anchor="platform",
            )
        )

    if _sandbox_active(ctx):
        issues.append(
            OperationalIssue(
                code="sandbox_mode",
                active=True,
                tier=_TIER_POTENTIAL,
                problem_ar="وضع تجربة (Sandbox) نشط",
                impact_ar=_IMPACT_NONE_AR,
                if_ignored_ar="الأرقام قد لا تعكس الإنتاج",
                affected_stores=0,
                urgency="low",
                action_ar="راجع إعدادات الإنتاج والمزود",
                why_ar="أغلب المتاجر في وضع تجريبي — ليس خطر إنتاج مباشر",
                detail_href="/admin/operations",
                detail_anchor="platform",
            )
        )

    return issues
