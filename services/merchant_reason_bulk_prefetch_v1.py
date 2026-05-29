# -*- coding: utf-8 -*-
"""
Single bulk CartRecoveryReason load for merchant normal-carts batch reads.

Replaces dual store-scoped + any-store SQL round-trips with one query and
in-memory maps preserving precedence (current store first, any-store fallback).
"""
from __future__ import annotations

import contextvars
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartRecoveryReason

# Pre-optimization structural baseline (hot-path audit, 2026-05-29).
AUDIT_BASELINE_REASON_BULK_QUERIES_PER_CHECK = 2

_bulk_query_count: contextvars.ContextVar[int] = contextvars.ContextVar(
    "reason_bulk_query_count", default=0
)
_fallback_rows_used: contextvars.ContextVar[int] = contextvars.ContextVar(
    "reason_fallback_rows_used", default=0
)


def reason_bulk_prof_reset() -> None:
    _bulk_query_count.set(0)
    _fallback_rows_used.set(0)


def reason_bulk_prof_record_query(n: int = 1) -> None:
    _bulk_query_count.set(int(_bulk_query_count.get()) + max(0, int(n)))


def reason_bulk_prof_record_fallback_rows(n: int) -> None:
    _fallback_rows_used.set(int(_fallback_rows_used.get()) + max(0, int(n)))


def reason_bulk_prof_snapshot() -> dict[str, int]:
    return {
        "reason_bulk_queries_after": int(_bulk_query_count.get()),
        "fallback_reason_rows_used": int(_fallback_rows_used.get()),
    }


def build_reason_bulk_comparison(
    *,
    avg_total_dashboard_queries: float,
    avg_reason_bulk_queries_after: float,
    avg_fallback_reason_rows_used: float,
) -> dict[str, Any]:
    before = float(AUDIT_BASELINE_REASON_BULK_QUERIES_PER_CHECK)
    after = round(float(avg_reason_bulk_queries_after), 2)
    return {
        "reason_bulk_queries_before": int(AUDIT_BASELINE_REASON_BULK_QUERIES_PER_CHECK),
        "before_baseline_per_dashboard_check": {
            "reason_bulk_queries": int(AUDIT_BASELINE_REASON_BULK_QUERIES_PER_CHECK),
            "source": "hot_path_audit_pre_reason_bulk_merge",
        },
        "after_avg_per_dashboard_check": {
            "reason_bulk_queries": after,
            "fallback_reason_rows_used": round(float(avg_fallback_reason_rows_used), 2),
            "total_dashboard_queries": round(float(avg_total_dashboard_queries), 2),
        },
        "delta_per_dashboard_check": {
            "reason_bulk_queries_removed": round(before - after, 2),
        },
        "dual_query_eliminated": (
            round(float(avg_reason_bulk_queries_after), 2) > 0
            and after <= 1.0
            and before >= 2.0
        ),
    }


def build_reason_maps_from_rows(
    rows: list[Any],
    *,
    store_slug: str,
) -> tuple[dict[str, CartRecoveryReason], dict[str, CartRecoveryReason], int]:
    """
    Build reason_store_by_session and reason_any_by_session from rows ordered
    by updated_at desc (same as legacy dual-query first-hit semantics).
    """
    slug = (store_slug or "").strip()
    reason_store_by_session: dict[str, CartRecoveryReason] = {}
    reason_any_by_session: dict[str, CartRecoveryReason] = {}
    for r in rows or ():
        k = (getattr(r, "session_id", None) or "").strip()[:512]
        if not k:
            continue
        if k not in reason_any_by_session:
            reason_any_by_session[k] = r
        if slug:
            rs = (getattr(r, "store_slug", None) or "").strip()
            if rs == slug and k not in reason_store_by_session:
                reason_store_by_session[k] = r
    fallback_used = sum(
        1 for k in reason_any_by_session if k not in reason_store_by_session
    )
    return reason_store_by_session, reason_any_by_session, fallback_used


def bulk_load_reason_maps_by_session(
    *,
    store_slug: str,
    session_keys: set[str] | list[str],
) -> tuple[dict[str, CartRecoveryReason], dict[str, CartRecoveryReason], int, int]:
    """
    One SQL round-trip for all candidate reason rows; returns
    (reason_store_by_session, reason_any_by_session, rows_fetched, fallback_rows_used).
    """
    keys = [
        (str(k).strip()[:512])
        for k in (session_keys or ())
        if (str(k).strip()[:512])
    ]
    if not keys:
        return {}, {}, 0, 0
    slug = (store_slug or "").strip()
    try:
        reason_bulk_prof_record_query(1)
        rows = (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.session_id.in_(list(keys)))
            .order_by(CartRecoveryReason.updated_at.desc())
            .all()
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return {}, {}, 0, 0
    store_map, any_map, fallback_used = build_reason_maps_from_rows(
        rows, store_slug=slug
    )
    reason_bulk_prof_record_fallback_rows(fallback_used)
    return store_map, any_map, len(rows), fallback_used


__all__ = [
    "AUDIT_BASELINE_REASON_BULK_QUERIES_PER_CHECK",
    "build_reason_bulk_comparison",
    "build_reason_maps_from_rows",
    "bulk_load_reason_maps_by_session",
    "reason_bulk_prof_record_fallback_rows",
    "reason_bulk_prof_record_query",
    "reason_bulk_prof_reset",
    "reason_bulk_prof_snapshot",
]
