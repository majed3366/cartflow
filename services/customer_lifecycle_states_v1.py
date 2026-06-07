# -*- coding: utf-8 -*-
"""
Customer Lifecycle States v1 — dashboard truth layer (read-only on recovery execution).

Maps timeline + schedule + archive flags to merchant-facing lifecycle states.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from sqlalchemy.exc import SQLAlchemyError

from extensions import db

log = logging.getLogger(__name__)

STATE_ACTIVE = "active"
STATE_WAITING_FIRST_SEND = "waiting_first_send"
STATE_WAITING_CUSTOMER_REPLY = "waiting_customer_reply"
STATE_CUSTOMER_ENGAGED = "customer_engaged"
STATE_CUSTOMER_REPLY = "customer_reply"
STATE_RETURN_TO_SITE = "return_to_site"
STATE_WAITING_PURCHASE_WINDOW = "waiting_purchase_window"
STATE_WAITING_NEXT_SCHEDULED = "waiting_next_scheduled"
STATE_NEEDS_INTERVENTION = "needs_intervention"
STATE_COMPLETED = "completed"
STATE_ARCHIVED = "archived"
STATE_RECOVERY_FOLLOWUP_COMPLETE = "recovery_followup_complete"

LABEL_AR: dict[str, str] = {
    STATE_ACTIVE: "السلة نشطة",
    STATE_WAITING_FIRST_SEND: "بانتظار الإرسال",
    STATE_WAITING_CUSTOMER_REPLY: "بانتظار تفاعل العميل",
    STATE_CUSTOMER_REPLY: "رد العميل",
    STATE_CUSTOMER_ENGAGED: "تفاعل العميل — أرسل النظام متابعة",
    STATE_RETURN_TO_SITE: "عاد العميل للموقع — نراقب هل يكمل الطلب",
    STATE_WAITING_PURCHASE_WINDOW: "عاد العميل للموقع — أوقفنا المتابعة مؤقتًا",
    STATE_WAITING_NEXT_SCHEDULED: "بانتظار المتابعة التالية",
    STATE_NEEDS_INTERVENTION: "تحتاج تدخل",
    STATE_COMPLETED: "تمت الاستعادة",
    STATE_ARCHIVED: "مؤرشفة",
    STATE_RECOVERY_FOLLOWUP_COMPLETE: "انتهت متابعة CartFlow",
}

ROW_CLASS: dict[str, str] = {
    STATE_ACTIVE: "s-waiting",
    STATE_WAITING_FIRST_SEND: "s-waiting",
    STATE_WAITING_CUSTOMER_REPLY: "s-sent",
    STATE_CUSTOMER_REPLY: "s-attention",
    STATE_CUSTOMER_ENGAGED: "s-attention",
    STATE_RETURN_TO_SITE: "s-sent",
    STATE_WAITING_PURCHASE_WINDOW: "s-sent",
    STATE_WAITING_NEXT_SCHEDULED: "s-sent",
    STATE_NEEDS_INTERVENTION: "s-attention",
    STATE_COMPLETED: "s-recovered",
    STATE_ARCHIVED: "s-archived",
    STATE_RECOVERY_FOLLOWUP_COMPLETE: "s-sent",
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
RETURN_TO_SITE_LOG = frozenset({"returned_to_site", "user_returned"})

UI_FILTER_ALL = "all"
UI_FILTER_SENT = "sent"
UI_FILTER_ATTENTION = "attention"
UI_FILTER_RECOVERED = "recovered"
UI_FILTER_NOPHONE = "nophone"
UI_FILTER_WAITING = "waiting"
UI_FILTER_ARCHIVED = "archived"

PRIMARY_WAITING = "waiting"
PRIMARY_SENT = "sent"
PRIMARY_NEEDS_FOLLOWUP = "needs_followup"
PRIMARY_CUSTOMER_ENGAGED = "customer_engaged"
PRIMARY_CUSTOMER_REPLY = "customer_reply"
PRIMARY_RETURN_TO_SITE = "return_to_site"
PRIMARY_RECOVERED = "recovered"
PRIMARY_NO_PHONE = "no_phone"
PRIMARY_ARCHIVED = "archived"


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
            "customer_lifecycle_is_archived_visual": self.state_key == STATE_ARCHIVED,
        }


def lifecycle_state_to_filter_bucket(state_key: str) -> str:
    sk = (state_key or "").strip().lower()
    if sk in (STATE_ACTIVE, STATE_WAITING_FIRST_SEND):
        return UI_FILTER_WAITING
    if sk in (
        STATE_WAITING_CUSTOMER_REPLY,
        STATE_WAITING_NEXT_SCHEDULED,
        STATE_RETURN_TO_SITE,
        STATE_WAITING_PURCHASE_WINDOW,
        STATE_RECOVERY_FOLLOWUP_COMPLETE,
    ):
        return UI_FILTER_SENT
    if sk in (STATE_CUSTOMER_REPLY, STATE_CUSTOMER_ENGAGED, STATE_NEEDS_INTERVENTION):
        return UI_FILTER_ATTENTION
    if sk == STATE_COMPLETED:
        return UI_FILTER_RECOVERED
    if sk == STATE_ARCHIVED:
        return UI_FILTER_ARCHIVED
    return UI_FILTER_WAITING


def lifecycle_state_to_primary_bucket(state_key: str) -> str:
    sk = (state_key or "").strip().lower()
    if sk in (STATE_ACTIVE, STATE_WAITING_FIRST_SEND):
        return PRIMARY_WAITING
    if sk in (STATE_WAITING_CUSTOMER_REPLY, STATE_RECOVERY_FOLLOWUP_COMPLETE):
        return PRIMARY_SENT
    if sk == STATE_WAITING_NEXT_SCHEDULED:
        return PRIMARY_NEEDS_FOLLOWUP
    if sk == STATE_CUSTOMER_REPLY:
        return PRIMARY_CUSTOMER_REPLY
    if sk == STATE_CUSTOMER_ENGAGED:
        return PRIMARY_CUSTOMER_ENGAGED
    if sk in (STATE_RETURN_TO_SITE, STATE_WAITING_PURCHASE_WINDOW):
        return PRIMARY_RETURN_TO_SITE
    if sk == STATE_NEEDS_INTERVENTION:
        return PRIMARY_NEEDS_FOLLOWUP
    if sk == STATE_COMPLETED:
        return PRIMARY_RECOVERED
    if sk == STATE_ARCHIVED:
        return PRIMARY_ARCHIVED
    return PRIMARY_WAITING


def lifecycle_state_visible_tabs(state_key: str) -> tuple[str, ...]:
    b = lifecycle_state_to_filter_bucket(state_key)
    if b == UI_FILTER_ARCHIVED:
        return (UI_FILTER_ALL,)
    return (UI_FILTER_ALL, b)


def lifecycle_filter_counts_from_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        UI_FILTER_ALL: len(rows),
        UI_FILTER_SENT: 0,
        UI_FILTER_ATTENTION: 0,
        UI_FILTER_RECOVERED: 0,
        UI_FILTER_NOPHONE: 0,
        UI_FILTER_WAITING: 0,
    }
    for row in rows:
        sk = str(row.get("customer_lifecycle_state") or "").strip().lower()
        tabs = lifecycle_state_visible_tabs(sk)
        if UI_FILTER_WAITING in tabs:
            counts[UI_FILTER_WAITING] = int(counts[UI_FILTER_WAITING]) + 1
        if UI_FILTER_SENT in tabs:
            counts[UI_FILTER_SENT] = int(counts[UI_FILTER_SENT]) + 1
        if UI_FILTER_ATTENTION in tabs:
            counts[UI_FILTER_ATTENTION] = int(counts[UI_FILTER_ATTENTION]) + 1
        if UI_FILTER_RECOVERED in tabs:
            counts[UI_FILTER_RECOVERED] = int(counts[UI_FILTER_RECOVERED]) + 1
        if UI_FILTER_NOPHONE in tabs:
            counts[UI_FILTER_NOPHONE] = int(counts[UI_FILTER_NOPHONE]) + 1
    return counts


def lifecycle_nav_badge_waiting_count(rows: list[dict[str, Any]]) -> int:
    n = 0
    for row in rows:
        sk = str(row.get("customer_lifecycle_state") or "").strip().lower()
        if lifecycle_state_to_filter_bucket(sk) == UI_FILTER_WAITING:
            n += 1
    return n


def lifecycle_truth_consistency_for_row(row: Mapping[str, Any]) -> tuple[bool, str]:
    sk = str(row.get("customer_lifecycle_state") or "").strip().lower()
    if not sk:
        return False, "missing_customer_lifecycle_state"
    tab_expected = lifecycle_state_to_filter_bucket(sk)
    bucket = str(row.get("merchant_cart_bucket") or "").strip().lower()
    if tab_expected != bucket:
        return False, f"bucket_mismatch expected={tab_expected} got={bucket or '-'}"
    chip = str(
        row.get("customer_lifecycle_label_ar")
        or row.get("merchant_status_label_ar")
        or ""
    ).strip()
    if not chip:
        return False, "missing_chip_label"
    arch_vis = bool(row.get("customer_lifecycle_is_archived_visual"))
    if arch_vis and sk != STATE_ARCHIVED:
        return False, "archived_visual_without_archived_state"
    if sk == STATE_ARCHIVED and not arch_vis:
        return False, "archived_state_without_archived_visual"
    if sk in (STATE_RETURN_TO_SITE, STATE_WAITING_PURCHASE_WINDOW) and (
        "تفاعل العميل" in chip or "رد العميل" in chip
    ):
        return False, "return_state_with_reply_chip"
    if sk == STATE_WAITING_PURCHASE_WINDOW and "أوقفنا المتابعة" not in chip:
        return False, "purchase_window_chip_mismatch"
    if sk == STATE_WAITING_FIRST_SEND and "الإرسال" not in chip:
        return False, "waiting_send_chip_mismatch"
    return True, "ok"


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


_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"


def _ar_num(value: int) -> str:
    n = max(0, int(value or 0))
    return "".join(_AR_DIGITS[int(ch)] for ch in str(n))


def _format_eta_ar(delta_seconds: float) -> str:
    """Minutes for sub-hour and non-whole-hour delays (e.g. 90m); hours only when exact."""
    sec = max(0, int(delta_seconds))
    if sec >= 86400 and sec % 86400 == 0:
        days = sec // 86400
        if days == 1:
            return "يوم"
        if days == 2:
            return "يومين"
        if days <= 10:
            return f"{_ar_num(days)} أيام"
        return f"{_ar_num(days)} يوماً"
    if sec >= 3600 and sec % 3600 == 0:
        h = sec // 3600
        if h == 1:
            return "ساعة"
        if h == 2:
            return "ساعتين"
        return f"{_ar_num(h)} ساعات"
    m = max(1, sec // 60)
    return f"{_ar_num(m)} دقيقة" if m != 1 else "دقيقة"


def _timeline_flags(
    recovery_key: str,
    *,
    timeline_statuses: Optional[frozenset[str]] = None,
) -> dict[str, bool]:
    rk = (recovery_key or "").strip()
    out = {
        "scheduled": False,
        "delay_started": False,
        "provider_sent": False,
        "customer_reply": False,
        "continuation_started": False,
    }
    if not rk and not timeline_statuses:
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

        ts = (
            timeline_statuses
            if timeline_statuses is not None
            else timeline_status_set(rk)
        )
        out["scheduled"] = STATUS_SCHEDULED in ts
        out["delay_started"] = STATUS_DELAY_STARTED in ts
        out["provider_sent"] = STATUS_PROVIDER_SENT in ts
        out["customer_reply"] = STATUS_CUSTOMER_REPLY in ts
        out["continuation_started"] = STATUS_CONTINUATION_STARTED in ts
    except Exception:  # noqa: BLE001
        pass
    return out


def _scheduled_effective_delay_seconds(recovery_key: str) -> Optional[float]:
    """Configured delay on the pending schedule row (template truth, not live countdown)."""
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return None
    try:
        from models import RecoverySchedule

        from services.recovery_restart_survival import STATUS_SCHEDULED

        row = (
            db.session.query(RecoverySchedule.effective_delay_seconds)
            .filter(
                RecoverySchedule.recovery_key == rk,
                RecoverySchedule.status == STATUS_SCHEDULED,
            )
            .order_by(RecoverySchedule.due_at.asc())
            .first()
        )
        if row and row[0] is not None:
            return float(row[0])
    except SQLAlchemyError:
        db.session.rollback()
    return None


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
    *,
    timeline_statuses: Optional[frozenset[str]] = None,
) -> bool:
    try:
        from services.recovery_truth_timeline_v1 import provider_send_proven

        return provider_send_proven(
            recovery_key,
            log_statuses=log_ss,
            sent_count=int(sent_count or 0),
            timeline_statuses=timeline_statuses,
        )
    except Exception:  # noqa: BLE001
        return bool(sent_count >= 1 or log_ss & SENT_LOG)


def _customer_replied(
    recovery_key: str,
    *,
    behavioral: Optional[Mapping[str, Any]] = None,
    timeline_statuses: Optional[frozenset[str]] = None,
) -> bool:
    """WhatsApp/webhook reply only — canonical timeline ``customer_reply``."""
    bh = behavioral if isinstance(behavioral, dict) else {}
    if bh.get("customer_replied") is True:
        return True
    rk = (recovery_key or "").strip()
    if not rk:
        return False
    try:
        from services.recovery_truth_timeline_v1 import (  # noqa: PLC0415
            STATUS_CUSTOMER_REPLY,
            customer_reply_proven,
        )

        if timeline_statuses is not None:
            return STATUS_CUSTOMER_REPLY in timeline_statuses
        return customer_reply_proven(rk, behavioral=bh)
    except Exception:  # noqa: BLE001
        return False


def _return_to_site_detected(
    *,
    recovery_key: str,
    phase_key: str,
    coarse: str,
    log_ss: frozenset[str],
    behavioral: Mapping[str, Any],
) -> bool:
    if _customer_replied(recovery_key):
        return False
    pk = (phase_key or "").strip()
    cnorm = _norm(coarse)
    if pk == "customer_returned" or cnorm == "returned":
        return True
    if log_ss & RETURN_TO_SITE_LOG:
        return True
    if behavioral.get("customer_returned_to_site") is True:
        return True
    if behavioral.get("user_returned_to_site") is True:
        return True
    return False


def _recovery_sequence_complete(
    *,
    sent_count: int,
    attempt_cap: int,
    log_ss: frozenset[str],
) -> bool:
    """All configured recovery sends finished (no further automated messages pending)."""
    cap = max(1, int(attempt_cap or 1))
    sent_n = int(sent_count or 0)
    if sent_n >= cap:
        return True
    if "skipped_attempt_limit" in log_ss:
        return True
    return False


def _parse_utc_datetime(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _last_provider_sent_at_utc(
    *,
    recovery_key: str,
    last_provider_sent_at: Optional[str] = None,
    matched_logs: Optional[Sequence[Any]] = None,
) -> Optional[datetime]:
    """Latest provider send timestamp for post-sequence engagement window."""
    parsed = _parse_utc_datetime(last_provider_sent_at)
    if parsed is not None:
        return parsed
    best: Optional[datetime] = None
    for lg in matched_logs or ():
        try:
            from services.vip_operational_truth_v1 import (  # noqa: PLC0415
                is_vip_merchant_only_recovery_log,
            )

            if is_vip_merchant_only_recovery_log(lg):
                continue
        except Exception:  # noqa: BLE001
            pass
        st = _norm(getattr(lg, "status", None))
        if st not in SENT_LOG:
            continue
        t = getattr(lg, "sent_at", None) or getattr(lg, "created_at", None)
        ts = _parse_utc_datetime(t)
        if ts is None:
            continue
        if best is None or ts > best:
            best = ts
    if best is not None:
        return best
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return None
    try:
        from models import CartRecoveryLog  # noqa: PLC0415
        from services.vip_operational_truth_v1 import (  # noqa: PLC0415
            vip_merchant_alert_reason_tag_sql_exclusion,
        )

        rows = (
            db.session.query(CartRecoveryLog.sent_at, CartRecoveryLog.created_at)
            .filter(
                CartRecoveryLog.recovery_key == rk,
                CartRecoveryLog.status.in_(tuple(SENT_LOG)),
            )
            .filter(vip_merchant_alert_reason_tag_sql_exclusion())
            .order_by(CartRecoveryLog.id.desc())
            .limit(24)
            .all()
        )
        for sent_at, created_at in rows:
            ts = _parse_utc_datetime(sent_at) or _parse_utc_datetime(created_at)
            if ts is None:
                continue
            if best is None or ts > best:
                best = ts
    except SQLAlchemyError:
        db.session.rollback()
    return best


def _post_sequence_engagement_window_expired(
    *,
    last_sent_at: Optional[datetime],
    now: datetime,
) -> bool:
    if last_sent_at is None:
        return False
    try:
        from services.normal_recovery_merchant_view_config import (  # noqa: PLC0415
            post_recovery_sequence_engagement_wait_minutes,
        )

        wait_m = max(0, int(post_recovery_sequence_engagement_wait_minutes()))
    except (TypeError, ValueError):
        wait_m = 2880
    return now >= last_sent_at + timedelta(minutes=wait_m)


def _recovery_messages_exhausted_for_archive(
    *,
    sent_count: int,
    attempt_cap: int,
    log_ss: frozenset[str],
) -> bool:
    """True only for explicit automation closure — not when all templates were sent."""
    del sent_count, attempt_cap
    if "skipped_reason_template_disabled" in log_ss:
        return True
    # Full sequence + scheduler skip: stay active/sent until purchase / manual / opt-out.
    if "skipped_attempt_limit" in log_ss:
        return False
    return False


def _log_archive_decision(
    *,
    recovery_key: str,
    provider_sent: bool,
    messages_exhausted: bool,
    manual_archive: bool,
    auto_archive: bool,
    archive_reason: str,
    final_state: str,
) -> None:
    log.info(
        "[ARCHIVE DECISION] recovery_key=%s provider_sent=%s messages_exhausted=%s "
        "manual_archive=%s auto_archive=%s archive_reason=%s final_state=%s",
        (recovery_key or "-")[:512],
        provider_sent,
        messages_exhausted,
        manual_archive,
        auto_archive,
        archive_reason or "-",
        final_state or "-",
    )


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


def last_provider_sent_at_iso_from_recovery_logs(
    *,
    matched_logs: Optional[Sequence[Any]] = None,
    latest_log: Optional[Any] = None,
    recovery_key: str = "",
) -> Optional[str]:
    """ISO timestamp of the latest provider send for dashboard lifecycle windows."""
    logs: list[Any] = list(matched_logs or ())
    if latest_log is not None:
        logs.append(latest_log)
    dt = _last_provider_sent_at_utc(
        recovery_key=recovery_key,
        matched_logs=logs,
    )
    return dt.isoformat() if dt is not None else None


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
    timeline_statuses: Optional[frozenset[str]] = None,
    last_provider_sent_at: Optional[str] = None,
    matched_logs: Optional[Sequence[Any]] = None,
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
    tl = _timeline_flags(rk, timeline_statuses=timeline_statuses)
    now = _utc_now()
    sent_proven_early = _provider_sent(
        rk, log_ss, sent_n, timeline_statuses=timeline_statuses
    )
    exhausted_early = _recovery_messages_exhausted_for_archive(
        sent_count=sent_n, attempt_cap=cap, log_ss=log_ss
    )

    def _finish(
        lc: CustomerLifecycleStateV1,
        *,
        archive_reason: str,
        auto_archive: bool = False,
    ) -> CustomerLifecycleStateV1:
        _log_archive_decision(
            recovery_key=rk,
            provider_sent=sent_proven_early,
            messages_exhausted=exhausted_early,
            manual_archive=merchant_archived,
            auto_archive=auto_archive,
            archive_reason=archive_reason,
            final_state=lc.state_key,
        )
        return lc

    if merchant_archived:
        return _finish(
            _pack(
                STATE_ARCHIVED,
                what_happened="أُغلقت السلة من لوحة التاجر.",
                system_did="أوقفنا المتابعة الآلية لهذه السلة.",
                what_next="يمكنك إعادة فتحها للمراجعة فقط.",
                merchant_needed="لا",
                dashboard_action="reopen",
            ),
            archive_reason="manual_archive",
        )

    if terminal_history_archived and not sent_proven_early:
        return _finish(
            _pack(
                STATE_ARCHIVED,
                what_happened="أُغلقت السلة من السجل التاريخي.",
                system_did="أوقفنا المتابعة الآلية لهذه السلة.",
                what_next="يمكنك إعادة فتحها للمراجعة فقط.",
                merchant_needed="لا",
                dashboard_action="reopen",
            ),
            archive_reason="terminal_history",
        )

    purchased = bool(
        purchase_truth
        or cst == "recovered"
        or cnorm == "converted"
        or "stopped_converted" in log_ss
    )
    if purchased:
        variant = "purchased" if purchase_truth or cnorm == "converted" else "recovered"
        return _finish(
            _pack(
                STATE_COMPLETED,
                what_happened="اكتملت عملية الشراء أو استُعيدت السلة.",
                system_did="أنهينا مهمة الاسترجاع لهذه السلة.",
                what_next="لا مزيد من رسائل الاسترجاع الآلية.",
                merchant_needed="لا",
                dashboard_action="none",
                completed_variant=variant,
            ),
            archive_reason="purchased",
        )

    if _needs_intervention(
        log_ss=log_ss, phase_key=pk, is_vip_lane=is_vip_lane
    ):
        return _finish(
            _pack(
            STATE_NEEDS_INTERVENTION,
            what_happened="تحتاج السلة تدخلاً خاصاً (VIP أو قناة أو معالجة يدوية).",
            system_did="أوقفنا الإرسال الآلي أو تعذّر إكماله.",
            what_next="راجع السلة واتخذ إجراءً يدوياً عند الحاجة.",
            merchant_needed="نعم",
            dashboard_action="archive",
        ),
            archive_reason="needs_intervention",
        )

    replied = _customer_replied(
        rk, behavioral=bh, timeline_statuses=timeline_statuses
    )
    sent_proven = sent_proven_early

    if replied and sent_proven and tl["continuation_started"]:
        return _finish(
            _pack(
            STATE_CUSTOMER_ENGAGED,
            what_happened="ردّ العميل بعد رسالة الاسترجاع.",
            system_did="أرسل النظام متابعة الاعتراض تلقائياً.",
            what_next="لا حاجة لرسائل إرسال إضافية — المتابعة آلية.",
            merchant_needed="لا",
            dashboard_action="archive",
        ),
            archive_reason="customer_engaged",
        )

    if replied and sent_proven:
        return _finish(
            _pack(
            STATE_CUSTOMER_REPLY,
            what_happened="ردّ العميل على رسالة الاسترجاع.",
            system_did="سجّلنا الرد — المتابعة التلقائية تبدأ عند الحاجة.",
            what_next="نراقب هل يكمّل الطلب أو يرد مرة أخرى.",
            merchant_needed="لا",
            dashboard_action="archive",
        ),
            archive_reason="customer_reply",
        )

    due_at: Optional[datetime] = None
    if next_attempt_due_at:
        try:
            due_at = datetime.fromisoformat(
                str(next_attempt_due_at).replace("Z", "+00:00")
            )
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            due_at = None
    if due_at is None:
        due_at = _next_schedule_due_at(rk)

    if _return_to_site_detected(
        recovery_key=rk,
        phase_key=pk,
        coarse=cnorm,
        log_ss=log_ss,
        behavioral=bh,
    ):
        has_next_template = sent_n < cap
        delay_pending = due_at is not None and due_at > now
        next_line = ""
        if sent_proven and has_next_template and delay_pending:
            next_line = (
                f"إن لم يُكمل الشراء، متابعة محتملة بعد: "
                f"{_format_eta_ar((due_at - now).total_seconds())}"
            )
        if sent_proven:
            return _finish(
                _pack(
                    STATE_WAITING_PURCHASE_WINDOW,
                    what_happened="عاد العميل للموقع بعد رسالة الاسترجاع.",
                    system_did="أوقفنا المتابعة مؤقتًا — لا ضغط فوري على العميل.",
                    what_next=(
                        "نراقب إن أكمل الشراء؛ وإن لم يشترِ قد تُرسل متابعة لاحقة وفق الإعداد."
                    ),
                    merchant_needed="لا",
                    dashboard_action="none",
                    next_followup_line=next_line,
                ),
                archive_reason="waiting_purchase_window",
            )
        return _finish(
            _pack(
                STATE_RETURN_TO_SITE,
                what_happened="عاد العميل للموقع.",
                system_did="أوقفنا المتابعة مؤقتًا حتى لا يزعج العميل.",
                what_next="ننتظر هل يكمل الطلب أو يغادر.",
                merchant_needed="لا",
                dashboard_action="none",
            ),
            archive_reason="return_to_site",
        )

    exhausted = exhausted_early

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
        return _finish(
            _pack(
            STATE_WAITING_NEXT_SCHEDULED,
            what_happened="العميل لم يرد على الرسالة السابقة بعد.",
            system_did="أرسل النظام الرسالة الأولى (أو السابقة) وفق القالب.",
            what_next=f"رسالة تذكير مجدولة — {eta}",
            merchant_needed="لا",
            dashboard_action="archive",
            next_followup_line=f"المتابعة القادمة بعد: {eta}",
        ),
            archive_reason="waiting_next_scheduled",
        )

    sequence_complete = _recovery_sequence_complete(
        sent_count=sent_n, attempt_cap=cap, log_ss=log_ss
    )
    if (
        sent_proven
        and not replied
        and not exhausted
        and sequence_complete
        and not has_next_template
        and not delay_pending
    ):
        last_sent = _last_provider_sent_at_utc(
            recovery_key=rk,
            last_provider_sent_at=last_provider_sent_at,
            matched_logs=matched_logs,
        )
        if _post_sequence_engagement_window_expired(
            last_sent_at=last_sent, now=now
        ):
            return _finish(
                _pack(
                    STATE_RECOVERY_FOLLOWUP_COMPLETE,
                    what_happened="تم إرسال جميع رسائل المتابعة ولم يحدث تفاعل.",
                    system_did="أكمل CartFlow جميع خطوات الاسترجاع الآلية.",
                    what_next="لا توجد إجراءات مجدولة.",
                    merchant_needed="لا",
                    dashboard_action="none",
                    label_override=LABEL_AR[STATE_RECOVERY_FOLLOWUP_COMPLETE],
                ),
                archive_reason="recovery_sequence_engagement_window_expired",
            )

    if sent_proven and not replied and not exhausted:
        return _finish(
            _pack(
            STATE_WAITING_CUSTOMER_REPLY,
            what_happened="أُرسلت رسالة استرجاع للعميل.",
            system_did="أرسل النظام رسالة واتساب وفق سبب التردد.",
            what_next="ننتظر تفاعل العميل.",
            merchant_needed="لا",
            dashboard_action="archive",
        ),
            archive_reason="provider_sent_waiting_reply",
        )

    if exhausted and not replied:
        return _finish(
            _pack(
            STATE_ARCHIVED,
            what_happened="استُنفدت قوالب المتابعة دون رد من العميل.",
            system_did="أوقفنا الرسائل الآلية لهذه السلة.",
            what_next="يمكنك إعادة فتحها أو تركها في السجل.",
            merchant_needed="لا",
            dashboard_action="reopen",
        ),
            archive_reason="messages_exhausted",
            auto_archive=True,
        )

    if (
        tl["scheduled"]
        or tl["delay_started"]
        or pk in ("pending_send", "pending_second_attempt")
        or cnorm == "pending"
    ) and not sent_proven:
        if not has_phone:
            return _finish(
                _pack(
                STATE_NEEDS_INTERVENTION,
                what_happened="لا يوجد رقم موثوق لإكمال الإرسال.",
                system_did="لم يُرسل شيء بعد — بانتظار بيانات العميل.",
                what_next="أضف رقم العميل ليكمل النظام المسار.",
                merchant_needed="نعم",
                dashboard_action="archive",
            ),
                archive_reason="missing_phone",
            )
        next_line_fs = ""
        eta_sec = _scheduled_effective_delay_seconds(rk)
        if eta_sec is None and due_at is not None and due_at > now:
            eta_sec = (due_at - now).total_seconds()
        if eta_sec is not None and eta_sec > 0:
            next_line_fs = (
                f"الإرسال الأول بعد: "
                f"{_format_eta_ar(eta_sec)}"
            )
        return _finish(
            _pack(
            STATE_WAITING_FIRST_SEND,
            what_happened="السلة في انتظار أول رسالة استرجاع.",
            system_did="جدولنا المتابعة وفق التأخير المضبوط.",
            what_next="ستُرسل الرسالة تلقائياً عند حلول الموعد.",
            merchant_needed="لا",
            dashboard_action="archive",
            next_followup_line=next_line_fs,
        ),
            archive_reason="waiting_first_send",
        )

    return _finish(
        _pack(
        STATE_ACTIVE,
        what_happened="السلة قيد المتابعة في النظام.",
        system_did="يراقب النظام النشاط والسبب والتوقيت.",
        what_next="سيتابع النظام تلقائياً دون تدخل.",
        merchant_needed="لا",
        dashboard_action="archive",
    ),
        archive_reason="active_default",
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
    timeline_statuses: Optional[frozenset[str]] = None,
    last_provider_sent_at: Optional[str] = None,
    matched_logs: Optional[Sequence[Any]] = None,
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
        timeline_statuses=timeline_statuses,
        last_provider_sent_at=last_provider_sent_at,
        matched_logs=matched_logs,
    )
    target.update(lc.to_payload_fields())
    target["merchant_status_label_ar"] = lc.label_ar
    target["merchant_status_row_class"] = lc.status_row_class
    tab_bucket = lifecycle_state_to_filter_bucket(lc.state_key)
    primary_bucket = lifecycle_state_to_primary_bucket(lc.state_key)
    target["merchant_cart_primary_bucket"] = primary_bucket
    target["merchant_cart_bucket"] = tab_bucket
    target["merchant_cart_visible_tabs"] = list(lifecycle_state_visible_tabs(lc.state_key))
    if lc.state_key == STATE_COMPLETED:
        target["merchant_cart_is_terminal"] = True
        target["merchant_cart_is_active"] = False
    elif lc.state_key == STATE_ARCHIVED:
        target["merchant_cart_is_terminal"] = True
        target["merchant_cart_is_active"] = False
        target["merchant_is_history_slice"] = True
    else:
        target["merchant_cart_is_terminal"] = False
        target["merchant_cart_is_active"] = True
    return lc


def lifecycle_payload_for_reopen(recovery_key: str) -> dict[str, Any]:
    """Rebuild dashboard lifecycle fields after reopen (display-only archive cleared)."""
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return {}
    log_ss: set[str] = set()
    sent_n = 0
    try:
        from models import CartRecoveryLog  # noqa: PLC0415

        rows = (
            db.session.query(CartRecoveryLog.status)
            .filter(CartRecoveryLog.recovery_key == rk)
            .limit(200)
            .all()
        )
        for row in rows:
            st = _norm(row[0] if row else "")
            if st:
                log_ss.add(st)
            if st in SENT_LOG:
                sent_n += 1
    except SQLAlchemyError:
        db.session.rollback()
    lc = classify_customer_lifecycle_state_v1(
        recovery_key=rk,
        sent_count=sent_n,
        attempt_cap=max(2, sent_n or 1),
        log_statuses=frozenset(log_ss),
        coarse="sent" if sent_n else "pending",
        merchant_archived=False,
        terminal_history_archived=False,
    )
    fields = lc.to_payload_fields()
    fields["merchant_status_label_ar"] = lc.label_ar
    fields["merchant_status_row_class"] = lc.status_row_class
    return fields


__all__ = [
    "LABEL_AR",
    "STATE_ACTIVE",
    "STATE_ARCHIVED",
    "STATE_COMPLETED",
    "STATE_CUSTOMER_ENGAGED",
    "STATE_CUSTOMER_REPLY",
    "STATE_RETURN_TO_SITE",
    "STATE_NEEDS_INTERVENTION",
    "STATE_WAITING_CUSTOMER_REPLY",
    "STATE_WAITING_FIRST_SEND",
    "STATE_WAITING_NEXT_SCHEDULED",
    "STATE_WAITING_PURCHASE_WINDOW",
    "STATE_RECOVERY_FOLLOWUP_COMPLETE",
    "CustomerLifecycleStateV1",
    "attach_customer_lifecycle_state_v1",
    "classify_customer_lifecycle_state_v1",
    "last_provider_sent_at_iso_from_recovery_logs",
    "lifecycle_payload_for_reopen",
    "lifecycle_filter_counts_from_rows",
    "lifecycle_nav_badge_waiting_count",
    "lifecycle_state_to_filter_bucket",
    "lifecycle_state_to_primary_bucket",
    "lifecycle_state_visible_tabs",
    "lifecycle_truth_consistency_for_row",
]
