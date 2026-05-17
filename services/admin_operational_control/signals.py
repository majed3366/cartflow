# -*- coding: utf-8 -*-
"""Derive active operational issues from existing read-only signals."""
from __future__ import annotations

from typing import Any

from services.admin_operational_control.context import OperationalControlContext, OperationalIssue


def _affected_from_summary(ctx: OperationalControlContext, *, floor: int = 1) -> int:
    summary = ctx.admin_summary
    rows = summary.get("store_operational_rows")
    if isinstance(rows, list) and rows:
        n = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            bucket = str(row.get("trust_bucket") or "")
            if bucket in ("degraded", "unstable", "partially_ready"):
                n += 1
        if n > 0:
            return n
    scanned = int(summary.get("stores_scanned_for_trust") or 0)
    if scanned > 0 and ctx.affected_stores_estimate > 0:
        return min(scanned, max(floor, ctx.affected_stores_estimate))
    return max(floor, ctx.affected_stores_estimate)


def build_operational_issues(ctx: OperationalControlContext) -> list[OperationalIssue]:
    issues: list[OperationalIssue] = []
    aff_default = _affected_from_summary(ctx)

    if ctx.cart.get("slow_warning"):
        n_slow = max(1, ctx.slow_cart_event_count)
        issues.append(
            OperationalIssue(
                code="cart_event_slow",
                active=True,
                problem_ar="ارتفاع زمن cart-event",
                impact_ar="قد تتأخر رسائل الاسترداد وجدولة المتابعة",
                if_ignored_ar="تتراكم السلال في الانتظار دون إرسال في الوقت المناسب",
                affected_stores=min(aff_default, max(1, n_slow)),
                urgency="high" if n_slow >= 3 else "medium",
                action_ar="راجع ضغط قاعدة البيانات ومسار cart-event",
                detail_href="/admin/operational-health#issue-cart-event",
                detail_anchor="cart-event",
            )
        )

    if ctx.pool_timeout_count > 0:
        issues.append(
            OperationalIssue(
                code="db_pool_timeout",
                active=True,
                problem_ar="ضغط على مسبح الاتصالات (QueuePool)",
                impact_ar="قد تتعطل طلبات API واللوحة مؤقتاً",
                if_ignored_ar="اختناق عام يصل للتاجر كبطء أو فشل صامت",
                affected_stores=aff_default,
                urgency="high" if ctx.pool_timeout_count >= 2 else "medium",
                action_ar="راجع ضغط قاعدة البيانات",
                detail_href="/admin/operational-health#issue-db-pool",
                detail_anchor="db-pool",
            )
        )

    if ctx.background_failure_count > 0 or ctx.bg.get("status") == "warn":
        issues.append(
            OperationalIssue(
                code="background_task_failure",
                active=True,
                problem_ar="إشارات فشل في المهام الخلفية أو الجدولة",
                impact_ar="قد لا تُرسَل رسائل الاسترداد المؤجلة",
                if_ignored_ar="فجوة بين نية النظام والتنفيذ الفعلي",
                affected_stores=aff_default,
                urgency="medium",
                action_ar="افحص سجل الأتمتة والمهام المؤجلة",
                detail_href="/admin/operations",
                detail_anchor="runtime",
            )
        )

    wa_fail = ctx.whatsapp_failed_24h
    if (wa_fail is not None and wa_fail > 0) or ctx.wa.get("status") == "warn":
        issues.append(
            OperationalIssue(
                code="whatsapp_failure",
                active=True,
                problem_ar="فشل إرسال واتساب أو ضعف المزود",
                impact_ar="التجار لا يصلهم استرداد عبر القناة الرئيسية",
                if_ignored_ar="خسارة فرص استرداد مباشرة على السلال النشطة",
                affected_stores=aff_default,
                urgency="high" if (wa_fail or 0) >= 3 else "medium",
                action_ar="تحقق من إعدادات المزود وافحص أخطاء WhatsApp",
                detail_href="/admin/operations",
                detail_anchor="provider",
            )
        )

    if ctx.provider_unstable:
        issues.append(
            OperationalIssue(
                code="provider_instability",
                active=True,
                problem_ar="عدم استقرار مزود واتساب",
                impact_ar="إرسال غير متوقع أو متقطع",
                if_ignored_ar="تذبذب ثقة التاجر في الأتمتة",
                affected_stores=aff_default,
                urgency="medium",
                action_ar="تحقق من إعدادات المزود",
                detail_href="/admin/operations",
                detail_anchor="provider",
            )
        )

    if not bool(ctx.admin_rt.get("recovery_runtime_ok")):
        issues.append(
            OperationalIssue(
                code="recovery_runtime_down",
                active=True,
                problem_ar="مسار الاسترداد غير نشط",
                impact_ar="لا تُجدول رسائل استرداد جديدة",
                if_ignored_ar="توقف عملي لاسترداد السلال",
                affected_stores=max(aff_default, 1),
                urgency="high",
                action_ar="تحقق من اتصال القاعدة وبيئة التشغيل",
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
                problem_ar="تدهور إشارات ثقة التشغيل",
                impact_ar="قد تظهر بيانات متضاربة في لوحات المتابعة",
                if_ignored_ar="قرارات تشغيل على معلومات غير موثوقة",
                affected_stores=aff_default,
                urgency="medium",
                action_ar="راجع مركز التشغيل — فئة المنصة والثقة",
                detail_href="/admin/operations",
                detail_anchor="platform",
            )
        )

    return issues
