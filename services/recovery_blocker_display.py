# -*- coding: utf-8 -*-
"""
Merchant-facing copy for operational recovery blockers (dashboard only).

Maps stable internal reasons and log statuses to Arabic labels without changing
recovery scheduling or send behavior.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

RecoveryBlockerSeverity = Literal["info", "warning", "error", "success"]


def _norm_key(raw: Optional[str]) -> str:
    return (raw or "").strip().lower().replace("-", "_")


def log_status_to_recovery_blocker_key(log_status: Optional[str]) -> Optional[str]:
    """
    Map CartRecoveryLog.status (lowercase) to a stable blocker key for display.
    Returns None when the status should not surface a blocker banner (success path).
    """
    s = _norm_key(log_status)
    if not s or s in ("mock_sent", "sent_real", "queued"):
        return None
    if s in ("skipped_no_verified_phone",):
        return "missing_customer_phone"
    if s in (
        "skipped_missing_reason_tag",
        "skipped_missing_last_activity",
    ):
        return "missing_reason"
    if s in ("whatsapp_failed",):
        return "whatsapp_failed"
    if s in ("skipped_duplicate",):
        return "duplicate_attempt_blocked"
    if s in ("skipped_anti_spam",):
        return "user_returned"
    if s in (
        "skipped_followup_customer_replied",
        "skipped_user_rejected_help",
    ):
        return "customer_replied"
    if s in ("stopped_converted",):
        return "purchase_completed"
    if s in (
        "skipped_delay_gate",
        "skipped_reason_template_disabled",
        "skipped_attempt_limit",
    ):
        return "automation_disabled"
    return "automation_disabled"


def get_recovery_blocker_display_state(blocker_reason: Optional[str]) -> dict[str, Any]:
    """
    Return a stable dict for dashboard/JSON. Unknown reasons fall back to automation_disabled
    (merchant-safe generic) to avoid leaking internal enum names.
    """
    k = _norm_key(blocker_reason)
    aliases = {
        "missing_phone": "missing_customer_phone",
        "no_verified_phone": "missing_customer_phone",
        "skipped_no_verified_phone": "missing_customer_phone",
        "already_sent": "duplicate_attempt_blocked",
        "max_attempts_reached": "duplicate_attempt_blocked",
    }
    k = aliases.get(k, k)

    states: dict[str, dict[str, Any]] = {
        "missing_customer_phone": {
            "key": "missing_customer_phone",
            "label_ar": "لا يوجد رقم عميل",
            "operational_hint_ar": "بانتظار رقم العميل",
            "description_ar": "لا يمكن إرسال رسائل الاسترجاع لهذه السلة حتى يتوفر رقم العميل.",
            "severity": "warning",
            "merchant_action_ar": "تحقق من مصدر رقم العميل أو تكامل المنصة.",
        },
        "missing_reason": {
            "key": "missing_reason",
            "label_ar": "سبب التردد غير معروف",
            "operational_hint_ar": "سبب التردد غير معروف",
            "description_ar": "لم يتم تحديد سبب التردد، لذلك لا يمكن اختيار الرسالة المناسبة.",
            "severity": "warning",
            "merchant_action_ar": "راجع إعدادات الودجت أو تدفق اختيار السبب.",
        },
        "whatsapp_failed": {
            "key": "whatsapp_failed",
            "label_ar": "فشل إرسال واتساب",
            "operational_hint_ar": "فشل إرسال واتساب",
            "description_ar": "حاول النظام الإرسال لكن مزود واتساب لم يقبل الرسالة أو فشل التسليم.",
            "severity": "error",
            "merchant_action_ar": "راجع إعدادات واتساب أو حالة المزود.",
        },
        "duplicate_attempt_blocked": {
            "key": "duplicate_attempt_blocked",
            "label_ar": "محاولة مكررة",
            "operational_hint_ar": "تم منع محاولة مكررة",
            "description_ar": (
                "تم منع محاولة مكررة، أو تم تجاهل تكرار الحدث، أو تم منع إرسال متكرر "
                "لحماية العميل — قد يعني ذلك أن الرسالة وصلت مسبقاً أو أن النظام كبح "
                "تكراراً غير مقصود."
            ),
            "severity": "info",
            "merchant_action_ar": "إذا سبق أن وصلت رسالة للعميل فلا حاجة لإجراء. وإلا راجع السجل أو تواصل يدوياً.",
        },
        "user_returned": {
            "key": "user_returned",
            "label_ar": "عاد العميل للموقع",
            "operational_hint_ar": "تم إيقاف الإرسال بعد عودة العميل",
            "description_ar": "تم إيقاف الضغط البيعي لأن العميل عاد للتصفح أو الإكمال.",
            "severity": "info",
            "merchant_action_ar": "راقب السلة أو ساعده عند الحاجة.",
        },
        "customer_replied": {
            "key": "customer_replied",
            "label_ar": "العميل رد",
            "operational_hint_ar": "تم إيقاف الإرسال بعد رد العميل",
            "description_ar": "تم إيقاف الرسائل الآلية لأن العميل دخل في محادثة.",
            "severity": "info",
            "merchant_action_ar": "راجع الرد المقترح وتابع المحادثة.",
        },
        "purchase_completed": {
            "key": "purchase_completed",
            "label_ar": "تم إيقاف الاسترجاع بعد الشراء",
            "operational_hint_ar": "تم إيقاف الاسترجاع بعد إتمام الشراء",
            "description_ar": "لا حاجة لمتابعة إضافية بعد إكمال الطلب.",
            "severity": "success",
            "merchant_action_ar": "لا يوجد إجراء مطلوب.",
        },
        "automation_disabled": {
            "key": "automation_disabled",
            "label_ar": "الاسترجاع متوقف",
            "operational_hint_ar": "الاسترجاع متوقف حسب الإعدادات أو الشروط",
            "description_ar": "إعدادات المتجر تمنع إرسال رسائل الاسترجاع حالياً أو لم تكتمل شروط الإرسال.",
            "severity": "warning",
            "merchant_action_ar": "فعّل الاسترجاع من إعدادات السلال العادية أو راجع المهلات والقوالب.",
        },
    }
    if k not in states:
        return dict(states["automation_disabled"])
    return dict(states[k])


def recovery_blocker_from_latest_log_status(log_status: Optional[str]) -> Optional[dict[str, Any]]:
    """Convenience: log status → full display dict, or None if no blocker."""
    bk = log_status_to_recovery_blocker_key(log_status)
    if bk is None:
        return None
    return get_recovery_blocker_display_state(bk)
