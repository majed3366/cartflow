# -*- coding: utf-8 -*-
"""
Durable recovery truth timeline — proven transitions for dashboard + debug.

Statuses (ordered):
  scheduled → delay_started → before_send → provider_queued → provider_sent
  → webhook_delivered → customer_reply → continuation_started
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoveryTruthTimelineEvent

log = logging.getLogger("cartflow")

STATUS_SCHEDULED = "scheduled"
STATUS_DELAY_STARTED = "delay_started"
STATUS_BEFORE_SEND = "before_send"
STATUS_PROVIDER_QUEUED = "provider_queued"
STATUS_PROVIDER_SENT = "provider_sent"
STATUS_WEBHOOK_DELIVERED = "webhook_delivered"
STATUS_CUSTOMER_REPLY = "customer_reply"
STATUS_CONTINUATION_STARTED = "continuation_started"

CANONICAL_ORDER: tuple[str, ...] = (
    STATUS_SCHEDULED,
    STATUS_DELAY_STARTED,
    STATUS_BEFORE_SEND,
    STATUS_PROVIDER_QUEUED,
    STATUS_PROVIDER_SENT,
    STATUS_WEBHOOK_DELIVERED,
    STATUS_CUSTOMER_REPLY,
    STATUS_CONTINUATION_STARTED,
)

_ORDER_INDEX = {s: i for i, s in enumerate(CANONICAL_ORDER)}

# Record at most once per recovery_key (customer_reply may repeat).
_MONOTONIC_ONCE = frozenset(
    {
        STATUS_SCHEDULED,
        STATUS_DELAY_STARTED,
        STATUS_BEFORE_SEND,
        STATUS_PROVIDER_QUEUED,
        STATUS_PROVIDER_SENT,
        STATUS_WEBHOOK_DELIVERED,
        STATUS_CONTINUATION_STARTED,
    }
)

_PROVIDER_SEND_STATUSES = frozenset({STATUS_PROVIDER_QUEUED, STATUS_PROVIDER_SENT})
_PROVIDER_SENT_STATUSES = frozenset({STATUS_PROVIDER_SENT})
_LOG_SENT = frozenset({"sent_real", "mock_sent"})


def _norm(s: Any) -> str:
    return str(s or "").strip()


def parse_recovery_key(recovery_key: str) -> tuple[str, str]:
    rk = _norm(recovery_key)
    if not rk or ":" not in rk:
        return rk, ""
    store_slug, session_id = rk.split(":", 1)
    return _norm(store_slug), _norm(session_id)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dt_iso(dt: Any) -> str:
    if dt is None:
        return ""
    try:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except (TypeError, ValueError, AttributeError):
        return ""


def record_recovery_truth_event(
    *,
    recovery_key: str,
    status: str,
    source: str,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> bool:
    """
    Persist one timeline transition. Returns True when a new row was written.
    """
    rk = _norm(recovery_key)[:512]
    st = _norm(status)[:64]
    if not rk or not st:
        return False
    slug = _norm(store_slug)[:255]
    sid = _norm(session_id)[:512]
    cid = _norm(cart_id)[:255]
    if not slug:
        slug, sid_from_rk = parse_recovery_key(rk)
        if not sid and sid_from_rk:
            sid = sid_from_rk
    try:
        from schema_recovery_truth_timeline import (  # noqa: PLC0415
            ensure_recovery_truth_timeline_schema,
        )

        ensure_recovery_truth_timeline_schema(db)
        if st in _MONOTONIC_ONCE:
            exists = (
                db.session.query(RecoveryTruthTimelineEvent.id)
                .filter(
                    RecoveryTruthTimelineEvent.recovery_key == rk,
                    RecoveryTruthTimelineEvent.status == st,
                )
                .first()
            )
            if exists is not None:
                return False
        row = RecoveryTruthTimelineEvent(
            recovery_key=rk,
            store_slug=slug or "unknown",
            session_id=sid or None,
            cart_id=cid or None,
            status=st,
            source=_norm(source)[:128] or "unknown",
            created_at=_utc_now(),
        )
        db.session.add(row)
        db.session.commit()
        try:
            log.info(
                "[RECOVERY TRUTH TIMELINE] status=%s recovery_key=%s source=%s",
                st,
                rk[:120],
                _norm(source)[:64],
            )
        except Exception:  # noqa: BLE001
            pass
        return True
    except SQLAlchemyError as exc:
        db.session.rollback()
        log.warning("record_recovery_truth_event failed: %s", exc)
        return False


def get_recovery_truth_timeline(recovery_key: str) -> list[dict[str, Any]]:
    """Ordered timeline for one recovery_key."""
    rk = _norm(recovery_key)[:512]
    if not rk:
        return []
    try:
        from schema_recovery_truth_timeline import (  # noqa: PLC0415
            ensure_recovery_truth_timeline_schema,
        )

        ensure_recovery_truth_timeline_schema(db)
        rows = (
            db.session.query(RecoveryTruthTimelineEvent)
            .filter(RecoveryTruthTimelineEvent.recovery_key == rk)
            .order_by(
                RecoveryTruthTimelineEvent.created_at.asc(),
                RecoveryTruthTimelineEvent.id.asc(),
            )
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []

    out: list[dict[str, Any]] = []
    for row in rows:
        st = _norm(getattr(row, "status", None))
        out.append(
            {
                "status": st,
                "timestamp": _dt_iso(getattr(row, "created_at", None)),
                "source": _norm(getattr(row, "source", None)) or None,
                "store_slug": _norm(getattr(row, "store_slug", None)) or None,
                "session_id": _norm(getattr(row, "session_id", None)) or None,
                "cart_id": _norm(getattr(row, "cart_id", None)) or None,
                "recovery_key": rk,
            }
        )
    out.sort(
        key=lambda e: (
            _ORDER_INDEX.get(str(e.get("status") or ""), 999),
            str(e.get("timestamp") or ""),
        )
    )
    return out


def timeline_status_set(recovery_key: str) -> frozenset[str]:
    return frozenset(
        _norm(e.get("status"))
        for e in get_recovery_truth_timeline(recovery_key)
        if _norm(e.get("status"))
    )


def provider_send_proven(
    recovery_key: str,
    *,
    log_statuses: Optional[Any] = None,
    sent_count: int = 0,
) -> bool:
    """
    Dashboard may show «تم الإرسال» only when provider_sent (or sent log) is proven.
    Queued alone is not sufficient.
    """
    ts = timeline_status_set(recovery_key)
    if ts & _PROVIDER_SENT_STATUSES:
        return True
    log_ss: set[str] = set()
    if log_statuses:
        for raw in log_statuses:
            t = _norm(raw).lower()
            if t:
                log_ss.add(t)
    if log_ss & _LOG_SENT:
        return True
    if int(sent_count or 0) >= 1 and log_ss & _LOG_SENT:
        return True
    return False


def customer_reply_proven(
    recovery_key: str,
    *,
    behavioral: Optional[dict[str, Any]] = None,
) -> bool:
    ts = timeline_status_set(recovery_key)
    if STATUS_CUSTOMER_REPLY in ts:
        return True
    bh = behavioral if isinstance(behavioral, dict) else {}
    if bh.get("customer_replied") is True and STATUS_CUSTOMER_REPLY in ts:
        return True
    return False


def continuation_started_proven(recovery_key: str) -> bool:
    return STATUS_CONTINUATION_STARTED in timeline_status_set(recovery_key)


def customer_reply_proven_for_dashboard(
    recovery_key: str,
    *,
    behavioral: Optional[dict[str, Any]] = None,
) -> bool:
    """«بدأ متابعة الاعتراض» requires durable customer_reply event."""
    return STATUS_CUSTOMER_REPLY in timeline_status_set(recovery_key)


def map_cart_recovery_log_status_to_timeline(status: str) -> Optional[str]:
    st = _norm(status).lower()
    if st == "queued":
        return STATUS_PROVIDER_QUEUED
    if st in _LOG_SENT:
        return STATUS_PROVIDER_SENT
    return None


__all__ = [
    "CANONICAL_ORDER",
    "STATUS_BEFORE_SEND",
    "STATUS_CONTINUATION_STARTED",
    "STATUS_CUSTOMER_REPLY",
    "STATUS_DELAY_STARTED",
    "STATUS_PROVIDER_QUEUED",
    "STATUS_PROVIDER_SENT",
    "STATUS_SCHEDULED",
    "STATUS_WEBHOOK_DELIVERED",
    "continuation_started_proven",
    "customer_reply_proven_for_dashboard",
    "get_recovery_truth_timeline",
    "map_cart_recovery_log_status_to_timeline",
    "provider_send_proven",
    "record_recovery_truth_event",
    "timeline_status_set",
]
