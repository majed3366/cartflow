# -*- coding: utf-8 -*-
"""
Dashboard/Home KPI temporal projections (INV-001 WP-5).

Consumes Platform Time Authority → Query Time Context → WP-3 filtering.
Rolling windows share ``resolve_knowledge_windows`` with Knowledge so
Dashboard and Knowledge cannot diverge for the same context.

Interval: half-open ``[start, end)`` naive UTC for DB predicates.
No private wall-clock window math. Not a second Time Authority.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason
from services.knowledge_time_authority_v1 import (
    KnowledgeTimeWindow,
    resolve_knowledge_query_context,
    resolve_knowledge_windows,
)
from services.time_authority import WindowRecipeId, window_for
from services.time_authority.query_context import QueryTimeContext

log = logging.getLogger("cartflow")

_LEGACY_SENT_LOG_STATUSES = frozenset({"sent_real", "mock_sent"})


def _naive_utc(dt: datetime) -> datetime:
    from services.time_authority import ensure_utc

    return ensure_utc(dt).replace(tzinfo=None)


def resolve_dashboard_rolling_windows(
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> KnowledgeTimeWindow:
    """
    Same rolling + comparison windows as Knowledge for the same context.

    Cross-surface contract: identical to ``resolve_knowledge_windows``.
    """
    return resolve_knowledge_windows(
        window_days=window_days, now=now, context=context
    )


def resolve_dashboard_today_window(
    *,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> tuple[datetime, datetime, QueryTimeContext]:
    """Governed calendar UTC today ``[start, end)`` naive bounds."""
    ctx = resolve_knowledge_query_context(now=now, context=context)
    tw = window_for(WindowRecipeId.TODAY, context=ctx)
    if not tw.ok:
        z = _naive_utc(ctx.authoritative_now)
        return z, z, ctx
    return _naive_utc(tw.start_at), _naive_utc(tw.end_at), ctx


def non_vip_scoped_base_query(dash_store: Optional[Any]) -> Optional[Any]:
    """Non-VIP scoped AbandonedCart query for merchant KPI projections."""
    if dash_store is None:
        return None
    try:
        from main import (  # noqa: PLC0415
            _normal_recovery_abandoned_scope_filter,
            merchant_vip_threshold_int,
        )

        base_q = db.session.query(AbandonedCart)
        _st_scope = _normal_recovery_abandoned_scope_filter(dash_store)
        if _st_scope is not None:
            base_q = base_q.filter(_st_scope)
        vip_th = merchant_vip_threshold_int(dash_store)
        if vip_th is not None:
            base_q = base_q.filter(
                func.coalesce(AbandonedCart.cart_value, 0) < float(vip_th)
            )
        return base_q
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return None


def merchant_kpi_today_projection(
    dash_store: Optional[Any],
    *,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> dict[str, Any]:
    """Daily KPIs — Time Authority ``today`` recipe."""
    out = {
        "abandoned_today": 0,
        "recovered_today": 0,
        "whatsapp_sent_today": 0,
        "recovered_revenue_today": 0.0,
    }
    bq = non_vip_scoped_base_query(dash_store)
    if bq is None:
        return out
    slug = (getattr(dash_store, "zid_store_id", None) or "").strip()
    start, end_day, _ctx = resolve_dashboard_today_window(now=now, context=context)
    try:
        out["abandoned_today"] = int(
            bq.filter(
                AbandonedCart.status == "abandoned",
                AbandonedCart.last_seen_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.last_seen_at >= start,
                AbandonedCart.last_seen_at < end_day,
            ).count()
            or 0
        )
        out["recovered_today"] = int(
            bq.filter(
                AbandonedCart.status == "recovered",
                AbandonedCart.recovered_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.recovered_at >= start,
                AbandonedCart.recovered_at < end_day,
            ).count()
            or 0
        )
        rev = (
            bq.filter(
                AbandonedCart.status == "recovered",
                AbandonedCart.recovered_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.recovered_at >= start,
                AbandonedCart.recovered_at < end_day,
            )
            .with_entities(func.coalesce(func.sum(AbandonedCart.cart_value), 0.0))
            .scalar()
        )
        out["recovered_revenue_today"] = float(rev or 0.0)
        if slug:
            out["whatsapp_sent_today"] = int(
                db.session.query(func.count(CartRecoveryLog.id))
                .filter(
                    CartRecoveryLog.store_slug == slug,
                    CartRecoveryLog.status.in_(_LEGACY_SENT_LOG_STATUSES),
                    CartRecoveryLog.created_at >= start,
                    CartRecoveryLog.created_at < end_day,
                )
                .scalar()
                or 0
            )
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("merchant_kpi_today_projection: %s", e)
    return out


def merchant_month_window_projection(
    dash_store: Optional[Any],
    *,
    days: int = 30,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> dict[str, Any]:
    """Rolling KPI summary — Time Authority ``last_n_days`` half-open window."""
    out = {
        "abandoned_total": 0,
        "recovered_total": 0,
        "recovery_pct": 0.0,
        "recovered_revenue": 0.0,
    }
    bq = non_vip_scoped_base_query(dash_store)
    if bq is None:
        return out
    tw = resolve_dashboard_rolling_windows(
        window_days=days, now=now, context=context
    )
    start, end = tw.start, tw.end
    try:
        out["abandoned_total"] = int(
            bq.filter(
                AbandonedCart.status == "abandoned",
                AbandonedCart.last_seen_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.last_seen_at >= start,
                AbandonedCart.last_seen_at < end,
            ).count()
            or 0
        )
        out["recovered_total"] = int(
            bq.filter(
                AbandonedCart.status == "recovered",
                AbandonedCart.recovered_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.recovered_at >= start,
                AbandonedCart.recovered_at < end,
            ).count()
            or 0
        )
        rev = (
            bq.filter(
                AbandonedCart.status == "recovered",
                AbandonedCart.recovered_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.recovered_at >= start,
                AbandonedCart.recovered_at < end,
            )
            .with_entities(func.coalesce(func.sum(AbandonedCart.cart_value), 0.0))
            .scalar()
        )
        out["recovered_revenue"] = float(rev or 0.0)
        denom = int(out["abandoned_total"]) + int(out["recovered_total"])
        if denom > 0:
            out["recovery_pct"] = round(
                100.0 * float(out["recovered_total"]) / float(denom), 1
            )
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("merchant_month_window_projection: %s", e)
    return out


def merchant_reason_counts_store_window(
    dash_store: Optional[Any],
    *,
    days: int = 7,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> dict[str, int]:
    """Hesitation reason counts — Time Authority ``last_n_days`` half-open window."""
    if dash_store is None:
        return {}
    slug = (getattr(dash_store, "zid_store_id", None) or "").strip()
    if not slug:
        return {}
    tw = resolve_dashboard_rolling_windows(
        window_days=days, now=now, context=context
    )
    start, end = tw.start, tw.end
    counts: dict[str, int] = {}
    try:
        rows = (
            db.session.query(CartRecoveryReason.reason, func.count(CartRecoveryReason.id))
            .filter(
                CartRecoveryReason.store_slug == slug,
                CartRecoveryReason.updated_at >= start,
                CartRecoveryReason.updated_at < end,
            )
            .group_by(CartRecoveryReason.reason)
            .all()
        )
        for rkey, c in rows:
            k = (rkey or "").strip().lower()
            if not k:
                continue
            counts[k] = int(c or 0)
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("merchant_reason_counts_store_window: %s", e)
    return counts


__all__ = [
    "merchant_kpi_today_projection",
    "merchant_month_window_projection",
    "merchant_reason_counts_store_window",
    "non_vip_scoped_base_query",
    "resolve_dashboard_rolling_windows",
    "resolve_dashboard_today_window",
]
