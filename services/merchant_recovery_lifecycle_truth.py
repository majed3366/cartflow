# -*- coding: utf-8 -*-
"""عرض قراءة فقط لحقيقة مسار الاسترجاع في لوحة التاجر — دون تغيير سلوك الإرسال."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from services.cartflow_merchant_lifecycle import build_normal_recovery_merchant_lifecycle
from services.cartflow_merchant_lifecycle_precedence import (
    lifecycle_delay_scheduling_only,
    lifecycle_purchased_evidence,
    lifecycle_replied_evidence,
    lifecycle_returned_evidence,
    recovery_log_statuses_lower,
)

log = logging.getLogger("cartflow")

_SENT_STATUSES = frozenset({"sent_real", "mock_sent"})
_MESSAGE_PREVIEW_MAX = 220


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def _log_matches_abandoned_cart(ac: Any, lg: Any) -> bool:
    sess = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
    zid = (getattr(ac, "zid_cart_id", None) or "").strip()[:255]
    ls = (getattr(lg, "session_id", None) or "").strip()[:512]
    lc = (getattr(lg, "cart_id", None) or "").strip()[:255]
    if sess and ls == sess:
        return True
    if zid and lc == zid:
        return True
    if zid and ls == zid:
        return True
    return False


def matched_recovery_logs(ac: Any, logs: Optional[Iterable[Any]]) -> list[Any]:
    if not logs:
        return []
    seen: set[int] = set()
    out: list[Any] = []
    for lg in logs:
        lid = int(getattr(lg, "id", 0) or 0)
        if lid and lid in seen:
            continue
        if _log_matches_abandoned_cart(ac, lg):
            if lid:
                seen.add(lid)
            out.append(lg)
    return out


def _dt_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    try:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except (TypeError, ValueError, AttributeError):
        return None


def _format_sent_at_ar(dt: Any) -> str:
    iso = _dt_iso(dt)
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return iso[:19]


def _message_preview(text: Optional[str]) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    if len(raw) <= _MESSAGE_PREVIEW_MAX:
        return raw
    return raw[: _MESSAGE_PREVIEW_MAX - 1] + "…"


def _not_sent_reason_key(
    *,
    latest_status: str,
    phase_key: str,
    has_phone: bool,
    has_reason: bool,
    purchased: bool,
    returned: bool,
    sent_ct: int,
) -> str:
    ls = _norm(latest_status)
    pk = _norm(phase_key)
    if purchased or ls == "stopped_converted":
        return "purchased"
    if returned or ls in (
        "returned_to_site",
        "skipped_anti_spam",
        "skipped_followup_customer_replied",
    ) or pk in ("customer_returned", "stopped_purchase"):
        return "stopped_returned"
    if ls in _SENT_STATUSES:
        return "sent"
    if ls == "whatsapp_failed":
        return "failed"
    if ls in ("skipped_no_verified_phone",) or pk == "blocked_missing_customer_phone":
        return "missing_phone"
    if ls in ("skipped_missing_reason_tag", "skipped_missing_last_activity"):
        return "missing_reason"
    if ls in ("queued", "skipped_delay", "skipped_duplicate") or pk in (
        "pending_send",
        "pending_second_attempt",
    ):
        return "waiting_delay"
    if sent_ct < 1 and not has_phone:
        return "missing_phone"
    if sent_ct < 1 and not has_reason:
        return "missing_reason"
    if sent_ct < 1:
        return "waiting_delay"
    return "unknown"


_NOT_SENT_REASON_AR: dict[str, str] = {
    "waiting_delay": "بانتظار المهلة أو الجدولة",
    "missing_phone": "لا يوجد رقم عميل موثوق للإرسال",
    "missing_reason": "لم يُحدَّد سبب التردد بعد",
    "stopped_returned": "توقّف الإرسال بعد عودة العميل",
    "purchased": "اكتمل الشراء",
    "failed": "تعذّر إرسال واتساب",
    "unknown": "لم تُرسل رسالة بعد",
}


def _resolve_lifecycle_status(
    *,
    purchased: bool,
    returned: bool,
    replied: bool,
    message_sent: bool,
    scheduling: bool,
    missing_data: bool,
    failed: bool,
) -> str:
    if purchased:
        return "purchased"
    if returned:
        return "returned_to_site"
    if replied:
        return "engaged"
    if message_sent:
        return "message_sent"
    if failed:
        return "failed"
    if missing_data:
        return "missing_data"
    if scheduling:
        return "scheduled"
    return "scheduled"


_LIFECYCLE_STATUS_LABEL_AR: dict[str, str] = {
    "purchased": "اكتمل الشراء",
    "returned_to_site": "عاد للموقع",
    "engaged": "تفاعل مع الرسالة",
    "message_sent": "تم إرسال رسالة",
    "scheduled": "مجدول / بانتظار",
    "missing_data": "بيانات ناقصة",
    "failed": "تعذّر الإرسال",
}


def _log_truth_gap(
    *,
    cart_id: str,
    session_id: str,
    available: dict[str, Any],
    missing_field: str,
) -> None:
    try:
        av_parts = ",".join(f"{k}={v}" for k, v in available.items() if v is not None)
        line = (
            "[MERCHANT LIFECYCLE TRUTH] gap "
            f"cart_id={(cart_id or '-')[:80]} "
            f"session_id={(session_id or '-')[:80]} "
            f"available={av_parts or '-'} "
            f"missing={missing_field}"
        )
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def build_merchant_recovery_lifecycle_truth(
    *,
    ac: Any,
    phase_key: str,
    coarse: str,
    sent_ct: int,
    log_statuses: Optional[Iterable[str]],
    behavioral: dict[str, Any],
    reason_tag: Optional[str],
    has_phone: bool,
    latest_log: Any = None,
    matched_logs: Optional[list[Any]] = None,
    attempt_cap: int = 1,
) -> dict[str, Any]:
    """حقول موحّدة للوحة التاجر — قراءة فقط من سجلات ومؤشرات موجودة."""
    bh = behavioral if isinstance(behavioral, dict) else {}
    log_ss = recovery_log_statuses_lower(log_statuses)
    ls = _norm(getattr(latest_log, "status", None) if latest_log is not None else "")
    pk = _norm(phase_key)
    cr = _norm(coarse)

    purchased = lifecycle_purchased_evidence(ls=ls, bk="", pk=pk, cr=cr, log_ss=log_ss)
    if not purchased and _norm(getattr(ac, "status", None)) == "recovered":
        purchased = True
    replied = lifecycle_replied_evidence(bh=bh, ls=ls, bk="", pk=pk, log_ss=log_ss)
    returned = lifecycle_returned_evidence(
        bh=bh,
        ls=ls,
        bk="",
        pk=pk,
        cr=cr,
        log_ss=log_ss,
        dashboard_return_track=False,
        dashboard_return_intel_panel=False,
    )

    sent_logs: list[Any] = []
    if matched_logs:
        sent_logs = [
            lg
            for lg in matched_logs
            if _norm(getattr(lg, "status", None)) in _SENT_STATUSES
        ]
    latest_sent = None
    if sent_logs:
        latest_sent = max(
            sent_logs,
            key=lambda r: (
                getattr(r, "sent_at", None)
                or getattr(r, "created_at", None)
                or datetime.min.replace(tzinfo=timezone.utc),
                int(getattr(r, "id", 0) or 0),
            ),
        )

    message_sent = sent_ct > 0 or bool(sent_logs) or ls in _SENT_STATUSES
    scheduling = lifecycle_delay_scheduling_only(
        ls=ls,
        pk=pk,
        purchased=purchased,
        replied=replied,
        returned=returned,
    ) and not message_sent
    failed = ls == "whatsapp_failed"
    has_reason = bool((reason_tag or "").strip())
    missing_data = (not has_phone or not has_reason) and sent_ct < 1 and not message_sent

    lifecycle_status = _resolve_lifecycle_status(
        purchased=purchased,
        returned=returned,
        replied=replied,
        message_sent=message_sent,
        scheduling=scheduling,
        missing_data=missing_data and not failed,
        failed=failed,
    )
    lifecycle_label_ar = _LIFECYCLE_STATUS_LABEL_AR.get(
        lifecycle_status, "مسار الاسترجاع"
    )

    preview = ""
    sent_at_iso: Optional[str] = None
    sent_at_display = ""
    if latest_sent is not None:
        preview = _message_preview(getattr(latest_sent, "message", None))
        sent_at_iso = _dt_iso(
            getattr(latest_sent, "sent_at", None)
            or getattr(latest_sent, "created_at", None)
        )
        sent_at_display = _format_sent_at_ar(
            getattr(latest_sent, "sent_at", None)
            or getattr(latest_sent, "created_at", None)
        )

    whatsapp_status = "sent" if message_sent else "not_sent"
    if failed:
        whatsapp_status = "failed"

    purchase_completed_at: Optional[str] = None
    if purchased:
        purchase_completed_at = _dt_iso(getattr(ac, "recovered_at", None))
        if not purchase_completed_at and latest_log is not None and ls == "stopped_converted":
            purchase_completed_at = _dt_iso(getattr(latest_log, "created_at", None))

    not_sent_key = _not_sent_reason_key(
        latest_status=ls,
        phase_key=pk,
        has_phone=has_phone,
        has_reason=has_reason,
        purchased=purchased,
        returned=returned,
        sent_ct=int(sent_ct),
    )

    if replied and not purchased:
        whatsapp_line_ar = "تفاعل العميل — بدأ النظام متابعة المسار المناسب."
    elif returned and not purchased:
        whatsapp_line_ar = "العميل عاد للموقع — أوقفنا الرسائل تلقائياً."
    elif purchased:
        whatsapp_line_ar = "تمت عملية الشراء — انتهت مهمة الاسترجاع."
    elif message_sent:
        whatsapp_line_ar = "تم إرسال الرسالة — ننتظر تفاعل العميل."
        if preview:
            whatsapp_line_ar += f" ({preview})"
        if sent_at_display:
            whatsapp_line_ar += f" ({sent_at_display})"
    elif scheduling or not_sent_key == "waiting_delay":
        whatsapp_line_ar = "ننتظر تفاعل العميل — سيتابع النظام تلقائياً."
    elif failed:
        whatsapp_line_ar = "قد تحتاج تدخل التاجر — تعذّر إرسال واتساب."
    else:
        reason_ar = _NOT_SENT_REASON_AR.get(not_sent_key, _NOT_SENT_REASON_AR["unknown"])
        if not_sent_key in ("missing_phone", "missing_reason"):
            whatsapp_line_ar = f"قد تحتاج تدخل التاجر — {reason_ar}"
        else:
            whatsapp_line_ar = f"لم تُرسل رسالة بعد — {reason_ar}"

    return_line_ar = ""
    if returned and not purchased:
        return_line_ar = "العميل عاد للموقع — أوقفنا الرسائل تلقائيًا."

    purchase_line_ar = ""
    if purchased:
        purchase_line_ar = "تمت عملية الشراء — انتهت مهمة الاسترجاع."

    lifecycle_pack = build_normal_recovery_merchant_lifecycle(
        phase_key=phase_key,
        coarse=coarse,
        latest_log_status=getattr(latest_log, "status", None) if latest_log else None,
        blocker_key=None,
        behavioral=bh,
        sent_ct=int(sent_ct),
        attempt_cap=max(1, int(attempt_cap or 1)),
        recovery_log_statuses=log_ss,
        dashboard_customer_returned_track=returned,
        dashboard_return_intel_panel=False,
    )

    cart_id = str(getattr(ac, "zid_cart_id", None) or "").strip()[:255]
    session_id = str(getattr(ac, "recovery_session_id", None) or "").strip()[:512]

    out: dict[str, Any] = {
        "cart_id": cart_id or None,
        "session_id": session_id or None,
        "reason_tag": (reason_tag or "").strip()[:64] or None,
        "customer_phone_present": bool(has_phone),
        "recovery_status": cr or "pending",
        "whatsapp_status": whatsapp_status,
        "message_preview": preview or None,
        "last_sent_message_body": preview or None,
        "sent_at": sent_at_iso,
        "sent_at_display_ar": sent_at_display or None,
        "returned_to_site": bool(returned and not purchased),
        "purchased": bool(purchased),
        "purchase_completed_at": purchase_completed_at,
        "lifecycle_status": lifecycle_status,
        "lifecycle_label_ar": lifecycle_label_ar,
        "merchant_whatsapp_line_ar": whatsapp_line_ar,
        "merchant_return_line_ar": return_line_ar or None,
        "merchant_purchase_line_ar": purchase_line_ar or None,
        "merchant_lifecycle_primary_key": lifecycle_pack.get("merchant_lifecycle_primary_key"),
        "merchant_lifecycle_customer_behavior_ar": lifecycle_pack.get(
            "merchant_lifecycle_customer_behavior_ar"
        ),
        "merchant_lifecycle_system_outcome_ar": lifecycle_pack.get(
            "merchant_lifecycle_system_outcome_ar"
        ),
        "merchant_lifecycle_next_action_ar": lifecycle_pack.get(
            "merchant_lifecycle_next_action_ar"
        ),
    }

    if message_sent and not preview:
        _log_truth_gap(
            cart_id=cart_id,
            session_id=session_id,
            available={"whatsapp_status": whatsapp_status, "sent_ct": sent_ct},
            missing_field="message_preview",
        )
    if lifecycle_status == "scheduled" and not ls and sent_ct < 1:
        _log_truth_gap(
            cart_id=cart_id,
            session_id=session_id,
            available={"lifecycle_status": lifecycle_status, "phase_key": pk},
            missing_field="latest_log_status",
        )
    return out


def attach_merchant_recovery_lifecycle_truth(
    target: dict[str, Any],
    *,
    ac: Any,
    phase_key: str,
    coarse: str,
    sent_ct: int,
    log_statuses: Optional[Iterable[str]],
    behavioral: dict[str, Any],
    reason_tag: Optional[str],
    has_phone: bool,
    latest_log: Any = None,
    matched_logs: Optional[list[Any]] = None,
    attempt_cap: int = 1,
) -> None:
    truth = build_merchant_recovery_lifecycle_truth(
        ac=ac,
        phase_key=phase_key,
        coarse=coarse,
        sent_ct=sent_ct,
        log_statuses=log_statuses,
        behavioral=behavioral,
        reason_tag=reason_tag,
        has_phone=has_phone,
        latest_log=latest_log,
        matched_logs=matched_logs,
        attempt_cap=attempt_cap,
    )
    target.update(truth)
