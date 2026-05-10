# -*- coding: utf-8 -*-
"""
Additive merchant-facing clarity for recovery lifecycle (labels, grouping, hints).

Read-only copy layer: does not alter recovery, scheduling, blockers, onboarding
evaluation, provider logic, or observability internals.
"""
from __future__ import annotations

from typing import Any, Optional

# ─— Operational grouping (merchant Arabic) —───────────────────────────────────
GROUP_NEEDS_ACTION = "يحتاج إجراء"
GROUP_NORMAL = "يعمل بشكل طبيعي"
GROUP_STOPPED_CUSTOMER = "توقف بسبب تفاعل العميل"
GROUP_STOPPED_SETUP = "توقف بسبب إعداد ناقص"
GROUP_WAITING = "بانتظار تنفيذ الاسترجاع"
GROUP_PROTECTED = "حماية تشغيلية"

# Canonical log / outcome labels (concise)
LOG_LABELS: dict[str, str] = {
    "queued": "تم جدولة الاسترجاع — بانتظار وقت الإرسال",
    "skipped_delay_gate": "بانتظار المهلة قبل الإرسال",
    "mock_sent": "تم إرسال رسالة الاسترجاع",
    "sent_real": "تم إرسال رسالة الاسترجاع",
    "skipped_no_verified_phone": "بانتظار رقم العميل",
    "whatsapp_failed": "لم يكتمل الإرسال عبر قناة الواتساب",
    "skipped_duplicate": "تم منع محاولة مكررة",
    "skipped_anti_spam": "تم إيقاف الاسترجاع تلقائيًا بعد عودة العميل للموقع",
    "skipped_followup_customer_replied": "توقف الإرسال بعد تفاعل العميل",
    "skipped_user_rejected_help": "توقف الإرسال بعد رفض العميل المساعدة",
    "stopped_converted": "تم إيقاف الاسترجاع بعد الشراء",
    "skipped_missing_reason_tag": "بانتظار سبب التردد",
    "skipped_missing_last_activity": "بانتظار نشاط السلة",
    "skipped_attempt_limit": "توقف عند حد المحاولات",
    "skipped_reason_template_disabled": "قالب السبب معطّل — لم يُرسل",
}

BLOCKER_GROUPS: dict[str, tuple[str, str]] = {
    # blocker_key → (group_ar, roi_hint_ar)
    "missing_customer_phone": (
        GROUP_NEEDS_ACTION,
        "هذه السلة تحتاج رقم عميل حتى يبدأ الاسترجاع.",
    ),
    "missing_reason": (
        GROUP_STOPPED_SETUP,
        "أكمل اختيار سبب التردد من الودجت حتى تتكامل الرسائل.",
    ),
    "whatsapp_failed": (
        GROUP_NEEDS_ACTION,
        "تحقق من جاهزية قناة الواتساب والإعدادات قبل إعادة المحاولة.",
    ),
    "duplicate_attempt_blocked": (
        GROUP_PROTECTED,
        "منع التكرار يحمي العميل؛ إن وصلت رسالة مسبقاً فلا حاجة لضغط إضافي.",
    ),
    "user_returned": (
        GROUP_STOPPED_CUSTOMER,
        "العميل عاد للموقع، يفضّل عدم الضغط برسائل إضافية.",
    ),
    "customer_replied": (
        GROUP_STOPPED_CUSTOMER,
        "العميل تفاعل بالفعل، راقب المحادثة.",
    ),
    "purchase_completed": (GROUP_NORMAL, "اكتمال شراء جيد — لا إجراء مطلوب لهذه السلة."),
    "automation_disabled": (
        GROUP_STOPPED_SETUP,
        "راجع إعدادات التوقيت أو تفعيل القوالب في السلال العادية.",
    ),
}

WAITING_STATUSES = frozenset(
    {
        "queued",
        "skipped_delay_gate",
    }
)
SENT_STATUSES = frozenset({"mock_sent", "sent_real"})


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def status_waiting_not_failure(log_status: Optional[str]) -> bool:
    return _norm(log_status) in WAITING_STATUSES


def status_intentional_customer_stop(log_status: Optional[str], blocker_key: Optional[str]) -> bool:
    ls = _norm(log_status)
    bk = _norm(blocker_key)
    if bk in ("user_returned", "customer_replied", "purchase_completed"):
        return True
    if ls in (
        "skipped_anti_spam",
        "skipped_followup_customer_replied",
        "stopped_converted",
        "skipped_user_rejected_help",
    ):
        return True
    return False


