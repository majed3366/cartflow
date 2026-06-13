# -*- coding: utf-8 -*-
"""Merchant-facing follow-up progress lines — display derivatives only (LT-C1).

Lifecycle scheduling decisions live in ``customer_lifecycle_state``.
Use ``sync_merchant_followup_clarity_from_lifecycle`` in
``lifecycle_authority_recovery_v1`` for dashboard rows.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

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


def _parse_due_iso(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _next_due_from_schedules(
    schedule_rows: Optional[Sequence[Any]],
    *,
    now: datetime,
) -> Optional[datetime]:
    best: Optional[datetime] = None
    for sr in schedule_rows or ():
        st = (getattr(sr, "status", None) or "").strip().lower()
        if st not in ("scheduled", "running"):
            continue
        due = getattr(sr, "due_at", None)
        if due is None:
            continue
        if getattr(due, "tzinfo", None) is None:
            due = due.replace(tzinfo=timezone.utc)
        else:
            due = due.astimezone(timezone.utc)
        if due <= now:
            continue
        if best is None or due < best:
            best = due
    return best


def build_merchant_followup_clarity_fields(
    *,
    sent_count: int,
    configured_count: int,
    next_attempt_due_at: Optional[str] = None,
    schedule_rows: Optional[Sequence[Any]] = None,
    now: Optional[datetime] = None,
    purchased: bool = False,
) -> dict[str, Any]:
    """
    Calm merchant copy from sent/configured counts and RecoverySchedule timing.
    """
    nu = now or datetime.now(timezone.utc)
    sent_n = max(0, int(sent_count or 0))
    cap = max(0, int(configured_count or 0))
    out: dict[str, Any] = {
        "merchant_followup_sent_count": sent_n,
        "merchant_followup_configured_count": cap,
        "merchant_followup_progress_ar": None,
        "merchant_followup_sequence_line_ar": None,
        "merchant_followup_next_line_ar": None,
    }
    if purchased or cap < 1 or sent_n < 1:
        return out

    sent_show = min(sent_n, cap) if cap else sent_n
    out["merchant_followup_progress_ar"] = (
        f"تم إرسال {_ar_num(sent_show)} من {_ar_num(cap)}"
    )

    due_dt = _parse_due_iso(next_attempt_due_at)
    if due_dt is None:
        due_dt = _next_due_from_schedules(schedule_rows, now=nu)

    sequence_done = sent_n >= cap
    more_pending = sent_n < cap

    if sequence_done:
        out["merchant_followup_sequence_line_ar"] = (
            "اكتملت سلسلة المتابعة — بانتظار تفاعل العميل"
        )

    if more_pending and due_dt is not None and due_dt > nu:
        eta = _format_eta_ar((due_dt - nu).total_seconds())
        out["merchant_followup_next_line_ar"] = f"الرسالة التالية خلال {eta}"

    return out


def attach_merchant_followup_clarity(
    target: Mapping[str, Any],
    *,
    sent_count: int,
    configured_count: int,
    next_attempt_due_at: Optional[str] = None,
    schedule_rows: Optional[Sequence[Any]] = None,
    purchased: bool = False,
) -> dict[str, Any]:
    """Merge display fields into a dashboard cart row dict."""
    if not isinstance(target, dict):
        fields = build_merchant_followup_clarity_fields(
            sent_count=sent_count,
            configured_count=configured_count,
            next_attempt_due_at=next_attempt_due_at,
            schedule_rows=schedule_rows,
            purchased=purchased,
        )
        return fields
    fields = build_merchant_followup_clarity_fields(
        sent_count=sent_count,
        configured_count=configured_count,
        next_attempt_due_at=next_attempt_due_at,
        schedule_rows=schedule_rows,
        purchased=purchased,
    )
    target.update(fields)  # type: ignore[union-attr]
    return fields


__all__ = [
    "attach_merchant_followup_clarity",
    "build_merchant_followup_clarity_fields",
]
