# -*- coding: utf-8 -*-
"""
exposure_retention_tick_v1 — seal then bounded raw/fact delete.

Default OFF. Oldest-first. Fail closed on unsealed raw.
Fact DELETE is a separate statement from raw DELETE.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, exists, func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ProductExposureDailyFact, ProductExposureEvent
from schema_product_exposure_v1 import ensure_product_exposure_schema
from services.product_exposure_v1.constants_v1 import (
    FACT_DELETE_MAX,
    FACT_RETENTION_DAYS,
    RAW_DELETE_MAX,
    RAW_RETENTION_DAYS,
    SEAL_BATCH_MAX,
    TRUTH_VERSION_EXPOSURE_V1,
)
from services.product_exposure_v1.metrics_v1 import (
    incr_exposure_metric,
    set_exposure_gauge,
)
from services.product_exposure_v1.persist_v1 import day_bounds_utc
from services.product_exposure_v1.rebuild_v1 import recompute_facts_from_raw

_log = logging.getLogger("cartflow.product_exposure.retention")

ENV_RETENTION_ENABLED = "CARTFLOW_EXPOSURE_RETENTION_ENABLED"

_tick_lock = threading.Lock()
_last_tick_result: dict[str, Any] = {}


def exposure_retention_enabled() -> bool:
    raw = (os.environ.get(ENV_RETENTION_ENABLED) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def hot_cutoff_utc(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)
    today = now.date()
    start = datetime.combine(today - timedelta(days=RAW_RETENTION_DAYS), datetime.min.time())
    return start


def fact_cutoff_date_utc(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(timezone.utc).date() if now.tzinfo else now.date()
    return (today - timedelta(days=FACT_RETENTION_DAYS)).isoformat()


def _seal_store_day(store_slug: str, date_utc: str) -> tuple[bool, str]:
    computed = recompute_facts_from_raw(store_slug=store_slug, date_utc=date_utc)
    facts = (
        db.session.query(ProductExposureDailyFact)
        .filter(
            ProductExposureDailyFact.store_slug == store_slug,
            ProductExposureDailyFact.date_utc == date_utc,
        )
        .all()
    )
    stored = {str(f.product_id): f for f in facts}
    if set(computed.keys()) != set(stored.keys()):
        return False, "coverage_mismatch"
    for pid, vals in computed.items():
        fact = stored[pid]
        if int(fact.pdp_view_count) != vals["pdp_view_count"]:
            return False, "view_count_mismatch"
        if int(fact.viewing_session_count) != vals["viewing_session_count"]:
            return False, "session_count_mismatch"
        if int(vals["raw_row_count"]) != vals["pdp_view_count"]:
            return False, "row_count_inconsistent"

    day_start, day_end = day_bounds_utc(date_utc)
    sealed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    for pid, fact in stored.items():
        fact.sealed_at = sealed_at
        fact.seal_truth_version = TRUTH_VERSION_EXPOSURE_V1
        fact.seal_source_window_start = day_start
        fact.seal_source_window_end = day_end
        fact.seal_source_row_count = computed[pid]["raw_row_count"]
    db.session.commit()
    return True, "sealed"


def _eligible_store_days(cutoff: datetime, limit: int) -> list[tuple[str, str]]:
    day_expr = func.date(ProductExposureEvent.occurred_at)
    rows = (
        db.session.query(ProductExposureEvent.store_slug, day_expr.label("date_utc"))
        .filter(ProductExposureEvent.occurred_at < cutoff)
        .group_by(ProductExposureEvent.store_slug, day_expr)
        .order_by(day_expr.asc(), ProductExposureEvent.store_slug.asc())
        .limit(limit)
        .all()
    )
    out: list[tuple[str, str]] = []
    for slug, d in rows:
        date_s = d if isinstance(d, str) else d.isoformat()
        out.append((str(slug), str(date_s)[:10]))
    return out


def _delete_sealed_raw(cutoff: datetime, limit: int) -> int:
    day_expr = func.date(ProductExposureEvent.occurred_at)
    unsealed_exists = exists().where(
        and_(
            ProductExposureDailyFact.store_slug == ProductExposureEvent.store_slug,
            ProductExposureDailyFact.date_utc == day_expr,
            ProductExposureDailyFact.sealed_at.is_(None),
        )
    )
    sealed_exists = exists().where(
        and_(
            ProductExposureDailyFact.store_slug == ProductExposureEvent.store_slug,
            ProductExposureDailyFact.date_utc == day_expr,
            ProductExposureDailyFact.sealed_at.isnot(None),
        )
    )
    ids = [
        int(r[0])
        for r in db.session.query(ProductExposureEvent.id)
        .filter(ProductExposureEvent.occurred_at < cutoff)
        .filter(sealed_exists)
        .filter(~unsealed_exists)
        .order_by(ProductExposureEvent.occurred_at.asc())
        .limit(limit)
        .all()
    ]
    if not ids:
        return 0
    deleted = (
        db.session.query(ProductExposureEvent)
        .filter(ProductExposureEvent.id.in_(ids))
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return int(deleted or 0)


def _delete_old_sealed_facts(cutoff_date: str, limit: int) -> int:
    ids = [
        int(r[0])
        for r in db.session.query(ProductExposureDailyFact.id)
        .filter(ProductExposureDailyFact.sealed_at.isnot(None))
        .filter(ProductExposureDailyFact.date_utc < cutoff_date)
        .order_by(ProductExposureDailyFact.date_utc.asc())
        .limit(limit)
        .all()
    ]
    if not ids:
        return 0
    deleted = (
        db.session.query(ProductExposureDailyFact)
        .filter(ProductExposureDailyFact.id.in_(ids))
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return int(deleted or 0)


def _update_unsealed_gauge(cutoff: datetime) -> int:
    day_expr = func.date(ProductExposureEvent.occurred_at)
    unsealed_exists = exists().where(
        and_(
            ProductExposureDailyFact.store_slug == ProductExposureEvent.store_slug,
            ProductExposureDailyFact.date_utc == day_expr,
            ProductExposureDailyFact.sealed_at.is_(None),
        )
    )
    no_facts = ~exists().where(
        and_(
            ProductExposureDailyFact.store_slug == ProductExposureEvent.store_slug,
            ProductExposureDailyFact.date_utc == day_expr,
        )
    )
    n = (
        db.session.query(ProductExposureEvent.store_slug, day_expr)
        .filter(ProductExposureEvent.occurred_at < cutoff)
        .filter(unsealed_exists | no_facts)
        .group_by(ProductExposureEvent.store_slug, day_expr)
        .count()
    )
    set_exposure_gauge("unsealed_days_past_retention_total", int(n or 0))
    oldest = (
        db.session.query(func.min(ProductExposureEvent.occurred_at))
        .scalar()
    )
    if oldest is not None:
        if getattr(oldest, "tzinfo", None) is not None:
            oldest = oldest.replace(tzinfo=None)
        age = (datetime.now(timezone.utc).replace(tzinfo=None) - oldest).days
        set_exposure_gauge("retention_oldest_raw_age_days", max(0, int(age)))
    else:
        set_exposure_gauge("retention_oldest_raw_age_days", 0)
    return int(n or 0)


def run_exposure_retention_tick(
    *,
    force: bool = False,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Bounded hourly tick. force=True runs even when the enable flag is OFF (tests).
    Skip if previous tick still holds the lock.
    """
    if not force and not exposure_retention_enabled():
        return {"ok": True, "skipped": True, "reason": "retention_disabled"}
    if not _tick_lock.acquire(blocking=False):
        return {"ok": True, "skipped": True, "reason": "tick_in_progress"}

    global _last_tick_result
    t0 = time.perf_counter()
    incr_exposure_metric("retention_run_total")
    result: dict[str, Any] = {
        "ok": True,
        "skipped": False,
        "task": "exposure_retention_tick_v1",
        "seal_attempts": 0,
        "seal_success": 0,
        "seal_failure": 0,
        "raw_deleted": 0,
        "facts_deleted": 0,
        "query_count": 0,
    }
    try:
        ensure_product_exposure_schema(db)
        cutoff = hot_cutoff_utc(now)
        fact_cut = fact_cutoff_date_utc(now)
        candidates = _eligible_store_days(cutoff, SEAL_BATCH_MAX)
        result["query_count"] += 1
        result["seal_attempts"] = len(candidates)
        for slug, date_utc in candidates:
            already = (
                db.session.query(ProductExposureDailyFact.id)
                .filter(
                    ProductExposureDailyFact.store_slug == slug,
                    ProductExposureDailyFact.date_utc == date_utc,
                    ProductExposureDailyFact.sealed_at.isnot(None),
                )
                .limit(1)
                .first()
            )
            unsealed = (
                db.session.query(ProductExposureDailyFact.id)
                .filter(
                    ProductExposureDailyFact.store_slug == slug,
                    ProductExposureDailyFact.date_utc == date_utc,
                    ProductExposureDailyFact.sealed_at.is_(None),
                )
                .limit(1)
                .first()
            )
            result["query_count"] += 2
            if already is not None and unsealed is None:
                continue
            ok, reason = _seal_store_day(slug, date_utc)
            result["query_count"] += 2
            if ok:
                result["seal_success"] += 1
                incr_exposure_metric("fact_seal_success_total")
            else:
                result["seal_failure"] += 1
                incr_exposure_metric("fact_seal_failure_total")
                _log.warning(
                    "exposure seal failed store=%s date=%s reason=%s",
                    slug[:64],
                    date_utc,
                    reason,
                )

        raw_n = _delete_sealed_raw(cutoff, RAW_DELETE_MAX)
        result["query_count"] += 2
        result["raw_deleted"] = raw_n
        if raw_n:
            incr_exposure_metric("retention_rows_deleted_total", raw_n)

        fact_n = _delete_old_sealed_facts(fact_cut, FACT_DELETE_MAX)
        result["query_count"] += 2
        result["facts_deleted"] = fact_n
        if fact_n:
            incr_exposure_metric("retention_fact_rows_deleted_total", fact_n)

        unsealed_n = _update_unsealed_gauge(cutoff)
        result["query_count"] += 2
        result["unsealed_days_past_retention"] = unsealed_n
        result["wall_ms"] = round((time.perf_counter() - t0) * 1000, 3)
        _last_tick_result = dict(result)
        return result
    except SQLAlchemyError as exc:
        db.session.rollback()
        incr_exposure_metric("retention_failure_total")
        result["ok"] = False
        result["error"] = "unavailable"
        result["wall_ms"] = round((time.perf_counter() - t0) * 1000, 3)
        _log.warning("exposure retention tick failed: %s", exc)
        _last_tick_result = dict(result)
        return result
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        incr_exposure_metric("retention_failure_total")
        result["ok"] = False
        result["error"] = "tick_error"
        result["wall_ms"] = round((time.perf_counter() - t0) * 1000, 3)
        _log.warning("exposure retention tick error: %s", exc)
        _last_tick_result = dict(result)
        return result
    finally:
        _tick_lock.release()


