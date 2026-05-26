# -*- coding: utf-8 -*-
"""
Customer Lifecycle States v1 — dashboard truth layer (read-only on recovery execution).

Maps timeline + schedule + archive flags to merchant-facing lifecycle states.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db

STATE_ACTIVE = "active"
STATE_WAITING_FIRST_SEND = "waiting_first_send"
STATE_WAITING_CUSTOMER_REPLY = "waiting_customer_reply"
STATE_CUSTOMER_ENGAGED = "customer_engaged"
STATE_WAITING_NEXT_SCHEDULED = "waiting_next_scheduled"
STATE_NEEDS_INTERVENTION = "needs_intervention"
STATE_COMPLETED = "completed"
STATE_ARCHIVED = "archived"

LABEL_AR: dict[str, str] = {
    STATE_ACTIVE: "السلة نشطة",
    STATE_WAITING_FIRST_SEND: "بانتظار الإرسال",
    STATE_WAITING_CUSTOMER_REPLY: "بانتظار تفاعل العميل",
    STATE_CUSTOMER_ENGAGED: "تفاعل العميل — أرسل النظام متابعة",
    STATE_WAITING_NEXT_SCHEDULED: "بانتظار المتابعة التالية",
    STATE_NEEDS_INTERVENTION: "تحتاج تدخل",
    STATE_COMPLETED: "تمت الاستعادة",
    STATE_ARCHIVED: "مؤرشفة",
}

ROW_CLASS: dict[str, str] = {
    STATE_ACTIVE: "s-waiting",
    STATE_WAITING_FIRST_SEND: "s-waiting",
    STATE_WAITING_CUSTOMER_REPLY: "s-sent",
    STATE_CUSTOMER_ENGAGED: "s-attention",
    STATE_WAITING_NEXT_SCHEDULED: "s-sent",
    STATE_NEEDS_INTERVENTION: "s-attention",
    STATE_COMPLETED: "s-recovered",
    STATE_ARCHIVED: "s-recovered",
}

SENT_LOG = frozenset({"sent_real", "mock_sent"})
FAILED_LOG = frozenset({"whatsapp_failed", "failed_final", "failed_retry"})
INTERVENTION_LOG = frozenset(
    {
        "whatsapp_failed",
        "failed_final",
        "failed_retry",
        "vip_manual_handling",
        "skipped_user_rejected_help",
    }
)
EXHAUSTED_LOG = frozenset({"skipped_attempt_limit", "skipped_reason_template_disabled"})


@dataclass(frozen=True)
class CustomerLifecycleStateV1:
    state_key: str
    label_ar: str
    what_happened_ar: str
    system_did_ar: str
    what_next_ar: str
    merchant_needed_ar: str
    dashboard_action: str  # archive | reopen | none
    status_row_class: str
    next_followup_line_ar: str = ""
    completed_variant: str = ""  # recovered | purchased

    def to_payload_fields(self) -> dict[str, Any]:
        return {
            "customer_lifecycle_state": self.state_key,
            "customer_lifecycle_label_ar": self.label_ar,
            "customer_lifecycle_what_happened_ar": self.what_happened_ar,
            "customer_lifecycle_system_did_ar": self.system_did_ar,
            "customer_lifecycle_what_next_ar": self.what_next_ar,
            "customer_lifecycle_merchant_needed_ar": self.merchant_needed_ar,
            "customer_lifecycle_dashboard_action": self.dashboard_action,
            "customer_lifecycle_next_followup_line_ar": self.next_followup_line_ar
            or None,
            "customer_lifecycle_status_row_class": self.status_row_class,
            "customer_lifecycle_completed_variant": self.completed_variant or None,
        }


def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _log_set(raw: Any) -> frozenset[str]:
    if not raw:
        return frozenset()
    if isinstance(raw, frozenset):
        return raw
    out: set[str] = set()
    for item in raw:
        t = _norm(item)
        if t:
            out.add(t)
    return frozenset(out)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_eta_ar(delta_seconds: float) -> str:
    sec = max(0, int(delta_seconds))
    if sec < 3600:
        m = max(1, sec // 60)
        return f"{m} دقيقة" if m != 1 else "دقيقة"
    if sec < 86400:
        h = max(1, sec // 3600)
        if h == 1:
            return "ساعة"
        if h == 2:
            return "ساعتين"
        return f"{h} ساعات"
    days = max(1, sec // 86400)
    if days == 1:
        return "يوم"
    if days == 2:
        return "يومين"
    if days <= 10:
        return f"{days} أيام"
    return f"{days} يوماً"


def _timeline_flags(recovery_key: str) -> dict[str, bool]:
    rk = (recovery_key or "").strip()
    out = {
        "scheduled": False,
        "delay_started": False,
        "provider_sent": False,
        "customer_reply": False,
        "continuation_started": False,
    }
    if not rk:
        return out
    try:
        from services.recovery_truth_timeline_v1 import (  # noqa: PLC0415
            STATUS_CONTINUATION_STARTED,
            STATUS_CUSTOMER_REPLY,
            STATUS_DELAY_STARTED,
            STATUS_PROVIDER_SENT,
            STATUS_SCHEDULED,
            timeline_status_set,
        )

        ts = timeline_status_set(rk)
        out["scheduled"] = STATUS_SCHEDULED in ts
        out["delay_started"] = STATUS_DELAY_STARTED in ts
        out["provider_sent"] = STATUS_PROVIDER_SENT in ts
        out["customer_reply"] = STATUS_CUSTOMER_REPLY in ts
        out["continuation_started"] = STATUS_CONTINUATION_STARTED in ts
    except Exception:  # noqa: BLE001
        pass
    return out


def _next_schedule_due_at(recovery_key: str) -> Optional[datetime]:
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return None
    try:
        from models import RecoverySchedule

        from services.recovery_restart_survival import STATUS_SCHEDULED

        row = (
            db.session.query(RecoverySchedule.due_at)
            .filter(
                RecoverySchedule.recovery_key == rk,
                RecoverySchedule.status == STATUS_SCHEDULED,
            )
            .order_by(RecoverySchedule.due_at.asc())
            .first()
        )
        if not row or row[0] is None:
            return None
        due = row[0]
        if due.tzinfo is None:
            return due.replace(tzinfo=timezone.utc)
        return due.astimezone(timezone.utc)
    except SQLAlchemyError:
        db.session.rollback()
        return None


def _provider_sent(
    recovery_key: str,
    log_ss: frozenset[str],
    sent_count: int,
) -> bool:
    try:
        from services.recovery_truth_timeline_v1 import provider_send_proven

        return provider_send_proven(
            recovery_key, log_statuses=log_ss, sent_count=int(sent_count or 0)
        )
    except Exception:  # noqa: BLE001
        return bool(sent_count >= 1 or log_ss & SENT_LOG)


def _customer_replied(
    recovery_key: str,
    behavioral: Mapping[str, Any],
    coarse: str,
) -> bool:
    tl = _timeline_flags(recovery_key)
    if tl["customer_reply"]:
        return True
    if behavioral.get("customer_replied") is True:
        return True
    return _norm(coarse) in ("replied", "engaged", "clicked")


def _templates_exhausted(
    *,
    sent_count: int,
    attempt_cap: int,
    log_ss: frozenset[str],
) -> bool:
    cap = max(1, int(attempt_cap or 1))
    if int(sent_count or 0) >= cap:
        return True
    if log_ss & EXHAUSTED_LOG:
        return True
    return False


def _needs_intervention(
    *,
    log_ss: frozenset[str],
    phase_key: str,
    is_vip_lane: bool,
) -> bool:
    if is_vip_lane:
        return True
    if log_ss & INTERVENTION_LOG:
        return True
    if _norm(phase_key) in ("blocked_missing_customer_phone",):
        return False
    if log_ss & FAILED_LOG:
        return True
    if "vip_manual" in _norm(phase_key):
        return True
    return False


def _pack(
    state_key: str,
    *,
    what_happened: str,
    system_did: str,
    what_next: str,
    merchant_needed: str,
    dashboard_action: str,
    next_followup_line: str = "",
    completed_variant: str = "",
    label_override: str = "",
) -> CustomerLifecycleStateV1:
    label = label_override or LABEL_AR.get(state_key, state_key)
    if state_key == STATE_COMPLETED and completed_variant == "purchased":
        label = "تم الشراء"
    return CustomerLifecycleStateV1(
        state_key=state_key,
        label_ar=label,
        what_happened_ar=what_happened,
        system_did_ar=system_did,
        what_next_ar=what_next,
        merchant_needed_ar=merchant_needed,
        dashboard_action=dashboard_action,
        status_row_class=ROW_CLASS.get(state_key, "s-waiting"),
        next_followup_line_ar=next_followup_line,
        completed_variant=completed_variant,
    )


def classify_customer_lifecycle_state_v1(
    *,
    recovery_key: str = "",
    phase_key: str = "",
    coarse: str = "",
    sent_count: int = 0,
    attempt_cap: int = 1,
    log_statuses: Any = None,
    behavioral: Optional[Mapping[str, Any]] = None,
    purchase_truth: bool = False,
    cart_status: str = "",
    merchant_archived: bool = False,
    terminal_history_archived: bool = False,
    is_vip_lane: bool = False,
    has_phone: bool = True,
    next_attempt_due_at: Optional[str] = None,
) -> CustomerLifecycleStateV1:
    """Classify one cart row for dashboard lifecycle display."""
    rk = (recovery_key or "").strip()
    log_ss = _log_set(log_statuses)
    bh = behavioral if isinstance(behavioral, dict) else {}
    pk = (phase_key or "").strip()
    cnorm = _norm(coarse)
    cst = _norm(cart_status)
    cap = max(1, int(attempt_cap or 1))
    sent_n = int(sent_count or 0)
    tl = _timeline_flags(rk)
    now = _utc_now()

    if merchant_archived or terminal_history_archived:
        return _pack(
            STATE_ARCHIVED,
            what_happened="أُغلقت السلة من لوحة التاجر أو اكتمل مسار الرسائل دون تفاعل.",
            system_did="أوقفنا المتابعة الآلية لهذه السلة.",
            what_next="يمكنك إعادة فتحها للمراجعة فقط.",
            merchant_needed="لا",
            dashboard_action="reopen",
        )

    purchased = bool(
        purchase_truth
        or cst == "recovered"
        or cnorm == "converted"
        or "stopped_converted" in log_ss
    )
    if purchased:
        variant = "purchased" if purchase_truth or cnorm == "converted" else "recovered"
        return _pack(
            STATE_COMPLETED,
            what_happened="اكتملت عملية الشراء أو استُعيدت السلة.",
            system_did="أنهينا مهمة الاسترجاع لهذه السلة.",
            what_next="لا مزيد من رسائل الاسترجاع الآلية.",
            merchant_needed="لا",
            dashboard_action="none",
            completed_variant=variant,
        )

    if _needs_intervention(
        log_ss=log_ss, phase_key=pk, is_vip_lane=is_vip_lane
    ):
        return _pack(
            STATE_NEEDS_INTERVENTION,
            what_happened="تحتاج السلة تدخلاً خاصاً (VIP أو قناة أو معالجة يدوية).",
            system_did="أوقفنا الإرسال الآلي أو تعذّر إكماله.",
            what_next="راجع السلة واتخذ إجراءً يدوياً عند الحاجة.",
            merchant_needed="نعم",
            dashboard_action="archive",
        )

    replied = _customer_replied(rk, bh, cnorm)
    sent_proven = _provider_sent(rk, log_ss, sent_n)

    if replied and sent_proven:
        return _pack(
            STATE_CUSTOMER_ENGAGED,
            what_happened="ردّ العميل بعد رسالة الاسترجاع.",
            system_did="أرسل النظام متابعة الاعتراض تلقائياً."
            if tl["continuation_started"]
            else "يتابع النظام مسار التفاعل تلقائياً.",
            what_next="لا حاجة لرسائل إرسال إضافية — المتابعة آلية.",
            merchant_needed="لا",
            dashboard_action="archive",
        )

    exhausted = _templates_exhausted(
        sent_count=sent_n, attempt_cap=cap, log_ss=log_ss
    )

    due_at = _next_schedule_due_at(rk)
    if due_at is None and next_attempt_due_at:
        try:
            due_at = datetime.fromisoformat(
                str(next_attempt_due_at).replace("Z", "+00:00")
            )
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            due_at = None

    ignored_phase = pk == "ignored" or cnorm == "ignored"
    has_next_template = sent_n < cap
    delay_pending = due_at is not None and due_at > now

    if (
        (ignored_phase or "skipped_user_rejected_help" in log_ss)
        and sent_proven
        and has_next_template
        and delay_pending
        and not replied
    ):
        eta = _format_eta_ar((due_at - now).total_seconds())
        return _pack(
            STATE_WAITING_NEXT_SCHEDULED,
            what_happened="العميل لم يرد على الرسالة السابقة بعد.",
            system_did="أرسل النظام الرسالة الأولى (أو السابقة) وفق القالب.",
            what_next=f"رسالة تذكير مجدولة — {eta}",
            merchant_needed="لا",
            dashboard_action="archive",
            next_followup_line=f"المتابعة القادمة بعد: {eta}",
        )

    if sent_proven and not replied and not exhausted:
        return _pack(
            STATE_WAITING_CUSTOMER_REPLY,
            what_happened="أُرسلت رسالة استرجاع للعميل.",
            system_did="أرسل النظام رسالة واتساب وفق سبب التردد.",
            what_next="ننتظر تفاعل العميل.",
            merchant_needed="لا",
            dashboard_action="archive",
        )

    if exhausted and not replied:
        return _pack(
            STATE_ARCHIVED,
            what_happened="استُنفدت قوالب المتابعة دون رد من العميل.",
            system_did="أوقفنا الرسائل الآلية لهذه السلة.",
            what_next="يمكنك إعادة فتحها أو تركها في السجل.",
            merchant_needed="لا",
            dashboard_action="reopen",
        )

    if (
        tl["scheduled"]
        or tl["delay_started"]
        or pk in ("pending_send", "pending_second_attempt")
        or cnorm == "pending"
    ) and not sent_proven:
        if not has_phone:
            return _pack(
                STATE_NEEDS_INTERVENTION,
                what_happened="لا يوجد رقم موثوق لإكمال الإرسال.",
                system_did="لم يُرسل شيء بعد — بانتظار بيانات العميل.",
                what_next="أضف رقم العميل ليكمل النظام المسار.",
                merchant_needed="نعم",
                dashboard_action="archive",
            )
        return _pack(
            STATE_WAITING_FIRST_SEND,
            what_happened="السلة في انتظار أول رسالة استرجاع.",
            system_did="جدولنا المتابعة وفق التأخير المضبوط.",
            what_next="ستُرسل الرسالة تلقائياً عند حلول الموعد.",
            merchant_needed="لا",
            dashboard_action="archive",
        )

    return _pack(
        STATE_ACTIVE,
        what_happened="السلة قيد المتابعة في النظام.",
        system_did="يراقب النظام النشاط والسبب والتوقيت.",
        what_next="سيتابع النظام تلقائياً دون تدخل.",
        merchant_needed="لا",
        dashboard_action="archive",
    )


def attach_customer_lifecycle_state_v1(
    target: dict[str, Any],
    *,
    recovery_key: str = "",
    phase_key: str = "",
    coarse: str = "",
    sent_count: int = 0,
    attempt_cap: int = 1,
    log_statuses: Any = None,
    behavioral: Optional[Mapping[str, Any]] = None,
    purchase_truth: bool = False,
    cart_status: str = "",
    merchant_archived: bool = False,
    terminal_history_archived: bool = False,
    is_vip_lane: bool = False,
    has_phone: bool = True,
    abandoned_cart_id: Optional[int] = None,
    next_attempt_due_at: Optional[str] = None,
) -> CustomerLifecycleStateV1:
    """Attach lifecycle v1 fields; sync primary dashboard status label."""
    lc = classify_customer_lifecycle_state_v1(
        recovery_key=recovery_key,
        phase_key=phase_key,
        coarse=coarse,
        sent_count=sent_count,
        attempt_cap=attempt_cap,
        log_statuses=log_statuses,
        behavioral=behavioral,
        purchase_truth=purchase_truth,
        cart_status=cart_status,
        merchant_archived=merchant_archived,
        terminal_history_archived=terminal_history_archived,
        is_vip_lane=is_vip_lane,
        has_phone=has_phone,
        next_attempt_due_at=next_attempt_due_at,
    )
    target.update(lc.to_payload_fields())
    target["merchant_status_label_ar"] = lc.label_ar
    target["merchant_status_row_class"] = lc.status_row_class
    if lc.state_key == STATE_COMPLETED:
        target["merchant_cart_is_terminal"] = True
        target["merchant_cart_is_active"] = False
    elif lc.state_key == STATE_ARCHIVED:
        target["merchant_cart_is_terminal"] = False
        target["merchant_is_history_slice"] = True
    return lc


__all__ = [
    "LABEL_AR",
    "STATE_ACTIVE",
    "STATE_ARCHIVED",
    "STATE_COMPLETED",
    "STATE_CUSTOMER_ENGAGED",
    "STATE_NEEDS_INTERVENTION",
    "STATE_WAITING_CUSTOMER_REPLY",
    "STATE_WAITING_FIRST_SEND",
    "STATE_WAITING_NEXT_SCHEDULED",
    "CustomerLifecycleStateV1",
    "attach_customer_lifecycle_state_v1",
    "classify_customer_lifecycle_state_v1",
]
