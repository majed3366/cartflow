# -*- coding: utf-8 -*-
"""
Knowledge Layer v1 — read-only metric aggregation.

Accepts db session + store_slug + date window; returns metrics only (no Arabic copy).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from models import (
    AbandonedCart,
    CartRecoveryLog,
    CartRecoveryReason,
    LifecycleClosureRecord,
    PurchaseTruthRecord,
    RecoverySchedule,
    RecoveryTruthTimelineEvent,
)
from services.reason_template_recovery import canonical_reason_template_key

# Recovery log statuses (read-side only — mirrors lifecycle layer vocabulary)
_MESSAGES_SENT_STATUSES = frozenset({"sent_real", "mock_sent"})
_FAILED_STATUSES = frozenset({"whatsapp_failed", "failed_final", "failed_retry"})
_RETURN_LOG_STATUSES = frozenset({"returned_to_site", "user_returned"})
_IGNORED_LOG_STATUSES = frozenset({"skipped_user_rejected_help"})
_STOPPED_LOG_STATUSES = frozenset({"skipped_attempt_limit", "skipped_anti_spam"})

_TIMELINE_REPLY = "customer_reply"
_TIMELINE_CHECKOUT_HINTS = frozenset(
    {"checkout_started", "checkout_push", "ready_for_checkout"}
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _window_bounds(*, window_days: int, now: Optional[datetime] = None) -> tuple[datetime, datetime, datetime]:
    end = _naive(now or _utc_now())
    start = end - timedelta(days=max(1, int(window_days)))
    prev_start = start - timedelta(days=max(1, int(window_days)))
    return start, end, prev_start


@dataclass
class KnowledgeMetricsBundle:
    store_slug: str
    window_days: int
    window_start: datetime
    window_end: datetime
    store_resolved: bool = False
    store_id: Optional[int] = None

    # Traffic / demand (CartFlow-visible only)
    visitor_data_available: bool = False
    cart_count: int = 0
    prev_cart_count: int = 0
    carts_with_phone: int = 0

    # Conversion funnel gaps
    checkout_data_available: bool = False
    checkout_signal_count: int = 0
    purchase_count: int = 0

    # Hesitation
    hesitation_total: int = 0
    hesitation_distribution: dict[str, int] = field(default_factory=dict)

    # Recovery activity
    recovery_messages_sent: int = 0
    recovery_replies: int = 0
    recovery_returns: int = 0
    recovery_purchases: int = 0
    recovery_ignored: int = 0
    recovery_stopped: int = 0
    recovery_failed: int = 0
    recovery_scheduled_active: int = 0

    # Truth layers
    purchase_truth_rows: int = 0
    lifecycle_closure_rows: int = 0

    source_tables: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_slug": self.store_slug,
            "window_days": self.window_days,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "store_resolved": self.store_resolved,
            "visitor_data_available": self.visitor_data_available,
            "cart_count": self.cart_count,
            "prev_cart_count": self.prev_cart_count,
            "carts_with_phone": self.carts_with_phone,
            "checkout_data_available": self.checkout_data_available,
            "checkout_signal_count": self.checkout_signal_count,
            "purchase_count": self.purchase_count,
            "hesitation_total": self.hesitation_total,
            "hesitation_distribution": dict(self.hesitation_distribution),
            "recovery_messages_sent": self.recovery_messages_sent,
            "recovery_replies": self.recovery_replies,
            "recovery_returns": self.recovery_returns,
            "recovery_purchases": self.recovery_purchases,
            "recovery_ignored": self.recovery_ignored,
            "recovery_stopped": self.recovery_stopped,
            "recovery_failed": self.recovery_failed,
            "recovery_scheduled_active": self.recovery_scheduled_active,
            "purchase_truth_rows": self.purchase_truth_rows,
            "lifecycle_closure_rows": self.lifecycle_closure_rows,
            "source_tables": list(self.source_tables),
        }


def _hesitation_bucket(reason_tag: str) -> str:
    canon = canonical_reason_template_key(reason_tag)
    if canon in ("price", "shipping", "quality", "delivery", "warranty"):
        return canon
    if canon == "thinking":
        return "other"
    if canon == "other":
        return "other"
    raw = (reason_tag or "").strip().lower()
    if raw in ("human_support", "vip_phone_capture"):
        return "other"
    return "other"


def collect_knowledge_metrics(
    db_session: Any,
    store_slug: str,
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
) -> KnowledgeMetricsBundle:
    """
    Aggregate read-only metrics for one store within ``window_days``.

    No writes; rolls back on SQLAlchemy errors.
    """
    ss = (store_slug or "").strip()[:255]
    start, end, prev_start = _window_bounds(window_days=window_days, now=now)
    bundle = KnowledgeMetricsBundle(
        store_slug=ss,
        window_days=window_days,
        window_start=start,
        window_end=end,
    )
    if not ss:
        return bundle

    tables: set[str] = set()

    try:
        from services.vip_abandoned_cart_phone import (  # noqa: PLC0415
            resolve_store_row_for_cartflow_slug_session,
        )

        store_row = resolve_store_row_for_cartflow_slug_session(db_session, ss)
        if store_row is not None:
            bundle.store_resolved = True
            bundle.store_id = int(getattr(store_row, "id", 0) or 0) or None
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db_session.rollback()
        store_row = None

    # --- Abandoned carts (demand proxy; not visitor traffic) ---
    if bundle.store_id:
        tables.add("abandoned_carts")
        try:
            bundle.cart_count = int(
                db_session.query(func.count(AbandonedCart.id))
                .filter(
                    AbandonedCart.store_id == bundle.store_id,
                    AbandonedCart.first_seen_at >= start,
                    AbandonedCart.first_seen_at < end,
                )
                .scalar()
                or 0
            )
            bundle.prev_cart_count = int(
                db_session.query(func.count(AbandonedCart.id))
                .filter(
                    AbandonedCart.store_id == bundle.store_id,
                    AbandonedCart.first_seen_at >= prev_start,
                    AbandonedCart.first_seen_at < start,
                )
                .scalar()
                or 0
            )
            bundle.carts_with_phone = int(
                db_session.query(func.count(AbandonedCart.id))
                .filter(
                    AbandonedCart.store_id == bundle.store_id,
                    AbandonedCart.first_seen_at >= start,
                    AbandonedCart.first_seen_at < end,
                    AbandonedCart.customer_phone.isnot(None),
                    AbandonedCart.customer_phone != "",
                )
                .scalar()
                or 0
            )
        except (SQLAlchemyError, OSError):
            db_session.rollback()

    # --- Hesitation reasons ---
    tables.add("cart_recovery_reasons")
    try:
        reason_rows = (
            db_session.query(CartRecoveryReason.reason)
            .filter(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.created_at >= start,
                CartRecoveryReason.created_at < end,
            )
            .all()
        )
        dist: dict[str, int] = {}
        for (reason_val,) in reason_rows:
            bucket = _hesitation_bucket(str(reason_val or ""))
            dist[bucket] = dist.get(bucket, 0) + 1
        bundle.hesitation_total = sum(dist.values())
        bundle.hesitation_distribution = dist
    except (SQLAlchemyError, OSError):
        db_session.rollback()

    # --- Recovery logs ---
    tables.add("cart_recovery_logs")
    try:
        log_rows = (
            db_session.query(CartRecoveryLog.status)
            .filter(
                CartRecoveryLog.store_slug == ss,
                CartRecoveryLog.created_at >= start,
                CartRecoveryLog.created_at < end,
            )
            .all()
        )
        for (st_raw,) in log_rows:
            st = (st_raw or "").strip().lower()
            if st in _MESSAGES_SENT_STATUSES:
                bundle.recovery_messages_sent += 1
            if st in _RETURN_LOG_STATUSES:
                bundle.recovery_returns += 1
            if st in _IGNORED_LOG_STATUSES:
                bundle.recovery_ignored += 1
            if st in _STOPPED_LOG_STATUSES:
                bundle.recovery_stopped += 1
            if st in _FAILED_STATUSES:
                bundle.recovery_failed += 1
    except (SQLAlchemyError, OSError):
        db_session.rollback()

    # --- Timeline replies + checkout hints ---
    tables.add("recovery_truth_timeline_events")
    try:
        tl_rows = (
            db_session.query(RecoveryTruthTimelineEvent.status)
            .filter(
                RecoveryTruthTimelineEvent.store_slug == ss,
                RecoveryTruthTimelineEvent.created_at >= start,
                RecoveryTruthTimelineEvent.created_at < end,
            )
            .all()
        )
        checkout_hits = 0
        for (st_raw,) in tl_rows:
            st = (st_raw or "").strip().lower()
            if st == _TIMELINE_REPLY:
                bundle.recovery_replies += 1
            if st in _TIMELINE_CHECKOUT_HINTS:
                checkout_hits += 1
        bundle.checkout_signal_count = checkout_hits
        bundle.checkout_data_available = checkout_hits > 0
    except (SQLAlchemyError, OSError):
        db_session.rollback()

    # --- Purchase truth ---
    tables.add("purchase_truth_records")
    try:
        bundle.purchase_truth_rows = int(
            db_session.query(func.count(PurchaseTruthRecord.id))
            .filter(
                PurchaseTruthRecord.store_slug == ss,
                PurchaseTruthRecord.purchase_time >= start,
                PurchaseTruthRecord.purchase_time < end,
            )
            .scalar()
            or 0
        )
        bundle.purchase_count = bundle.purchase_truth_rows
        bundle.recovery_purchases = bundle.purchase_truth_rows
    except (SQLAlchemyError, OSError):
        db_session.rollback()

    # --- Lifecycle closure ---
    tables.add("lifecycle_closure_records")
    try:
        bundle.lifecycle_closure_rows = int(
            db_session.query(func.count(LifecycleClosureRecord.id))
            .filter(
                LifecycleClosureRecord.store_slug == ss,
                LifecycleClosureRecord.closure_time >= start,
                LifecycleClosureRecord.closure_time < end,
            )
            .scalar()
            or 0
        )
    except (SQLAlchemyError, OSError):
        db_session.rollback()

    # --- Active recovery schedules (running recovery) ---
    tables.add("recovery_schedules")
    try:
        from services.recovery_restart_survival import STATUS_SCHEDULED  # noqa: PLC0415

        bundle.recovery_scheduled_active = int(
            db_session.query(func.count(RecoverySchedule.id))
            .filter(
                RecoverySchedule.store_slug == ss,
                RecoverySchedule.status == STATUS_SCHEDULED,
            )
            .scalar()
            or 0
        )
    except (SQLAlchemyError, OSError):
        db_session.rollback()

    # CartFlow has no storefront visitor analytics table in v1.
    bundle.visitor_data_available = False
    bundle.source_tables = sorted(tables)
    return bundle
