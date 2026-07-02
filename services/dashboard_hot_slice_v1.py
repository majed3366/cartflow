# -*- coding: utf-8 -*-
"""
Dashboard hot slice — bounded live rows merged into snapshot normal-carts (Phase 1).

Architecture: dashboard = snapshot_rows + hot_live_rows (merge by recovery_key).
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.dashboard_snapshot_hot_path_guard_v1 import dashboard_hot_slice_build_scope

log = logging.getLogger("cartflow")

ENV_HOT_SLICE = "CARTFLOW_DASHBOARD_HOT_SLICE"
HOT_SLICE_HOURS = 36
HOT_SLICE_MAX_ROWS = 25
HOT_SLICE_MAX_QUERIES = 15
HOT_SLICE_TARGET_MS = 500.0
NORMAL_CARTS_PAGE_LIMIT = 50


def _env_truthy(name: str, *, default: bool = True) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def dashboard_hot_slice_enabled() -> bool:
    return _env_truthy(ENV_HOT_SLICE, default=True)


def hot_slice_last_seen_cutoff(*, now: Optional[datetime] = None) -> datetime:
    now_u = now or datetime.now(timezone.utc)
    if now_u.tzinfo is None:
        now_u = now_u.replace(tzinfo=timezone.utc)
    return now_u - timedelta(hours=HOT_SLICE_HOURS)


def _row_recovery_key(row: dict[str, Any]) -> str:
    rk = (str(row.get("recovery_key") or "").strip())[:512]
    if rk:
        return rk
    store = (str(row.get("store_slug") or row.get("merchant_store_slug") or "").strip())[:255]
    cid = (str(row.get("zid_cart_id") or row.get("cart_id") or "").strip())[:255]
    sid = (str(row.get("recovery_session_id") or row.get("session_id") or "").strip())[:512]
    if store and cid:
        return f"{store}:{cid}"[:512]
    if store and sid:
        return f"{store}:{sid}"[:512]
    return ""


def merge_hot_slice_active_rows(
    snapshot_rows: list[dict[str, Any]],
    hot_rows: list[dict[str, Any]],
    *,
    page_limit: int = NORMAL_CARTS_PAGE_LIMIT,
) -> list[dict[str, Any]]:
    """Merge by recovery_key — hot row wins; no duplicates; hot rows first."""
    cap = max(1, int(page_limit or NORMAL_CARTS_PAGE_LIMIT))
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []

    for row in hot_rows:
        if not isinstance(row, dict):
            continue
        rk = _row_recovery_key(row)
        if rk:
            if rk in seen:
                continue
            seen.add(rk)
        merged.append(row)
        if len(merged) >= cap:
            return merged

    for row in snapshot_rows:
        if not isinstance(row, dict):
            continue
        rk = _row_recovery_key(row)
        if rk:
            if rk in seen:
                continue
            seen.add(rk)
        merged.append(row)
        if len(merged) >= cap:
            break

    return merged


def build_hot_slice_active_rows(
    dash_store: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
  Bounded live query for recent abandons — max 25 rows, ≤15 business queries.
  """
    from services.normal_carts_dashboard_batch_v1 import (  # noqa: PLC0415
        build_normal_carts_unified_rows,
        normal_carts_dashboard_query_prof_reset,
        normal_carts_dashboard_query_prof_snapshot,
    )

    meta: dict[str, Any] = {
        "hot_slice_rows": 0,
        "hot_slice_ms": 0.0,
        "hot_slice_queries": 0,
        "hot_slice_degraded": False,
        "hot_slice_reason": "",
    }
    if dash_store is None:
        meta["hot_slice_reason"] = "missing_store"
        return [], meta

    t0 = time.perf_counter()
    normal_carts_dashboard_query_prof_reset()
    cutoff = hot_slice_last_seen_cutoff()

    try:
        with dashboard_hot_slice_build_scope():
            active_rows, _archived, _prof, perf = build_normal_carts_unified_rows(
                dash_store,
                page_limit=HOT_SLICE_MAX_ROWS,
                page_offset=0,
                hot_slice_last_seen_cutoff=cutoff,
                hot_slice_row_cap=HOT_SLICE_MAX_ROWS,
                hot_slice_max_pick=HOT_SLICE_MAX_ROWS,
                hot_slice_skip_augment=True,
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("dashboard hot slice build failed: %s", exc)
        meta["hot_slice_degraded"] = True
        meta["hot_slice_reason"] = f"build_error:{type(exc).__name__}"
        meta["hot_slice_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
        return [], meta

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    q_count = int(normal_carts_dashboard_query_prof_snapshot().get("business_query_count") or 0)
    if perf.query_count:
        q_count = max(q_count, int(perf.query_count))

    meta["hot_slice_ms"] = round(elapsed_ms, 1)
    meta["hot_slice_queries"] = q_count
    meta["hot_slice_rows"] = len(active_rows)

    if q_count > HOT_SLICE_MAX_QUERIES:
        meta["hot_slice_degraded"] = True
        meta["hot_slice_reason"] = f"query_budget_exceeded_{q_count}"
        log.warning(
            "[DASHBOARD HOT SLICE] degraded reason=query_budget_exceeded "
            "queries=%s max=%s",
            q_count,
            HOT_SLICE_MAX_QUERIES,
        )
        return [], meta

    if elapsed_ms > HOT_SLICE_TARGET_MS:
        meta["hot_slice_degraded"] = True
        meta["hot_slice_reason"] = f"slow_{round(elapsed_ms)}ms"
        log.warning(
            "[DASHBOARD HOT SLICE] degraded reason=slow elapsed_ms=%.1f",
            elapsed_ms,
        )

    if perf.degraded or perf.partial:
        meta["hot_slice_degraded"] = True
        meta["hot_slice_reason"] = perf.timeout_stage or "partial_build"

    return list(active_rows), meta


def apply_hot_slice_to_normal_carts_payload(
    payload: dict[str, Any],
    *,
    store_slug: str,
    dash_store: Any = None,
) -> dict[str, Any]:
    """
    Merge hot live rows into snapshot normal-carts payload.

    Store-level counters and refresh token remain from snapshot (unchanged).
    """
    if not dashboard_hot_slice_enabled():
        payload.setdefault("data_freshness", "snapshot_only")
        return payload
    if not isinstance(payload, dict):
        return payload

    slug = (store_slug or "").strip()
    if dash_store is None and slug:
        try:
            from main import _dashboard_recovery_store_row  # noqa: PLC0415

            dash_store = _dashboard_recovery_store_row()
        except Exception:  # noqa: BLE001
            dash_store = None

    snapshot_rows = list(payload.get("merchant_carts_page_rows") or [])
    hot_rows, hot_meta = build_hot_slice_active_rows(dash_store)

    merged = merge_hot_slice_active_rows(snapshot_rows, hot_rows)
    payload["merchant_carts_page_rows"] = merged
    if merged:
        payload["merchant_table_rows"] = list(merged[:8])

    payload["hot_slice_rows"] = int(hot_meta.get("hot_slice_rows") or 0)
    payload["hot_slice_ms"] = hot_meta.get("hot_slice_ms")
    payload["hot_slice_queries"] = int(hot_meta.get("hot_slice_queries") or 0)
    payload["hot_slice_degraded"] = bool(hot_meta.get("hot_slice_degraded"))
    payload["hot_slice_reason"] = hot_meta.get("hot_slice_reason") or None
    payload["data_freshness"] = "hot_merged" if hot_rows else "snapshot_only"

    log.info(
        "[DASHBOARD HOT MERGE] store_slug=%s hot_rows=%s snapshot_rows=%s "
        "merged=%s hot_ms=%s queries=%s degraded=%s",
        slug or "-",
        len(hot_rows),
        len(snapshot_rows),
        len(merged),
        hot_meta.get("hot_slice_ms"),
        hot_meta.get("hot_slice_queries"),
        str(bool(hot_meta.get("hot_slice_degraded"))).lower(),
    )
    return payload


__all__ = [
    "ENV_HOT_SLICE",
    "HOT_SLICE_HOURS",
    "HOT_SLICE_MAX_QUERIES",
    "HOT_SLICE_MAX_ROWS",
    "apply_hot_slice_to_normal_carts_payload",
    "build_hot_slice_active_rows",
    "dashboard_hot_slice_enabled",
    "hot_slice_last_seen_cutoff",
    "merge_hot_slice_active_rows",
]
