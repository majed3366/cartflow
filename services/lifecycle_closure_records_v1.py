# -*- coding: utf-8 -*-
"""
Durable lifecycle closure records v1 — terminal outcomes beyond purchase.

Persist-only: does not change recovery, WhatsApp, delays, or decision engine.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import LifecycleClosureRecord
from schema_lifecycle_closure import ensure_lifecycle_closure_schema

log = logging.getLogger("cartflow")

# Canonical closure_status values
CLOSURE_PURCHASE_COMPLETED = "purchase_completed"
CLOSURE_RETURNED_TO_SITE = "returned_to_site"
CLOSURE_CUSTOMER_REPLIED = "customer_replied"
CLOSURE_FAILED = "failed"
CLOSURE_CANCELLED = "cancelled"
CLOSURE_MAX_ATTEMPTS = "max_attempts"
CLOSURE_USER_REJECTED_HELP = "user_rejected_help"
CLOSURE_VIP_MANUAL = "vip_manual_handling"

# Legacy alias (purchase truth v2)
CLOSURE_REPLIED = CLOSURE_CUSTOMER_REPLIED

CANONICAL_CLOSURE_STATUSES = frozenset(
    {
        CLOSURE_PURCHASE_COMPLETED,
        CLOSURE_RETURNED_TO_SITE,
        CLOSURE_CUSTOMER_REPLIED,
        CLOSURE_FAILED,
        CLOSURE_CANCELLED,
        CLOSURE_MAX_ATTEMPTS,
        CLOSURE_USER_REJECTED_HELP,
        CLOSURE_VIP_MANUAL,
        "replied",  # legacy rows
    }
)

# Higher rank wins on conflict
_CLOSURE_RANK: dict[str, int] = {
    CLOSURE_USER_REJECTED_HELP: 1,
    CLOSURE_MAX_ATTEMPTS: 2,
    CLOSURE_CANCELLED: 3,
    CLOSURE_FAILED: 4,
    CLOSURE_VIP_MANUAL: 5,
    CLOSURE_RETURNED_TO_SITE: 6,
    CLOSURE_CUSTOMER_REPLIED: 7,
    "replied": 7,
    CLOSURE_PURCHASE_COMPLETED: 8,
}

_LOG_STATUS_TO_CLOSURE: dict[str, tuple[str, str]] = {
    "returned_to_site": (CLOSURE_RETURNED_TO_SITE, "user_returned_to_site"),
    "skipped_anti_spam": (CLOSURE_RETURNED_TO_SITE, "anti_spam_return"),
    "skipped_followup_customer_replied": (
        CLOSURE_CUSTOMER_REPLIED,
        "customer_replied_followup",
    ),
    "skipped_user_rejected_help": (CLOSURE_USER_REJECTED_HELP, "user_rejected_help"),
    "skipped_attempt_limit": (CLOSURE_MAX_ATTEMPTS, "attempt_limit_reached"),
    "whatsapp_failed": (CLOSURE_FAILED, "whatsapp_send_failed"),
    "failed_final": (CLOSURE_FAILED, "whatsapp_failed_final"),
    "vip_manual_handling": (CLOSURE_VIP_MANUAL, "vip_manual_handling"),
    "stopped_converted": (CLOSURE_PURCHASE_COMPLETED, "log_stopped_converted"),
}

_TERMINAL_SCHEDULE_CANCEL_MARKERS = frozenset(
    {
        "purchase_truth_stop",
        "purchase_detected",
        "user_returned",
        "attempt_limit",
        "customer_replied",
        "terminal_cancel",
    }
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _norm_status(st: str) -> str:
    return (st or "").strip().lower()


def _canonical_status(st: str) -> str:
    s = _norm_status(st)
    if s == "replied":
        return CLOSURE_CUSTOMER_REPLIED
    return s


def _emit(tag: str, **fields: Any) -> None:
    parts = [f"[{tag}]"]
    for k, v in fields.items():
        if v is None:
            continue
        parts.append(f"{k}={str(v)[:220]}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def reset_lifecycle_closure_records_for_tests() -> None:
    try:
        ensure_lifecycle_closure_schema(db)
        db.session.query(LifecycleClosureRecord).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


def get_durable_closure(recovery_key: str) -> Optional[dict[str, Any]]:
    rk = (recovery_key or "").strip()
    if not rk:
        return None
    try:
        ensure_lifecycle_closure_schema(db)
        row = (
            db.session.query(LifecycleClosureRecord)
            .filter(LifecycleClosureRecord.recovery_key == rk)
            .first()
        )
        if row is None:
            return None
        ct = row.closure_time
        if ct is not None and getattr(ct, "tzinfo", None) is None:
            ct = ct.replace(tzinfo=timezone.utc)
        st = _canonical_status(row.closure_status or "")
        return {
            "recovery_key": rk,
            "closure_status": st,
            "closure_reason": (row.closure_reason or "").strip(),
            "closure_source": (row.closure_source or "").strip(),
            "closure_time": ct.astimezone(timezone.utc).isoformat() if ct else None,
            "store_slug": (getattr(row, "store_slug", None) or "").strip() or None,
            "session_id": (getattr(row, "session_id", None) or "").strip() or None,
            "cart_id": (getattr(row, "cart_id", None) or "").strip() or None,
        }
    except Exception:  # noqa: BLE001
        return None


def record_lifecycle_closure(
    recovery_key: str,
    *,
    closure_status: str,
    closure_reason: str,
    closure_source: str,
    closure_time: Optional[datetime] = None,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> bool:
    """
    Idempotent durable closure. Same status → no duplicate write.
    Stronger closure_status wins on conflict.
    """
    rk = (recovery_key or "").strip()
    st = _canonical_status(closure_status)
    if not rk or st not in CANONICAL_CLOSURE_STATUSES:
        return False

    reason = (closure_reason or st)[:128]
    source = (closure_source or "unknown")[:128]
    when = closure_time or _utc_now()
    new_rank = _CLOSURE_RANK.get(st, 0)
    ss = (store_slug or "").strip()[:255] or None
    sid = (session_id or "").strip()[:512] or None
    cid = (cart_id or "").strip()[:255] or None

    ensure_lifecycle_closure_schema(db)
    try:
        row = (
            db.session.query(LifecycleClosureRecord)
            .filter(LifecycleClosureRecord.recovery_key == rk)
            .first()
        )
        if row is None:
            row = LifecycleClosureRecord(
                recovery_key=rk,
                closure_status=st[:64],
                closure_reason=reason,
                closure_source=source,
                closure_time=when,
                store_slug=ss or "",
                session_id=sid or "",
                cart_id=cid,
            )
            db.session.add(row)
            db.session.commit()
            _emit(
                "LIFECYCLE CLOSURE RECORDED",
                recovery_key=rk,
                closure_status=st,
                closure_reason=reason,
                closure_source=source,
            )
            return True

        cur = _canonical_status(row.closure_status or "")
        if cur == st:
            return False
        cur_rank = _CLOSURE_RANK.get(cur, 0)
        if new_rank < cur_rank:
            return False
        row.closure_status = st[:64]
        row.closure_reason = reason
        row.closure_source = source
        row.closure_time = when
        if ss:
            row.store_slug = ss
        if sid:
            row.session_id = sid
        if cid:
            row.cart_id = cid
        db.session.commit()
        _emit(
            "LIFECYCLE CLOSURE UPDATED",
            recovery_key=rk,
            closure_status=st,
            closure_reason=reason,
            closure_source=source,
            previous=cur or "-",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        log.warning("record_lifecycle_closure failed: %s", exc)
        return False


# Back-compat alias (purchase truth v2)
record_durable_lifecycle_closure = record_lifecycle_closure


def maybe_record_closure_from_recovery_log(
    *,
    recovery_key: str,
    log_status: str,
    store_slug: str = "",
    session_id: str = "",
    cart_id: Optional[str] = None,
    source: str = "cart_recovery_log",
) -> bool:
    """Map CartRecoveryLog.status → durable closure when terminal."""
    rk = (recovery_key or "").strip()
    if not rk:
        try:
            from main import _recovery_key_from_payload

            rk = _recovery_key_from_payload(
                {
                    "store": store_slug,
                    "store_slug": store_slug,
                    "session_id": session_id,
                    "cart_id": cart_id,
                }
            )
        except Exception:  # noqa: BLE001
            rk = ""
    if not rk:
        return False

    mapped = _LOG_STATUS_TO_CLOSURE.get(_norm_status(log_status))
    if not mapped:
        return False
    closure_status, default_reason = mapped
    return record_lifecycle_closure(
        rk,
        closure_status=closure_status,
        closure_reason=default_reason,
        closure_source=f"{source}:{_norm_status(log_status)}"[:128],
        store_slug=store_slug,
        session_id=session_id,
        cart_id=str(cart_id or ""),
    )


def maybe_record_closure_from_schedule_cancel(
    *,
    recovery_key: str,
    last_error: str = "",
    store_slug: str = "",
    session_id: str = "",
    cart_id: Optional[str] = None,
) -> bool:
    """Terminal RecoverySchedule.cancelled — skip when purchase already owns closure."""
    rk = (recovery_key or "").strip()
    if not rk:
        return False
    err = (last_error or "").strip().lower()
    if "purchase_truth" in err or "purchase_detected" in err:
        return False
    try:
        from services.cartflow_purchase_truth import has_purchase

        if has_purchase(rk):
            return False
    except Exception:  # noqa: BLE001
        pass
    reason = "schedule_cancelled"
    if err:
        reason = err[:128]
    return record_lifecycle_closure(
        rk,
        closure_status=CLOSURE_CANCELLED,
        closure_reason=reason,
        closure_source="recovery_schedule:cancelled",
        store_slug=store_slug,
        session_id=session_id,
        cart_id=str(cart_id or ""),
    )


__all__ = [
    "CANONICAL_CLOSURE_STATUSES",
    "CLOSURE_CANCELLED",
    "CLOSURE_CUSTOMER_REPLIED",
    "CLOSURE_FAILED",
    "CLOSURE_MAX_ATTEMPTS",
    "CLOSURE_PURCHASE_COMPLETED",
    "CLOSURE_REPLIED",
    "CLOSURE_RETURNED_TO_SITE",
    "CLOSURE_USER_REJECTED_HELP",
    "CLOSURE_VIP_MANUAL",
    "get_durable_closure",
    "maybe_record_closure_from_recovery_log",
    "maybe_record_closure_from_schedule_cancel",
    "record_durable_lifecycle_closure",
    "record_lifecycle_closure",
    "reset_lifecycle_closure_records_for_tests",
]
