# -*- coding: utf-8 -*-
"""
Legacy Dashboard KPI temporal projections (INV-001 WP-5A).

TEMPORARY ownership of pre-WP-5 wall-clock window semantics extracted from
``main.py``. This is **not** Platform Time Authority and must **not** wire
WP-3 ``window_for`` until INV-001 WP-5 migrates these paths.

Legacy semantics preserved exactly:
- Calendar UTC today: ``[midnight, midnight+1day)``
- Rolling N-day month/reason windows: ``start = now - N days``, open-ended
  upper bound (``>= start`` only — no ``< end``)
- Wall ``datetime.now(timezone.utc)`` when ``now`` is omitted

Owner for migration/removal: **INV-001 WP-5**.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason

log = logging.getLogger("cartflow")

# Mirrors main._NORMAL_RECOVERY_SENT_LOG_STATUSES (legacy KPI WA count filter).
_LEGACY_SENT_LOG_STATUSES = frozenset({"sent_real", "mock_sent"})

# Temporary debt marker for WP-5 migration inventory.
LEGACY_KPI_TIME_OWNER = "INV-001 WP-5"
LEGACY_KPI_TIME_STATUS = "temporary_until_wp5"


def legacy_today_utc_bounds(
    *,
    now: Optional[datetime] = None,
) -> tuple[datetime, datetime]:
    """
    Legacy calendar-today UTC bounds (half-open).

    TEMPORARY — migrate to Time Authority ``today`` in WP-5.
    Production path (``now is None``) matches former ``main._merchant_ref_today_utc_bounds``.
    """
    now_u = datetime.now(timezone.utc) if now is None else now
    if now is not None and now_u.tzinfo is None:
        now_u = now_u.replace(tzinfo=timezone.utc)
    start = now_u.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = start + timedelta(days=1)
    return start, end_day


def legacy_rolling_start(
    *,
    days: int = 30,
    now: Optional[datetime] = None,
) -> datetime:
    """
    Legacy rolling-window start (open-ended upper bound at query site).

    TEMPORARY — migrate to Time Authority ``last_n_days`` in WP-5.
    """
    now_u = datetime.now(timezone.utc) if now is None else now
    if now is not None and now_u.tzinfo is None:
        now_u = now_u.replace(tzinfo=timezone.utc)
    return now_u - timedelta(days=max(1, int(days)))


def non_vip_scoped_base_query(dash_store: Optional[Any]) -> Optional[Any]:
    """
    Non-VIP scoped AbandonedCart query for merchant KPI projections.

    Closely coupled helper formerly ``main._merchant_ref_non_vip_scoped_base_query``.
    """
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
) -> dict[str, Any]:
    """Daily KPIs — UTC calendar day (legacy). TEMPORARY until WP-5."""
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
    start, end_day = legacy_today_utc_bounds(now=now)
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
) -> dict[str, Any]:
    """
    Rolling-window KPI summary (legacy open-ended ``>= start``).

    TEMPORARY until WP-5.
    """
    out = {
        "abandoned_total": 0,
        "recovered_total": 0,
        "recovery_pct": 0.0,
        "recovered_revenue": 0.0,
    }
    bq = non_vip_scoped_base_query(dash_store)
    if bq is None:
        return out
    start = legacy_rolling_start(days=days, now=now)
    try:
        out["abandoned_total"] = int(
            bq.filter(
                AbandonedCart.status == "abandoned",
                AbandonedCart.last_seen_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.last_seen_at >= start,
            ).count()
            or 0
        )
        out["recovered_total"] = int(
            bq.filter(
                AbandonedCart.status == "recovered",
                AbandonedCart.recovered_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.recovered_at >= start,
            ).count()
            or 0
        )
        rev = (
            bq.filter(
                AbandonedCart.status == "recovered",
                AbandonedCart.recovered_at.isnot(None),  # type: ignore[union-attr]
                AbandonedCart.recovered_at >= start,
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
) -> dict[str, int]:
    """
    Hesitation reason counts in rolling window (legacy open-ended ``>= start``).

    TEMPORARY until WP-5.
    """
    if dash_store is None:
        return {}
    slug = (getattr(dash_store, "zid_store_id", None) or "").strip()
    if not slug:
        return {}
    start = legacy_rolling_start(days=days, now=now)
    counts: dict[str, int] = {}
    try:
        rows = (
            db.session.query(CartRecoveryReason.reason, func.count(CartRecoveryReason.id))
            .filter(
                CartRecoveryReason.store_slug == slug,
                CartRecoveryReason.updated_at >= start,
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
    "LEGACY_KPI_TIME_OWNER",
    "LEGACY_KPI_TIME_STATUS",
    "legacy_rolling_start",
    "legacy_today_utc_bounds",
    "merchant_kpi_today_projection",
    "merchant_month_window_projection",
    "merchant_reason_counts_store_window",
    "non_vip_scoped_base_query",
]
