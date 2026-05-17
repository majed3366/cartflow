# -*- coding: utf-8 -*-
"""
Behavior-first merchant lifecycle narrative for normal recovery (presentation only).

Precedence is centralized in cartflow_merchant_lifecycle_precedence: behavioral
customer truth (purchase → reply → return) always beats scheduling / delay /
duplicate / automation narratives. Raw signals stay in merchant_lifecycle_internal.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from services.cartflow_merchant_lifecycle_precedence import (
    lifecycle_delay_scheduling_only,
    lifecycle_purchased_evidence,
    lifecycle_replied_evidence,
    lifecycle_returned_evidence,
    recovery_log_statuses_lower,
)


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def build_normal_recovery_merchant_lifecycle(
    *,
    phase_key: str,
    coarse: str,
    latest_log_status: Optional[str],
    blocker_key: Optional[str],
    behavioral: dict[str, Any],
    sent_ct: int,
    attempt_cap: int,
    recovery_log_statuses: Optional[Iterable[str]] = None,
    dashboard_customer_returned_track: bool = False,
    dashboard_return_intel_panel: bool = False,
) -> dict[str, Any]:
    pk = _norm(phase_key) or "pending_send"
    cr = _norm(coarse)
    ls = _norm(latest_log_status)
    bk = _norm(blocker_key)
    bh = behavioral if isinstance(behavioral, dict) else {}
    sent_n = max(0, int(sent_ct or 0))
    try:
        cap = max(1, int(attempt_cap or 1))
    except (TypeError, ValueError):
        cap = 1

    log_ss = recovery_log_statuses_lower(recovery_log_statuses)
    purchased = lifecycle_purchased_evidence(ls=ls, bk=bk, pk=pk, cr=cr, log_ss=log_ss)
    replied = lifecycle_replied_evidence(bh=bh, ls=ls, bk=bk, pk=pk, log_ss=log_ss)
    returned = lifecycle_returned_evidence(
        bh=bh,
        ls=ls,
        bk=bk,
        pk=pk,
        cr=cr,
        log_ss=log_ss,
        dashboard_return_track=bool(dashboard_customer_returned_track),
        dashboard_return_intel_panel=bool(dashboard_return_intel_panel),
    )

    internal: dict[str, Any] = {
        "latest_log_status": latest_log_status,
        "blocker_key": blocker_key,
        "phase_key": phase_key,
        "coarse": coarse,
        "recovery_log_statuses_seen": sorted(log_ss)[:48],
        "lifecycle_evidence_purchased": purchased,
        "lifecycle_evidence_replied": replied,
        "lifecycle_evidence_returned": returned,
    }

    def pack(
        primary: str,
        behavior_ar: str,
        outcome_ar: str,
        next_ar: str,
    ) -> dict[str, Any]:
        return {
            "merchant_lifecycle_primary_key": primary,
            "merchant_lifecycle_customer_behavior_ar": behavior_ar,
            "merchant_lifecycle_system_outcome_ar": outcome_ar,
            "merchant_lifecycle_next_action_ar": next_ar,
            "merchant_lifecycle_internal": internal,
        }

    # --- Strict precedence: purchase → reply → return → … (see precedence module) ---

    if purchased:
        return pack(
            "purchase_complete",
            "العميل أكمل الطلب",
            "تمت عملية الشراء — انتهت مهمة الاسترجاع.",
            "لا حاجة لرسائل استرجاع إضافية.",
        )

    if replied:
        return pack(
            "customer_replied",
            "العميل تفاعل مع الرسالة",
            "تفاعل العميل — بدأ النظام متابعة المسار المناسب.",
            "سيتابع النظام المسار المناسب تلقائياً.",
        )

    if returned:
        return pack(
            "customer_returned",
            "العميل عاد للموقع",
            "العميل عاد للموقع — أوقفنا الرسائل تلقائياً.",
            "لا حاجة لإجراء إضافي — النظام أوقف الرسائل تلقائياً.",
        )

    if bh.get("recovery_link_clicked") is True or pk == "behavioral_link_clicked":
        return pack(
            "link_clicked",
            "العميل عاد لمسار الشراء",
            "خفّفنا المتابعة الآلية بعد حركة واضحة منه.",
            "سيتابع النظام مسار الإتمام تلقائياً عند الإمكان.",
        )

    if bk == "whatsapp_failed" or ls == "whatsapp_failed":
        return pack(
            "channel_failed",
            "لم يكتمل وصول رسالة واتساب",
            "تعذّر إنهاء الإرسال آلياً في هذه المحاولة.",
            "قد تحتاج تدخل التاجر — تحقق من قناة الواتساب ثم أعد المحاولة.",
        )

    if (
        bk == "missing_customer_phone"
        or ls == "skipped_no_verified_phone"
        or pk == "blocked_missing_customer_phone"
    ):
        return pack(
            "needs_phone",
            "لا توجد قناة موثوقة للعميل بعد",
            "لا يمكن إرسال رسالة استرجاع قبل توفر الرقم.",
            "أضف أو فعّل رقم العميل ثم حدّث الصفحة.",
        )

    if bk == "missing_reason" or ls in (
        "skipped_missing_reason_tag",
        "skipped_missing_last_activity",
    ):
        return pack(
            "needs_reason",
            "ما زلنا بانتظار سياق واضح للسلة",
            "الرسالة الآلية تعتمد على سبب التردد أو النشاط.",
            "أكمل الودجت أو نشاط السلة المطلوب ثم أعد التحقق.",
        )

    if lifecycle_delay_scheduling_only(
        ls=ls,
        pk=pk,
        purchased=purchased,
        replied=replied,
        returned=returned,
    ):
        return pack(
            "delay_waiting",
            "بانتظار الوقت المناسب",
            "ننتظر تفاعل العميل — سيتابع النظام تلقائياً.",
            "لا حاجة لإجراء — سيتابع النظام تلقائياً.",
        )

    if sent_n >= 1 and pk in ("first_message_sent", "reminder_sent") and cr == "sent":
        return pack(
            "awaiting_customer_after_send",
            "أُرسلت رسالة استرجاع",
            "تم إرسال الرسالة — ننتظر تفاعل العميل.",
            "ننتظر تفاعل العميل — سيتابع النظام تلقائياً.",
        )

    if pk == "ignored":
        return pack(
            "ignored",
            "العميل لم يتفاعل أو طلب إيقاف المساعدة",
            "أوقفنا المتابعة الآلية لهذه السلة.",
            "يمكنك المراجعة يدوياً إن رغبت.",
        )

    if pk == "stopped_manual":
        return pack(
            "stopped_manual",
            "تم إيقاف المسار يدوياً",
            "لا إرسال آلي حتى تتغيّر الحالة.",
            "قد تحتاج تدخل التاجر — فعّل الاسترجاع من جديد إن كان ذلك مقصوداً.",
        )

    if sent_n == 0 and pk == "pending_send":
        if ls == "skipped_duplicate" or bk == "duplicate_attempt_blocked":
            return pack(
                "delay_waiting",
                "بانتظار الوقت المناسب",
                "ننتظر تفاعل العميل — سيتابع النظام تلقائياً.",
                "لا حاجة لإجراء — سيتابع النظام تلقائياً.",
            )
        if bk != "missing_customer_phone" and ls != "skipped_no_verified_phone":
            return pack(
                "no_engagement_yet",
                "العميل لم يتفاعل بعد",
                "ننتظر تفاعل العميل — سيتابع النظام تلقائياً.",
                "لا حاجة لإجراء — سيتابع النظام تلقائياً.",
            )

    if bk == "automation_disabled" or ls in (
        "skipped_attempt_limit",
        "skipped_reason_template_disabled",
    ):
        if sent_n >= cap >= 1:
            return pack(
                "attempts_exhausted",
                "اكتملت محاولات التواصل المخططة",
                "لا مزيد من الرسائل الآلية في هذه الدورة.",
                "قد تحتاج تدخل التاجر — راجع السلة أو حدود المحاولات في الإعدادات.",
            )
        return pack(
            "automation_paused",
            "بانتظار الوقت المناسب",
            "ننتظر تفاعل العميل — سيتابع النظام تلقائياً.",
            "راجع إعدادات السلال العادية إن أردت تغيير الإيقاف.",
        )

    if bk == "duplicate_attempt_blocked" or ls == "skipped_duplicate":
        if sent_n >= 1:
            return pack(
                "awaiting_customer_after_send",
                "تم التواصل مسبقاً",
                "تم إرسال الرسالة — ننتظر تفاعل العميل.",
                "ننتظر تفاعل العميل — سيتابع النظام تلقائياً.",
            )
        return pack(
            "delay_waiting",
            "بانتظار الوقت المناسب",
            "ننتظر تفاعل العميل — سيتابع النظام تلقائياً.",
            "لا حاجة لإجراء — سيتابع النظام تلقائياً.",
        )

    if ls in ("mock_sent", "sent_real"):
        return pack(
            "message_sent",
            "أُرسلت رسالة استرجاع",
            "تم إرسال الرسالة — ننتظر تفاعل العميل.",
            "ننتظر تفاعل العميل — سيتابع النظام تلقائياً.",
        )

    return pack(
        "in_progress",
        "مسار الاسترجاع قيد التشغيل",
        "المتابعة مستمرة — سيتابع النظام تلقائياً.",
        "حدّث الصفحة لاحقاً لآخر حالة.",
    )


def merchant_group_label_for_primary(primary_key: str) -> str:
    """Short badge line for legacy merchant_clarity_group_ar alignment."""
    k = _norm(primary_key)
    groups = {
        "purchase_complete": "اكتمال الشراء",
        "customer_replied": "تفاعل العميل",
        "customer_returned": "عودة للموقع",
        "link_clicked": "اهتمام بالشراء",
        "channel_failed": "يحتاج إجراء",
        "needs_phone": "يحتاج إجراء",
        "needs_reason": "يحتاج إعداد",
        "delay_waiting": "بانتظار التوقيت",
        "awaiting_customer_after_send": "بانتظار العميل",
        "ignored": "متوقف",
        "stopped_manual": "متوقف",
        "attempts_exhausted": "اكتمل المسار",
        "automation_paused": "متوقف حسب الإعداد",
        "pending_schedule": "بانتظار التوقيت",
        "no_engagement_yet": "بانتظار التفاعل",
        "message_sent": "تم الإرسال",
        "in_progress": "قيد التشغيل",
    }
    return groups.get(k, "مسار الاسترجاع")
