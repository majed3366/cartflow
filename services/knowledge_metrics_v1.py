# -*- coding: utf-8 -*-
"""
Knowledge Layer v1 — read-only metric aggregation.

Accepts db session + store_slug + date window; returns metrics only (no Arabic copy).
Temporal windows from Time Authority via knowledge_time_authority_v1 (WP-4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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
from services.knowledge_purchase_attribution_v1 import count_knowledge_purchase_attribution
from services.knowledge_time_authority_v1 import (
    KnowledgeTimeWindow,
    resolve_knowledge_windows,
)
from services.reason_template_recovery import canonical_reason_template_key
from services.vip_operational_truth_v1 import (
    VIP_MERCHANT_ALERT_LOG_STATUSES,
    VIP_MERCHANT_ALERT_REASON_TAGS,
)

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

_VIP_HESITATION_REASON_TAGS = frozenset(
    {
        "vip_phone_capture",
        "vip_merchant_alert",
        "vip_phone_capture_merchant",
    }
)


def _load_vip_session_ids(db_session: Any, store_id: int) -> set[str]:
    try:
        rows = (
            db_session.query(AbandonedCart.recovery_session_id)
            .filter(
                AbandonedCart.store_id == store_id,
                AbandonedCart.vip_mode.is_(True),
                AbandonedCart.recovery_session_id.isnot(None),
                AbandonedCart.recovery_session_id != "",
            )
            .distinct()
            .all()
        )
        return {str(r[0]).strip() for r in rows if r and r[0]}
    except (SQLAlchemyError, OSError):
        db_session.rollback()
        return set()


def _is_vip_lane_event(
    *,
    session_id: str,
    reason_tag: str,
    status: str,
    vip_sessions: set[str],
) -> bool:
    sid = (session_id or "").strip()
    rt = (reason_tag or "").strip().lower()
    st = (status or "").strip().lower()
    if rt in VIP_MERCHANT_ALERT_REASON_TAGS:
        return True
    if st in VIP_MERCHANT_ALERT_LOG_STATUSES:
        return True
    if sid and sid in vip_sessions:
        return True
    return False


@dataclass
class KnowledgeMetricsBundle:
    store_slug: str
    window_days: int
    window_start: datetime
    window_end: datetime
    store_resolved: bool = False
    store_id: Optional[int] = None

    # Traffic / demand (CartFlow-visible only; normal lane excludes VIP)
    visitor_data_available: bool = False
    cart_count: int = 0
    prev_cart_count: int = 0
    carts_with_phone: int = 0
    vip_cart_count: int = 0
    prev_vip_cart_count: int = 0

    # Conversion funnel gaps
    checkout_data_available: bool = False
    checkout_signal_count: int = 0
    purchase_count: int = 0
    attributed_recovery_purchase_count: int = 0
    purchase_attribution_unknown_count: int = 0
    purchase_attribution_evaluated_count: int = 0

    # Hesitation (normal lane)
    hesitation_total: int = 0
    hesitation_distribution: dict[str, int] = field(default_factory=dict)

    # Recovery activity (normal lane)
    recovery_messages_sent: int = 0
    recovery_replies: int = 0
    recovery_returns: int = 0
    recovery_ignored: int = 0
    recovery_stopped: int = 0
    recovery_failed: int = 0
    recovery_scheduled_active: int = 0

    # Truth layers
    purchase_truth_rows: int = 0
    lifecycle_closure_rows: int = 0

    # VIP evidence bucket — isolated from normal metrics/confidence
    vip_evidence: dict[str, Any] = field(default_factory=dict)

    source_tables: list[str] = field(default_factory=list)

    # Internal Time Authority evidence — never merchant-serialized via to_dict
    time_window: Optional[KnowledgeTimeWindow] = field(default=None, repr=False)

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
            "vip_cart_count": self.vip_cart_count,
            "prev_vip_cart_count": self.prev_vip_cart_count,
            "checkout_data_available": self.checkout_data_available,
            "checkout_signal_count": self.checkout_signal_count,
            "purchase_count": self.purchase_count,
            "attributed_recovery_purchase_count": self.attributed_recovery_purchase_count,
            "purchase_attribution_unknown_count": self.purchase_attribution_unknown_count,
            "purchase_attribution_evaluated_count": self.purchase_attribution_evaluated_count,
            "hesitation_total": self.hesitation_total,
            "hesitation_distribution": dict(self.hesitation_distribution),
            "recovery_messages_sent": self.recovery_messages_sent,
            "recovery_replies": self.recovery_replies,
            "recovery_returns": self.recovery_returns,
            "recovery_ignored": self.recovery_ignored,
            "recovery_stopped": self.recovery_stopped,
            "recovery_failed": self.recovery_failed,
            "recovery_scheduled_active": self.recovery_scheduled_active,
            "purchase_truth_rows": self.purchase_truth_rows,
            "lifecycle_closure_rows": self.lifecycle_closure_rows,
            "vip_evidence": dict(self.vip_evidence),
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
    VIP activity is counted in ``vip_evidence`` only — not normal lane metrics.
    """
    ss = (store_slug or "").strip()[:255]
    tw = resolve_knowledge_windows(window_days=window_days, now=now)
    start, end, prev_start = tw.start, tw.end, tw.prev_start
    bundle = KnowledgeMetricsBundle(
        store_slug=ss,
        window_days=tw.window_days,
        window_start=start,
        window_end=end,
        time_window=tw,
    )
    if not ss:
        return bundle

    tables: set[str] = set()
    vip_sessions: set[str] = set()

    try:
        from services.vip_abandoned_cart_phone import (  # noqa: PLC0415
            resolve_store_row_for_cartflow_slug_session,
        )

        store_row = resolve_store_row_for_cartflow_slug_session(db_session, ss)
        if store_row is not None:
            bundle.store_resolved = True
            bundle.store_id = int(getattr(store_row, "id", 0) or 0) or None
            if bundle.store_id:
                vip_sessions = _load_vip_session_ids(db_session, bundle.store_id)
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db_session.rollback()
        store_row = None

    vip_bucket: dict[str, Any] = {
        "isolated": True,
        "session_count": len(vip_sessions),
        "cart_count": 0,
        "prev_cart_count": 0,
        "hesitation_total": 0,
        "hesitation_distribution": {},
        "recovery_messages_sent": 0,
        "recovery_replies": 0,
        "recovery_returns": 0,
        "merchant_alert_logs": 0,
    }

    # --- Abandoned carts (demand proxy; normal lane excludes VIP) ---
    if bundle.store_id:
        tables.add("abandoned_carts")
        try:
            bundle.cart_count = int(
                db_session.query(func.count(AbandonedCart.id))
                .filter(
                    AbandonedCart.store_id == bundle.store_id,
                    AbandonedCart.vip_mode.is_(False),
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
                    AbandonedCart.vip_mode.is_(False),
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
                    AbandonedCart.vip_mode.is_(False),
                    AbandonedCart.first_seen_at >= start,
                    AbandonedCart.first_seen_at < end,
                    AbandonedCart.customer_phone.isnot(None),
                    AbandonedCart.customer_phone != "",
                )
                .scalar()
                or 0
            )
            vip_bucket["cart_count"] = int(
                db_session.query(func.count(AbandonedCart.id))
                .filter(
                    AbandonedCart.store_id == bundle.store_id,
                    AbandonedCart.vip_mode.is_(True),
                    AbandonedCart.first_seen_at >= start,
                    AbandonedCart.first_seen_at < end,
                )
                .scalar()
                or 0
            )
            vip_bucket["prev_cart_count"] = int(
                db_session.query(func.count(AbandonedCart.id))
                .filter(
                    AbandonedCart.store_id == bundle.store_id,
                    AbandonedCart.vip_mode.is_(True),
                    AbandonedCart.first_seen_at >= prev_start,
                    AbandonedCart.first_seen_at < start,
                )
                .scalar()
                or 0
            )
            bundle.vip_cart_count = int(vip_bucket["cart_count"])
            bundle.prev_vip_cart_count = int(vip_bucket["prev_cart_count"])
        except (SQLAlchemyError, OSError):
            db_session.rollback()

    # --- Hesitation reasons (normal lane; VIP sessions/tags excluded) ---
    tables.add("cart_recovery_reasons")
    try:
        reason_rows = (
            db_session.query(CartRecoveryReason.reason, CartRecoveryReason.session_id)
            .filter(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.created_at >= start,
                CartRecoveryReason.created_at < end,
            )
            .all()
        )
        dist: dict[str, int] = {}
        vip_dist: dict[str, int] = {}
        for reason_val, session_val in reason_rows:
            reason_s = str(reason_val or "")
            session_s = (str(session_val or "")).strip()
            raw = reason_s.strip().lower()
            if raw in _VIP_HESITATION_REASON_TAGS or session_s in vip_sessions:
                bucket = _hesitation_bucket(reason_s)
                vip_dist[bucket] = vip_dist.get(bucket, 0) + 1
                continue
            bucket = _hesitation_bucket(reason_s)
            dist[bucket] = dist.get(bucket, 0) + 1
        bundle.hesitation_total = sum(dist.values())
        bundle.hesitation_distribution = dist
        vip_bucket["hesitation_total"] = sum(vip_dist.values())
        vip_bucket["hesitation_distribution"] = vip_dist
    except (SQLAlchemyError, OSError):
        db_session.rollback()

    # --- Recovery logs (normal lane; VIP merchant alerts excluded) ---
    tables.add("cart_recovery_logs")
    try:
        log_rows = (
            db_session.query(
                CartRecoveryLog.status,
                CartRecoveryLog.session_id,
                CartRecoveryLog.reason_tag,
            )
            .filter(
                CartRecoveryLog.store_slug == ss,
                CartRecoveryLog.created_at >= start,
                CartRecoveryLog.created_at < end,
            )
            .all()
        )
        for st_raw, sid_raw, rt_raw in log_rows:
            st = (st_raw or "").strip().lower()
            sid = (str(sid_raw or "")).strip()
            rt = (str(rt_raw or "")).strip()
            if _is_vip_lane_event(
                session_id=sid,
                reason_tag=rt,
                status=st,
                vip_sessions=vip_sessions,
            ):
                if st in _MESSAGES_SENT_STATUSES or st in VIP_MERCHANT_ALERT_LOG_STATUSES:
                    vip_bucket["recovery_messages_sent"] = int(vip_bucket["recovery_messages_sent"]) + 1
                if rt in VIP_MERCHANT_ALERT_REASON_TAGS or st in VIP_MERCHANT_ALERT_LOG_STATUSES:
                    vip_bucket["merchant_alert_logs"] = int(vip_bucket["merchant_alert_logs"]) + 1
                continue
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

    # --- Timeline replies + checkout hints (normal lane) ---
    tables.add("recovery_truth_timeline_events")
    try:
        tl_rows = (
            db_session.query(
                RecoveryTruthTimelineEvent.status,
                RecoveryTruthTimelineEvent.session_id,
            )
            .filter(
                RecoveryTruthTimelineEvent.store_slug == ss,
                RecoveryTruthTimelineEvent.created_at >= start,
                RecoveryTruthTimelineEvent.created_at < end,
            )
            .all()
        )
        checkout_hits = 0
        for st_raw, sid_raw in tl_rows:
            st = (st_raw or "").strip().lower()
            sid = (str(sid_raw or "")).strip()
            if sid in vip_sessions:
                if st == _TIMELINE_REPLY:
                    vip_bucket["recovery_replies"] = int(vip_bucket["recovery_replies"]) + 1
                if st in _TIMELINE_CHECKOUT_HINTS:
                    pass
                continue
            if st == _TIMELINE_REPLY:
                bundle.recovery_replies += 1
            if st in _TIMELINE_CHECKOUT_HINTS:
                checkout_hits += 1
        bundle.checkout_signal_count = checkout_hits
        bundle.checkout_data_available = checkout_hits > 0
    except (SQLAlchemyError, OSError):
        db_session.rollback()

    # --- Purchase truth + honest attribution counts ---
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
        attribution = count_knowledge_purchase_attribution(
            db_session,
            ss,
            window_start=start,
            window_end=end,
        )
        bundle.purchase_count = attribution.purchase_count
        bundle.attributed_recovery_purchase_count = attribution.attributed_recovery_purchase_count
        bundle.purchase_attribution_unknown_count = attribution.purchase_attribution_unknown_count
        bundle.purchase_attribution_evaluated_count = attribution.purchase_attribution_evaluated_count
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

    bundle.vip_evidence = vip_bucket
    bundle.visitor_data_available = False
    bundle.source_tables = sorted(tables)
    return bundle
