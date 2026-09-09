# -*- coding: utf-8 -*-
"""
Same-transaction raw insert + daily fact UPSERT.

Postgres: pg_advisory_xact_lock on commercial_dedupe_key.
SQLite tests: per-key threading lock (same grain; not a store-wide mutex).
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import ProductCatalogEntry, ProductExposureDailyFact, ProductExposureEvent
from services.product_exposure_v1.constants_v1 import (
    COMMERCIAL_WINDOW_SECONDS,
    PAGE_CONTEXT_PDP,
    REASON_COMMERCIAL_DEDUPE,
    REASON_IDEMPOTENT_REPLAY,
    REASON_PERSISTED,
    TRUTH_VERSION_EXPOSURE_V1,
)

_sqlite_locks_guard = threading.Lock()
_sqlite_locks: dict[str, threading.Lock] = {}
_sqlite_write_lock = threading.Lock()  # SQLite stand-in for xact lock; not used on Postgres


@dataclass
class PersistResult:
    reason: str
    persisted: bool
    db_statements: int = 0
    event_pk: Optional[int] = None


def commercial_dedupe_key(store_slug: str, session_id: str, product_id: str) -> str:
    return f"{store_slug}|{session_id}|{product_id}|{PAGE_CONTEXT_PDP}"


def commercial_bucket_from_occurred_at(occurred_at: datetime) -> str:
    naive = _as_utc_naive(occurred_at).replace(microsecond=0)
    return naive.strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_date_from_occurred_at(occurred_at: datetime) -> str:
    return _as_utc_naive(occurred_at).strftime("%Y-%m-%d")


def day_bounds_utc(date_utc: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(date_utc, "%Y-%m-%d")
    return start, start + timedelta(days=1)


def catalog_owns_product(canonical_store_slug: str, product_id: str) -> bool:
    row = (
        db.session.query(ProductCatalogEntry.id)
        .filter(
            ProductCatalogEntry.store_slug == canonical_store_slug,
            ProductCatalogEntry.product_id == product_id,
        )
        .limit(1)
        .first()
    )
    return row is not None


def _as_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _is_postgres() -> bool:
    try:
        return db.engine.dialect.name == "postgresql"
    except Exception:  # noqa: BLE001
        return False


def _advisory_lock(key: str) -> Optional[threading.Lock]:
    if _is_postgres():
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        lock_id = int.from_bytes(digest[:8], "big", signed=True)
        db.session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": lock_id})
        return None
    with _sqlite_locks_guard:
        lk = _sqlite_locks.setdefault(key, threading.Lock())
    lk.acquire()
    return lk


def persist_commercial_exposure(
    *,
    event_id: str,
    store_slug: str,
    product_id: str,
    session_id: str,
    occurred_at: datetime,
    received_at: datetime,
    source: str,
    page_context: str,
    truth_version: str,
    commerce_platform: str,
    referrer_domain: Optional[str] = None,
    claimed_utm_source: Optional[str] = None,
    claimed_utm_medium: Optional[str] = None,
    claimed_utm_campaign: Optional[str] = None,
    _fail_after: Optional[str] = None,
) -> PersistResult:
    """
    Atomic persist. Raises SQLAlchemyError on DB failure (caller maps to 503).
    _fail_after: test hook 'raw' | 'fact' | 'commit' after the named step.
    """
    occurred_at = _as_utc_naive(occurred_at)
    received_at = _as_utc_naive(received_at)
    date_utc = utc_date_from_occurred_at(occurred_at)
    key = commercial_dedupe_key(store_slug, session_id, product_id)
    statements = 0
    sqlite_lock = None
    sqlite_write = False
    if not _is_postgres():
        _sqlite_write_lock.acquire()
        sqlite_write = True
    try:
        sqlite_lock = _advisory_lock(key)
        statements += 1
        db.session.expire_all()

        existing = (
            db.session.query(ProductExposureEvent.id)
            .filter(ProductExposureEvent.event_id == event_id)
            .limit(1)
            .first()
        )
        statements += 1
        if existing is not None:
            db.session.rollback()
            return PersistResult(
                reason=REASON_IDEMPOTENT_REPLAY,
                persisted=False,
                db_statements=statements,
                event_pk=int(existing[0]),
            )

        last = (
            db.session.query(ProductExposureEvent.occurred_at)
            .filter(
                ProductExposureEvent.store_slug == store_slug,
                ProductExposureEvent.session_id == session_id,
                ProductExposureEvent.product_id == product_id,
                ProductExposureEvent.page_context == PAGE_CONTEXT_PDP,
            )
            .order_by(ProductExposureEvent.occurred_at.desc())
            .limit(1)
            .first()
        )
        statements += 1
        if last is not None:
            last_at = _as_utc_naive(last[0])
            delta = (occurred_at - last_at).total_seconds()
            if 0 <= delta < COMMERCIAL_WINDOW_SECONDS:
                db.session.rollback()
                return PersistResult(
                    reason=REASON_COMMERCIAL_DEDUPE,
                    persisted=False,
                    db_statements=statements,
                )

        row = ProductExposureEvent(
            event_id=event_id,
            store_slug=store_slug,
            product_id=product_id,
            session_id=session_id,
            page_context=page_context,
            occurred_at=occurred_at,
            received_at=received_at,
            source=source,
            truth_version=truth_version,
            commercial_dedupe_key=key,
            commercial_bucket=commercial_bucket_from_occurred_at(occurred_at),
            commerce_platform=(commerce_platform or "unknown")[:32],
            identity_source="storefront_runtime",
            event_source="cartflow_storefront",
            referrer_domain=referrer_domain,
            claimed_utm_source=claimed_utm_source,
            claimed_utm_medium=claimed_utm_medium,
            claimed_utm_campaign=claimed_utm_campaign,
            lab_flag=False,
        )
        db.session.add(row)
        db.session.flush()
        statements += 1
        if _fail_after == "raw":
            raise RuntimeError("test_fail_after_raw")

        day_start, day_end = day_bounds_utc(date_utc)
        session_rows = (
            db.session.query(func.count(ProductExposureEvent.id))
            .filter(
                ProductExposureEvent.store_slug == store_slug,
                ProductExposureEvent.product_id == product_id,
                ProductExposureEvent.session_id == session_id,
                ProductExposureEvent.occurred_at >= day_start,
                ProductExposureEvent.occurred_at < day_end,
            )
            .scalar()
        )
        statements += 1
        session_delta = 1 if int(session_rows or 0) == 1 else 0

        _upsert_daily_fact(
            store_slug=store_slug,
            product_id=product_id,
            date_utc=date_utc,
            session_delta=session_delta,
        )
        statements += 1
        if _fail_after == "fact":
            raise RuntimeError("test_fail_after_fact")

        if _fail_after == "commit":
            db.session.commit()
            raise RuntimeError("test_fail_after_commit")

        db.session.commit()
        return PersistResult(
            reason=REASON_PERSISTED,
            persisted=True,
            db_statements=statements,
            event_pk=int(row.id),
        )
    except IntegrityError:
        db.session.rollback()
        replay = (
            db.session.query(ProductExposureEvent.id)
            .filter(ProductExposureEvent.event_id == event_id)
            .limit(1)
            .first()
        )
        statements += 1
        if replay is not None:
            return PersistResult(
                reason=REASON_IDEMPOTENT_REPLAY,
                persisted=False,
                db_statements=statements,
                event_pk=int(replay[0]),
            )
        raise
    except Exception:
        db.session.rollback()
        raise
    finally:
        if sqlite_lock is not None:
            try:
                sqlite_lock.release()
            except RuntimeError:
                pass
        if sqlite_write:
            _sqlite_write_lock.release()


def _upsert_daily_fact(
    *,
    store_slug: str,
    product_id: str,
    date_utc: str,
    session_delta: int,
) -> None:
    dialect = db.engine.dialect.name
    values = {
        "store_slug": store_slug,
        "product_id": product_id,
        "date_utc": date_utc,
        "pdp_view_count": 1,
        "viewing_session_count": int(session_delta),
        "truth_version": TRUTH_VERSION_EXPOSURE_V1,
    }
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(ProductExposureDailyFact).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["store_slug", "product_id", "date_utc"],
            set_={
                "pdp_view_count": ProductExposureDailyFact.pdp_view_count + 1,
                "viewing_session_count": (
                    ProductExposureDailyFact.viewing_session_count
                    + stmt.excluded.viewing_session_count
                ),
            },
        )
        db.session.execute(stmt)
        return

    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    stmt = sqlite_insert(ProductExposureDailyFact).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["store_slug", "product_id", "date_utc"],
        set_={
            "pdp_view_count": ProductExposureDailyFact.pdp_view_count + 1,
            "viewing_session_count": (
                ProductExposureDailyFact.viewing_session_count
                + stmt.excluded.viewing_session_count
            ),
        },
    )
    db.session.execute(stmt)


__all__ = [
    "PersistResult",
    "catalog_owns_product",
    "commercial_bucket_from_occurred_at",
    "commercial_dedupe_key",
    "day_bounds_utc",
    "persist_commercial_exposure",
    "utc_date_from_occurred_at",
]