BLOCKER_HEADLINES: dict[str, str] = {
    "missing_customer_phone": "بانتظار رقم العميل",
    "missing_reason": "سبب التردد غير مكتمل",
    "whatsapp_failed": "واتساب غير جاهز لإكمال الإرسال",
    "duplicate_attempt_blocked": "تم منع محاولة مكررة",
    "user_returned": "عاد العميل للموقع",
    "customer_replied": "العميل تفاعل مع الرسالة",
    "purchase_completed": "تم إيقاف الاسترجاع بعد الشراء",
    "automation_disabled": "الاسترجاع متوقف مؤقتاً",
}


def attach_merchant_clarity_to_normal_recovery_payload(
    payload: dict[str, Any],
    *,
    phase_key: str,
    coarse: str,
    latest_log_status: Optional[str],
    blocker_key: Optional[str],
    behavioral: dict[str, Any],
    sent_ct: int,
    phase_steps: list[dict[str, Any]],
) -> None:
    """Merge additive clarity keys into an existing normal-recovery dashboard dict."""
    ls = _norm(latest_log_status)
    bk = _norm(blocker_key)
    bh = behavioral if isinstance(behavioral, dict) else {}
    pk = _norm(phase_key) or "pending_send"
    if bk in ("duplicate_attempt_blocked", "automation_disabled"):
        if (
            bh.get("user_returned_to_site") is True
            or bh.get("customer_returned_to_site") is True
        ):
            bk = "user_returned"
        elif ls == "skipped_anti_spam":
            bk = "user_returned"
        elif bk == "automation_disabled" and pk == "customer_returned":
            bk = "user_returned"
    sent_n = int(sent_ct or 0)

    group_ar = GROUP_WAITING
    headline_ar = LOG_LABELS.get(ls, "متابعة مسار الاسترجاع")
    outcome_ar = "النظام يتابع السلة وفق الإعدادات الحالية."
    roi_hint_ar = ""
    waiting_normal: bool = False
    intentional_stop: bool = False

    if bk and bk in BLOCKER_GROUPS:
        group_ar, roi_hint_ar = BLOCKER_GROUPS[bk]
        headline_ar = BLOCKER_HEADLINES.get(bk, headline_ar)
        outcome_ar = LOG_LABELS.get(ls, outcome_ar) or outcome_ar
        if bk == "user_returned":
            outcome_ar = LOG_LABELS.get("skipped_anti_spam", outcome_ar)
        if ls in WAITING_STATUSES:
            outcome_ar = "المهلة أو الجدولة لا تزال ضمن النطاق الطبيعي."
        if bk in ("user_returned", "customer_replied", "purchase_completed"):
            intentional_stop = True
            waiting_normal = False
            if bk == "purchase_completed":
                group_ar = GROUP_NORMAL
        elif bk == "duplicate_attempt_blocked":
            waiting_normal = False
            intentional_stop = False
        elif bk in ("missing_customer_phone", "whatsapp_failed", "missing_reason"):
            waiting_normal = False
            intentional_stop = False
        elif bk == "automation_disabled":
            waiting_normal = False
            intentional_stop = False
    elif bh.get("customer_replied") is True and not bk:
        group_ar = GROUP_STOPPED_CUSTOMER
        headline_ar = "العميل تفاعل مع الرسالة"
        outcome_ar = "توقف الإرسال بعد التفاعل — سلوك مقصود وليس عطلًا."
        roi_hint_ar = BLOCKER_GROUPS["customer_replied"][1]
        intentional_stop = True
        waiting_normal = False
    elif bh.get("user_returned_to_site") is True and not bk:
        group_ar = GROUP_STOPPED_CUSTOMER
        headline_ar = "عاد العميل للموقع"
        outcome_ar = "تقليل المتابعة بعد العودة — لحماية تجربة العميل."
        roi_hint_ar = BLOCKER_GROUPS["user_returned"][1]
        intentional_stop = True
        waiting_normal = False
    elif ls in SENT_STATUSES and not bk:
        group_ar = GROUP_NORMAL
        headline_ar = "تم إرسال رسالة الاسترجاع"
        outcome_ar = "الرسالة صدرت بنجاح ضمن المسار الحالي."
        waiting_normal = False
        intentional_stop = False
    elif ls in WAITING_STATUSES or (ls == "queued" and sent_n == 0):
        group_ar = GROUP_WAITING
        headline_ar = LOG_LABELS.get(ls, "بانتظار تنفيذ الاسترجاع")
        outcome_ar = "هذا انتظار طبيعي ضمن المهلة — وليس فشلاً."
        roi_hint_ar = "لا حاجة لإجراء ما دامت المهلة ضمن الإعدادات."
        waiting_normal = True
        intentional_stop = False
    elif sent_n == 0 and pk == "pending_send" and not bk and ls in ("", "queued"):
        group_ar = GROUP_WAITING
        headline_ar = "بانتظار تنفيذ الاسترجاع"
        outcome_ar = "الجدولة أو المهلة قيد التقدم — ليس توقفاً خاطئاً."
        waiting_normal = True

    if _norm(coarse) in ("converted", "stopped") and pk in (
        "recovery_complete",
        "stopped_purchase",
    ) and not intentional_stop:
        group_ar = GROUP_NORMAL
        headline_ar = "تم إيقاف الاسترجاع بعد الشراء"
        outcome_ar = "اكتمال الشراء يوقف المسار كما هو متوقع."
        intentional_stop = True
        waiting_normal = False

    progress_chip = _progress_chip_from_steps(phase_steps)
    payload["merchant_clarity_group_ar"] = group_ar
    payload["merchant_clarity_headline_ar"] = headline_ar
    payload["merchant_clarity_outcome_ar"] = outcome_ar
    if roi_hint_ar:
        payload["merchant_clarity_roi_hint_ar"] = roi_hint_ar
    else:
        payload.pop("merchant_clarity_roi_hint_ar", None)
    payload["merchant_clarity_waiting_is_normal"] = bool(waiting_normal)
    payload["merchant_clarity_intentional_stop"] = bool(intentional_stop)
    if progress_chip:
        payload["merchant_clarity_progress_chip_ar"] = progress_chip