def last_exposure_retention_tick_result() -> dict[str, Any]:
    return dict(_last_tick_result)


def purge_exposure_for_store(store_slug: str, *, limit: int = 500) -> dict[str, Any]:
    """Bounded tenant purge — not the 30/400 retention policy."""
    slug = (store_slug or "").strip()
    if not slug:
        return {"raw_deleted": 0, "facts_deleted": 0}
    raw_ids = [
        int(r[0])
        for r in db.session.query(ProductExposureEvent.id)
        .filter(ProductExposureEvent.store_slug == slug)
        .limit(limit)
        .all()
    ]
    fact_ids = [
        int(r[0])
        for r in db.session.query(ProductExposureDailyFact.id)
        .filter(ProductExposureDailyFact.store_slug == slug)
        .limit(limit)
        .all()
    ]
    raw_n = 0
    fact_n = 0
    if raw_ids:
        raw_n = (
            db.session.query(ProductExposureEvent)
            .filter(ProductExposureEvent.id.in_(raw_ids))
            .delete(synchronize_session=False)
        )
    if fact_ids:
        fact_n = (
            db.session.query(ProductExposureDailyFact)
            .filter(ProductExposureDailyFact.id.in_(fact_ids))
            .delete(synchronize_session=False)
        )
    db.session.commit()
    return {"raw_deleted": int(raw_n or 0), "facts_deleted": int(fact_n or 0)}
