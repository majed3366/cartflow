# -*- coding: utf-8 -*-
"""Rebuild daily facts from raw (HOT window). Replace, never increment."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func

from extensions import db
from models import ProductExposureDailyFact, ProductExposureEvent
from services.product_exposure_v1.constants_v1 import (
    RAW_RETENTION_DAYS,
    TRUTH_VERSION_EXPOSURE_V1,
)
from services.product_exposure_v1.persist_v1 import day_bounds_utc, utc_date_from_occurred_at


def _as_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def recompute_facts_from_raw(
    *,
    store_slug: str,
    date_utc: str,
    product_id: Optional[str] = None,
) -> dict[str, dict[str, int]]:
    """product_id → {pdp_view_count, viewing_session_count, raw_row_count}."""
    day_start, day_end = day_bounds_utc(date_utc)
    q = db.session.query(
        ProductExposureEvent.product_id,
        func.count(ProductExposureEvent.id),
        func.count(func.distinct(ProductExposureEvent.session_id)),
    ).filter(
        ProductExposureEvent.store_slug == store_slug,
        ProductExposureEvent.occurred_at >= day_start,
        ProductExposureEvent.occurred_at < day_end,
    )
    if product_id:
        q = q.filter(ProductExposureEvent.product_id == product_id)
    q = q.group_by(ProductExposureEvent.product_id)
    out: dict[str, dict[str, int]] = {}
    for pid, views, sessions in q.all():
        out[str(pid)] = {
            "pdp_view_count": int(views or 0),
            "viewing_session_count": int(sessions or 0),
            "raw_row_count": int(views or 0),
        }
    return out


def rebuild_daily_facts(
    *,
    store_slug: Optional[str] = None,
    product_id: Optional[str] = None,
    since_date_utc: Optional[str] = None,
    until_date_utc: Optional[str] = None,
    last_30_days: bool = False,
) -> dict[str, Any]:
    """
    Tenant-scoped / product-scoped / last-30-days rebuild.

    Absolute replace from raw. If a sealed day still has raw and mismatches:
    unseal → replace → caller may reseal.
    """
    if not store_slug:
        return {"ok": False, "error": "store_slug_required", "replaced": 0}
    today = datetime.now(timezone.utc).date()
    if last_30_days and not since_date_utc:
        since_date_utc = (today - timedelta(days=RAW_RETENTION_DAYS)).isoformat()
    if not until_date_utc:
        until_date_utc = today.isoformat()

    q = db.session.query(ProductExposureEvent)
    if store_slug:
        q = q.filter(ProductExposureEvent.store_slug == store_slug)
    if product_id:
        q = q.filter(ProductExposureEvent.product_id == product_id)
    if since_date_utc:
        start, _ = day_bounds_utc(since_date_utc)
        q = q.filter(ProductExposureEvent.occurred_at >= start)
    if until_date_utc:
        _, end = day_bounds_utc(until_date_utc)
        q = q.filter(ProductExposureEvent.occurred_at < end)

    groups: dict[tuple[str, str, str], list[ProductExposureEvent]] = {}
    for row in q.all():
        slug = str(row.store_slug)
        pid = str(row.product_id)
        d = utc_date_from_occurred_at(_as_utc_naive(row.occurred_at))
        groups.setdefault((slug, pid, d), []).append(row)

    replaced = 0
    unsealed = 0
    for (slug, pid, d), rows in groups.items():
        views = len(rows)
        sessions = len({str(r.session_id) for r in rows})
        fact = (
            db.session.query(ProductExposureDailyFact)
            .filter(
                ProductExposureDailyFact.store_slug == slug,
                ProductExposureDailyFact.product_id == pid,
                ProductExposureDailyFact.date_utc == d,
            )
            .first()
        )
        mismatch = fact is None or int(fact.pdp_view_count) != views or int(
            fact.viewing_session_count
        ) != sessions
        if fact is not None and fact.sealed_at is not None and mismatch:
            fact.sealed_at = None
            fact.seal_truth_version = None
            fact.seal_source_window_start = None
            fact.seal_source_window_end = None
            fact.seal_source_row_count = None
            unsealed += 1
        if fact is None:
            fact = ProductExposureDailyFact(
                store_slug=slug,
                product_id=pid,
                date_utc=d,
                pdp_view_count=views,
                viewing_session_count=sessions,
                truth_version=TRUTH_VERSION_EXPOSURE_V1,
            )
            db.session.add(fact)
        else:
            fact.pdp_view_count = views
            fact.viewing_session_count = sessions
            fact.truth_version = TRUTH_VERSION_EXPOSURE_V1
        replaced += 1

    db.session.commit()
    return {
        "ok": True,
        "replaced": replaced,
        "unsealed": unsealed,
        "groups": len(groups),
        "since_date_utc": since_date_utc,
        "until_date_utc": until_date_utc,
    }