def _progress_chip_from_steps(phase_steps: list[dict[str, Any]]) -> str:
    chips: list[str] = []
    for step in phase_steps or []:
        if not isinstance(step, dict):
            continue
        if step.get("done"):
            lbl = str(step.get("label_ar") or "").strip()
            if lbl and lbl not in chips:
                chips.append(lbl)
        elif step.get("current"):
            lbl = str(step.get("label_ar") or "").strip()
            if lbl:
                chips.append(f"← {lbl}")
            break
        if len(chips) >= 5:
            break
    return " • ".join(chips)[:280]


def build_merchant_clarity_runtime_section(
    onboarding_runtime: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Compact, read-only supplement for health snapshots."""
    ob = onboarding_runtime if isinstance(onboarding_runtime, dict) else {}
    parts: list[str] = []
    if not bool(ob.get("onboarding_ready", True)):
        parts.append("أكمل إعداد التشغيل لقراءة أوضح لمسار الاسترجاع.")
    if bool(ob.get("sandbox_mode_active", False)):
        parts.append("وضع التجربة قد لا يعكس سلوك الإنتاج الفعلي.")
    return {
        "layer_version": "1",
        "merchant_clarity_focus": "operational_roi",
        "trust_supplement_ar": " ".join(parts).strip()[:400],
    }


def enrich_onboarding_visibility(
    visibility: dict[str, Any],
    evaluation: dict[str, Any],
) -> None:
    """Add one operational clarity line from onboarding evaluation (additive)."""
    ev = evaluation if isinstance(evaluation, dict) else {}
    vis = visibility
    parts: list[str] = []
    if bool(ev.get("sandbox_mode_active")):
        parts.append("التجربة التشغيلية للتحقق — الإنتاج يتطلب إكمال الإعداد.")
    if ev.get("blocking_steps"):
        parts.append("راجع البنود أعلاه؛ كل بند يوضح خطوة تشغيل واحدة.")
    line = " ".join(parts).strip()[:400]
    if line:
        vis["merchant_operational_clarity_ar"] = line


def enrich_runtime_trust_with_clarity(
    trust: dict[str, Any],
    clarity_runtime: Optional[dict[str, Any]] = None,
) -> None:
    """Attach merchant-safe supplement to trust dict (in-place, additive)."""
    cr = clarity_runtime if isinstance(clarity_runtime, dict) else {}
    sup = str(cr.get("trust_supplement_ar") or "").strip()
    if sup:
        trust["merchant_operational_clarity_ar"] = sup[:400]
