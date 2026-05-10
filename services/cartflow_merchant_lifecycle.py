# -*- coding: utf-8 -*-
"""
Behavior-first merchant lifecycle narrative for normal recovery (presentation only).

Single decision surface: derives one primary lifecycle story from phase, coarse status,
behavioral flags, and internal signals. Internal blocker keys and raw log statuses are
echoed only under merchant_lifecycle_internal for API/debug — not as the headline story.
"""
from __future__ import annotations

from typing import Any, Optional


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

    internal: dict[str, Any] = {
        "latest_log_status": latest_log_status,
        "blocker_key": blocker_key,
        "phase_key": phase_key,
        "coarse": coarse,
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

    # --- Strict precedence: one primary story (customer → decision → next) ---

    if (
        ls == "stopped_converted"
        or bk == "purchase_completed"
        or pk in ("stopped_purchase", "recovery_complete")
        or cr == "converted"
    ):
        return pack(
            "purchase_complete",
            "العميل أكمل الطلب",
            "تم إغلاق المتابعة.",
            "لا حاجة لرسائل استرجاع إضافية.",
        )

    if (
        bh.get("customer_replied") is True
        or pk == "behavioral_replied"
        or bk == "customer_replied"
        or ls in ("skipped_followup_customer_replied", "skipped_user_rejected_help")
    ):
        return pack(
            "customer_replied",
            "العميل تفاعل مع الرسالة",
            "ننتظر الرد الحالي.",
            "تابع المحادثة يدويًا عند الحاجة دون إغراق بالرسائل الآلية.",
        )

    if (
        bh.get("user_returned_to_site") is True
        or bh.get("customer_returned_to_site") is True
        or pk == "customer_returned"
        or cr == "returned"
        or ls == "skipped_anti_spam"
        or bk == "user_returned"
    ):
        return pack(
            "customer_returned",
            "العميل عاد للموقع",
            "أوقفنا الرسائل تلقائيًا.",
            "راجع السلة أو ساعد العميل عند الحاجة دون ضغط إضافي.",
        )

    if bh.get("recovery_link_clicked") is True or pk == "behavioral_link_clicked":
        return pack(
            "link_clicked",
            "العميل عاد لمسار الشراء",
            "خفّفنا المتابعة الآلية بعد حركة واضحة منه.",
            "راقب إتمام الطلب أو قدّم مساعدة خفيفة.",
        )

    if bk == "whatsapp_failed" or ls == "whatsapp_failed":
        return pack(
            "channel_failed",
            "لم يكتمل وصول رسالة واتساب",
            "تعذّر إنهاء الإرسال آلياً في هذه المحاولة.",
            "تحقق من قناة الواتساب ثم أعد المحاولة أو تواصل يدوياً.",
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

    if ls in ("queued", "skipped_delay_gate") or pk == "pending_second_attempt":
        return pack(
            "delay_waiting",
            "بانتظار الوقت المناسب",
            "سيتم التواصل لاحقًا ضمن الجدولة.",
            "لا حاجة لإجراء ما دامت المهلة ضمن إعداداتك.",
        )

    if sent_n >= 1 and pk in ("first_message_sent", "reminder_sent") and cr == "sent":
        return pack(
            "awaiting_customer_after_send",
            "أُرسلت رسالة استرجاع",
            "بانتظار خطوة أو رد من العميل.",
            "لا حاجة لإجراء إضافي ما دام العميل لم يتجاوب بعد.",
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
            "فعّل الاسترجاع من جديد إن كان ذلك مقصوداً.",
        )

    if sent_n == 0 and pk == "pending_send":
        if ls == "skipped_duplicate" or bk == "duplicate_attempt_blocked":
            return pack(
                "delay_waiting",
                "بانتظار الوقت المناسب",
                "سيتم التواصل لاحقًا ضمن الجدولة.",
                "لا حاجة لإجراء ما دامت المهلة ضمن إعداداتك.",
            )
        if bk != "missing_customer_phone" and ls != "skipped_no_verified_phone":
            return pack(
                "no_engagement_yet",
                "العميل لم يتفاعل بعد",
                "ننتظر المهلة المناسبة قبل محاولة جديدة.",
                "سنحاول التواصل لاحقًا.",
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
                "راقب السلة أو راجع الحدود في الإعدادات.",
            )
        return pack(
            "automation_paused",
            "بانتظار الوقت المناسب",
            "سيتم التواصل لاحقًا عندما يسمح المسار.",
            "راجع إعدادات السلال العادية إن أردت تغيير الإيقاف.",
        )

    if bk == "duplicate_attempt_blocked" or ls == "skipped_duplicate":
        if sent_n >= 1:
            return pack(
                "awaiting_customer_after_send",
                "تم التواصل مسبقاً",
                "لن نرسل رسائل متتابعة الآن.",
                "انتظر تفاعل العميل أو راجع السلة.",
            )
        return pack(
            "delay_waiting",
            "بانتظار الوقت المناسب",
            "سيتم التواصل لاحقًا ضمن الجدولة.",
            "لا حاجة لإجراء ما دامت المهلة ضمن إعداداتك.",
        )

    if ls in ("mock_sent", "sent_real"):
        return pack(
            "message_sent",
            "أُرسلت رسالة استرجاع",
            "الخطوة التالية عند العميل.",
            "لا حاجة لإجراء فوري.",
        )

    return pack(
        "in_progress",
        "نراقب السلة",
        "المتابعة مستمرة وفق الجدولة الحالية.",
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
