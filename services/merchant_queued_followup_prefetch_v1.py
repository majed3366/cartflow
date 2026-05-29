# -*- coding: utf-8 -*-
"""
Bulk prefetch for queued CartRecoveryLog rows used by merchant_group_stale_meta.

Removes per-group DB probes on the dashboard hot path; behavior matches
_has_recent_queued_followup exactly (in-memory filter on created_at >= since).
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartRecoveryLog

_per_group_db_queries: contextvars.ContextVar[int] = contextvars.ContextVar(
    "queued_followup_per_group_db_queries", default=0
)
_bulk_prefetch_queries: contextvars.ContextVar[int] = contextvars.ContextVar(
    "queued_followup_bulk_prefetch_queries", default=0
)

# Documented pre-optimization baseline from hot-path SQL audit (2026-05-29).
AUDIT_BASELINE_QUEUED_FOLLOWUP_QUERIES_PER_CHECK = 48
AUDIT_BASELINE_TOTAL_DASHBOARD_QUERIES_PER_CHECK = 658


@dataclass
class QueuedFollowupPrefetchIndex:
    """In-memory index of queued recovery logs for one store scope."""

    store_slug: str
    by_session_id: dict[str, list[datetime]] = field(default_factory=dict)
    by_cart_id: dict[str, list[datetime]] = field(default_factory=dict)
    by_recovery_key: dict[str, list[datetime]] = field(default_factory=dict)
    rows_loaded: int = 0
    bulk_query_count: int = 0

    def _append_ts(self, bucket: dict[str, list[datetime]], key: str, ts: datetime) -> None:
        k = (key or "").strip()
        if not k:
            return
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        bucket.setdefault(k, []).append(ts)

    def ingest_row(self, lg: Any) -> None:
        ct = getattr(lg, "created_at", None)
        if ct is None:
            return
        sid = (getattr(lg, "session_id", None) or "").strip()[:512]
        cid = (getattr(lg, "cart_id", None) or "").strip()[:255]
        rk = (getattr(lg, "recovery_key", None) or "").strip()[:512]
        if sid:
            self._append_ts(self.by_session_id, sid, ct)
        if cid:
            self._append_ts(self.by_cart_id, cid, ct)
        if rk:
            self._append_ts(self.by_recovery_key, rk, ct)

    def has_recent_for_abandoned(
        self,
        ac: Any,
        *,
        since_utc: datetime,
        recovery_key: str = "",
    ) -> bool:
        """Same predicate as _has_recent_queued_followup (OR on session/cart keys)."""
        del recovery_key  # indexed for diagnostics; match logic mirrors DB conds only
        if since_utc.tzinfo is None:
            since = since_utc.replace(tzinfo=timezone.utc)
        else:
            since = since_utc.astimezone(timezone.utc)

        sess = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
        zid = (getattr(ac, "zid_cart_id", None) or "").strip()[:255]

        def _any_since(rows: list[datetime]) -> bool:
            return any(ts >= since for ts in rows)

        if sess and _any_since(self.by_session_id.get(sess, [])):
            return True
        if zid:
            if _any_since(self.by_cart_id.get(zid, [])):
                return True
            if _any_since(self.by_session_id.get(zid, [])):
                return True
        return False


def queued_followup_prof_reset() -> None:
    _per_group_db_queries.set(0)
    _bulk_prefetch_queries.set(0)


def queued_followup_prof_record_per_group_db() -> None:
    _per_group_db_queries.set(int(_per_group_db_queries.get()) + 1)


def queued_followup_prof_record_bulk_prefetch() -> None:
    _bulk_prefetch_queries.set(int(_bulk_prefetch_queries.get()) + 1)


def queued_followup_prof_snapshot() -> dict[str, int]:
    return {
        "queued_followup_per_group_db_queries": int(_per_group_db_queries.get()),
        "queued_followup_bulk_prefetch_queries": int(_bulk_prefetch_queries.get()),
    }


def build_queued_followup_comparison(
    *,
    avg_total_dashboard_queries: float,
    avg_queued_followup_per_group_db: float,
    avg_queued_followup_bulk_prefetch: float,
) -> dict[str, Any]:
    after_per_group = round(float(avg_queued_followup_per_group_db), 2)
    after_bulk = round(float(avg_queued_followup_bulk_prefetch), 2)
    after_total = round(float(avg_total_dashboard_queries), 2)
    before_qf = float(AUDIT_BASELINE_QUEUED_FOLLOWUP_QUERIES_PER_CHECK)
    before_total = float(AUDIT_BASELINE_TOTAL_DASHBOARD_QUERIES_PER_CHECK)
    saved_qf = round(before_qf - after_per_group, 2)
    saved_total = round(before_total - after_total, 2)
    return {
        "before_baseline_per_dashboard_check": {
            "queued_followup_queries": int(AUDIT_BASELINE_QUEUED_FOLLOWUP_QUERIES_PER_CHECK),
            "total_dashboard_queries": int(AUDIT_BASELINE_TOTAL_DASHBOARD_QUERIES_PER_CHECK),
            "source": "hot_path_query_audit_pre_optimization",
        },
        "after_avg_per_dashboard_check": {
            "queued_followup_per_group_db_queries": after_per_group,
            "queued_followup_bulk_prefetch_queries": after_bulk,
            "total_dashboard_queries": after_total,
        },
        "delta_per_dashboard_check": {
            "queued_followup_queries_removed": saved_qf,
            "total_dashboard_queries_saved": saved_total,
        },
        "n_plus_one_removed": after_per_group <= 0,
    }


def bulk_load_queued_followup_index(
    *,
    store_slug: str,
    session_ids: set[str],
    cart_ids: set[str],
    recovery_keys: Optional[set[str]] = None,
) -> QueuedFollowupPrefetchIndex:
    """
    Single bulk query for queued logs matching session/cart keys in scope.
    created_at filtering happens per-group in has_recent_for_abandoned.
    """
    slug = (store_slug or "").strip()[:255]
    idx = QueuedFollowupPrefetchIndex(store_slug=slug)
    if not slug:
        return idx

    try:
        from services.dashboard_normal_carts_guard_v1 import (  # noqa: PLC0415
            dashboard_nc_skip_optional_db,
        )

        if dashboard_nc_skip_optional_db():
            return idx
    except Exception:  # noqa: BLE001
        pass

    combined = set(session_ids or ()) | set(cart_ids or ())
    or_parts: list[Any] = []
    if combined:
        or_parts.append(CartRecoveryLog.session_id.in_(list(combined)))
    if cart_ids:
        or_parts.append(CartRecoveryLog.cart_id.in_(list(cart_ids)))
    rk_list = [k for k in (recovery_keys or set()) if (k or "").strip()]
    if rk_list:
        or_parts.append(CartRecoveryLog.recovery_key.in_(rk_list))
    if not or_parts:
        return idx

    try:
        rows = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.store_slug == slug,
                CartRecoveryLog.status == "queued",
                or_(*or_parts),
            )
            .all()
        )
        queued_followup_prof_record_bulk_prefetch()
        idx.bulk_query_count = 1
        for lg in rows:
            idx.ingest_row(lg)
        idx.rows_loaded = len(rows)
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
    return idx


__all__ = [
    "AUDIT_BASELINE_QUEUED_FOLLOWUP_QUERIES_PER_CHECK",
    "AUDIT_BASELINE_TOTAL_DASHBOARD_QUERIES_PER_CHECK",
    "QueuedFollowupPrefetchIndex",
    "build_queued_followup_comparison",
    "bulk_load_queued_followup_index",
    "queued_followup_prof_record_bulk_prefetch",
    "queued_followup_prof_record_per_group_db",
    "queued_followup_prof_reset",
    "queued_followup_prof_snapshot",
]
