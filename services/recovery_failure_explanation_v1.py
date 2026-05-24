# -*- coding: utf-8 -*-
"""
Failed recovery explanation v1 — read-only operator clarity.

Maps ``RecoverySchedule`` / ``CartRecoveryLog`` failure statuses to calm
explanations and action hints. No recovery behavior changes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartRecoveryLog, RecoverySchedule
from services.recovery_restart_survival import (
    STATUS_FAILED_RESUME,
    STATUS_FAILED_RESUME_STALE,
    STATUS_NEEDS_REVIEW,
    STATUS_WHATSAPP_FAILED,
    _utc_now,
)

# --- Schedule terminal failures (recovery_schedules.status) ---
SCHEDULE_FAILURE_STATUSES = frozenset(
    {
        STATUS_WHATSAPP_FAILED,
        STATUS_FAILED_RESUME,
        STATUS_FAILED_RESUME_STALE,
        STATUS_NEEDS_REVIEW,
    }
)

# --- Log failures (cart_recovery_logs.status) — may exist without schedule row ---
LOG_FAILURE_STATUSES = frozenset(
    {
        "whatsapp_failed",
        "failed_retry",
        "failed_final",
    }
)

_FAILURE_CATALOG: dict[str, dict[str, str]] = {
    STATUS_WHATSAPP_FAILED: {
        "owner": "RecoverySchedule / CartRecoveryLog",
        "meaning": "WhatsApp provider did not accept or complete the send.",
        "explanation": "The message provider rejected the send or was unavailable.",
        "reason_code": "provider_restriction_or_unavailable",
        "risk": "medium",
        "action_needed": "yes",
        "action_summary": "Review WhatsApp/Twilio credentials, template approval, and customer number.",
    },
    STATUS_FAILED_RESUME: {
        "owner": "RecoverySchedule",
        "meaning": "Durable resume or execution ended without a safe terminal send.",
        "explanation": "Recovery could not safely resume or finish after restart or dispatch.",
        "reason_code": "resume_or_execution_incomplete",
        "risk": "medium",
        "action_needed": "review",
        "action_summary": "Inspect schedule context_json, last_error, and CartRecoveryLog for the session.",
    },
    STATUS_FAILED_RESUME_STALE: {
        "owner": "RecoverySchedule",
        "meaning": "Schedule stayed running too long with no send evidence.",
        "explanation": "A delayed recovery was left in running state past the stale threshold.",
        "reason_code": "stale_running_no_send_evidence",
        "risk": "low",
        "action_needed": "usually_no",
        "action_summary": "Often auto-repaired on startup; confirm customer was not messaged twice.",
    },
    STATUS_NEEDS_REVIEW: {
        "owner": "RecoverySchedule",
        "meaning": "Automated path flagged manual review.",
        "explanation": "Recovery stopped in a state that needs a human check.",
        "reason_code": "needs_manual_review",
        "risk": "medium",
        "action_needed": "yes",
        "action_summary": "Review dashboard row and logs before re-arming recovery.",
    },
    "failed_retry": {
        "owner": "CartRecoveryLog (WhatsApp queue worker)",
        "meaning": "Send failed but retries may still run.",
        "explanation": "A queued WhatsApp send failed; the worker will retry before giving up.",
        "reason_code": "provider_retry_in_progress",
        "risk": "low",
        "action_needed": "monitor",
        "action_summary": "Wait for retries; if it becomes failed_final, check provider settings.",
    },
    "failed_final": {
        "owner": "CartRecoveryLog (WhatsApp queue worker)",
        "meaning": "All send retries exhausted.",
        "explanation": "WhatsApp delivery failed after the maximum retry attempts.",
        "reason_code": "provider_retries_exhausted",
        "risk": "medium",
        "action_needed": "yes",
        "action_summary": "Check provider errors, template, and phone number validity.",
    },
}


def explain_failure_status(
    status: str,
    *,
    last_error: str = "",
    log_message: str = "",
) -> dict[str, str]:
    """Return explanation fields for a status (with optional detail hints)."""
    st = (status or "").strip().lower()
    cat = _FAILURE_CATALOG.get(st)
    base = dict(cat) if cat else {}
    if not base:
        base = {
            "owner": "unknown",
            "meaning": "Unclassified failure status.",
            "explanation": "Recovery ended in a failure state we do not have a detailed label for.",
            "reason_code": "unknown_failure",
            "risk": "medium",
            "action_needed": "review",
            "action_summary": "Inspect CartRecoveryLog and RecoverySchedule for this session.",
        }
    out = dict(base)
    detail = (last_error or log_message or "").strip()[:220]
    if detail:
        if "purchase_truth" in detail.lower():
            out["reason_code"] = "cancelled_for_purchase"
            out["explanation"] = "Recovery was stopped because purchase was detected."
            out["action_needed"] = "no"
            out["action_summary"] = "No resend needed unless purchase evidence was wrong."
        elif "timeout" in detail.lower():
            out["reason_code"] = "provider_timeout"
            out["explanation"] = "The provider or network timed out before confirming delivery."
        out["detail"] = detail
    return out


def _iso_dt(dt: Any) -> Optional[str]:
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


def _schedule_failure_row(row: RecoverySchedule) -> dict[str, Any]:
    st = (row.status or "").strip()
    err = (row.last_error or "").strip()
    meta = explain_failure_status(st, last_error=err)
    return {
        "source": "recovery_schedule",
        "schedule_id": int(row.id),
        "recovery_key": (row.recovery_key or "")[:120],
        "store_slug": (row.store_slug or "")[:64],
        "session_id": (row.session_id or "")[:80],
        "status": st,
        "reason": meta.get("reason_code", ""),
        "explanation": meta.get("explanation", ""),
        "action_needed": meta.get("action_needed", "review"),
        "action_summary": meta.get("action_summary", ""),
        "risk": meta.get("risk", ""),
        "time": _iso_dt(row.updated_at or row.scheduled_at),
        "last_error": err[:220] if err else None,
        "step": int(row.step),
    }


def _log_failure_row(lg: CartRecoveryLog) -> dict[str, Any]:
    st = (lg.status or "").strip()
    msg = (lg.message or "").strip()
    meta = explain_failure_status(st, log_message=msg)
    rk = ""
    ss = (lg.store_slug or "").strip()
    sid = (lg.session_id or "").strip()
    if ss and sid:
        rk = f"{ss}:{sid}"[:120]
    return {
        "source": "cart_recovery_log",
        "log_id": int(lg.id),
        "recovery_key": rk,
        "store_slug": ss[:64],
        "session_id": sid[:80],
        "status": st,
        "reason": meta.get("reason_code", ""),
        "explanation": meta.get("explanation", ""),
        "action_needed": meta.get("action_needed", "review"),
        "action_summary": meta.get("action_summary", ""),
        "risk": meta.get("risk", ""),
        "time": _iso_dt(lg.created_at),
        "message_preview": msg[:180] if msg else None,
        "step": int(lg.step) if lg.step is not None else None,
    }


def build_recent_failures_snapshot(*, limit: int = 10) -> dict[str, Any]:
    """
    Recent failure rows from DB (schedules + logs), merged by time descending.
    """
    lim = max(1, min(int(limit), 25))
    out: dict[str, Any] = {
        "count": 0,
        "schedule_failure_count": 0,
        "log_failure_count": 0,
        "by_status": {},
        "latest": None,
        "recent": [],
        "failure_types_documented": sorted(
            set(SCHEDULE_FAILURE_STATUSES) | set(LOG_FAILURE_STATUSES)
        ),
    }
    items: list[tuple[datetime, dict[str, Any]]] = []
    try:
        db.create_all()
        sched_rows = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.status.in_(tuple(SCHEDULE_FAILURE_STATUSES)))
            .order_by(RecoverySchedule.updated_at.desc())
            .limit(lim)
            .all()
        )
        out["schedule_failure_count"] = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.status.in_(tuple(SCHEDULE_FAILURE_STATUSES)))
            .count()
        )
        for row in sched_rows:
            item = _schedule_failure_row(row)
            ts = _parse_iso(item.get("time")) or _utc_now()
            items.append((ts, item))
            st = item["status"]
            out["by_status"][st] = int(out["by_status"].get(st, 0)) + 1

        log_rows = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.status.in_(tuple(LOG_FAILURE_STATUSES)))
            .order_by(CartRecoveryLog.created_at.desc())
            .limit(lim)
            .all()
        )
        out["log_failure_count"] = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.status.in_(tuple(LOG_FAILURE_STATUSES)))
            .count()
        )
        for lg in log_rows:
            item = _log_failure_row(lg)
            ts = _parse_iso(item.get("time")) or _utc_now()
            items.append((ts, item))
            st = item["status"]
            out["by_status"][st] = int(out["by_status"].get(st, 0)) + 1
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["error"] = str(exc)[:200]
        return out

    items.sort(key=lambda x: x[0], reverse=True)
    recent = [it[1] for it in items[:lim]]
    out["recent"] = recent
    out["count"] = len(recent)
    out["latest"] = recent[0] if recent else None
    return out


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        raw = str(s).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def build_failure_inventory_for_docs() -> list[dict[str, str]]:
    """Static catalog for documentation (Part 1 inventory)."""
    rows: list[dict[str, str]] = []
    for key in sorted(_FAILURE_CATALOG.keys()):
        row = _FAILURE_CATALOG[key]
        rows.append(
            {
                "status": key,
                "owner": row["owner"],
                "meaning": row["meaning"],
                "risk": row["risk"],
                "action_needed": row["action_needed"],
            }
        )
    return rows


__all__ = [
    "LOG_FAILURE_STATUSES",
    "SCHEDULE_FAILURE_STATUSES",
    "build_failure_inventory_for_docs",
    "build_recent_failures_snapshot",
    "explain_failure_status",
]
