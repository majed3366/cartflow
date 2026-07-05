# -*- coding: utf-8 -*-
"""
Read-only dashboard API responses from ``dashboard_snapshots`` (P0 hot path elimination).

Target: 200ms typical, 500ms hard max — return degraded/stale, never hang.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from services.dashboard_snapshot_hot_path_guard_v1 import (
    dashboard_api_snapshot_request_scope,
)
from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_STORE_CONNECTION,
    SNAPSHOT_TYPE_SUMMARY,
    SNAPSHOT_TYPE_WIDGET_PANEL,
    canonical_snapshot_store_slug,
    decode_snapshot_payload,
    emit_dashboard_degraded,
    emit_snapshot_miss,
    emit_snapshot_read,
    fetch_latest_snapshot_row,
    snapshot_row_is_stale,
)

log = logging.getLogger("cartflow")

DASHBOARD_ROUTE_TARGET_MS = 200.0
DASHBOARD_ROUTE_MAX_MS = 500.0


def _route_budget_ms() -> float:
    import os

    raw = (os.environ.get("CARTFLOW_DASHBOARD_ROUTE_MAX_MS") or "").strip()
    if raw:
        try:
            return max(50.0, min(2000.0, float(raw)))
        except (TypeError, ValueError):
            pass
    return DASHBOARD_ROUTE_MAX_MS


def _snapshot_meta(
    *,
    row: Any,
    stale: bool,
    read_ms: float,
    degraded: bool = False,
    reason: str = "",
) -> dict[str, Any]:
    gen = getattr(row, "generated_at", None)
    exp = getattr(row, "expires_at", None)
    return {
        "_snapshot": {
            "generated_at": gen.isoformat() if isinstance(gen, datetime) else None,
            "expires_at": exp.isoformat() if isinstance(exp, datetime) else None,
            "version": int(getattr(row, "version", 0) or 0),
            "status": str(getattr(row, "status", "") or ""),
            "stale": bool(stale),
            "degraded": bool(degraded),
            "read_ms": round(float(read_ms), 1),
            "reason": (reason or "")[:128] or None,
        }
    }


def _degraded_summary_payload(*, reason: str) -> dict[str, Any]:
    return {
        "snapshot_mode": True,
        "snapshot_degraded": True,
        "snapshot_reason": reason,
        "kpis": {
            "abandoned_today": 0,
            "recovered_today": 0,
            "whatsapp_sent_today": 0,
            "recovered_revenue_today": 0.0,
        },
        "month_window": {
            "abandoned_total": 0,
            "recovered_total": 0,
            "recovery_pct": 0.0,
            "recovered_revenue": 0.0,
        },
        "normal_carts_stats": {
            "normal_cart_count": 0,
            "messages_sent_count": 0,
            "normal_recovered_count": 0,
            "stopped_flow_count": 0,
        },
        "merchant_nav_badge_abandoned": 0,
        "merchant_table_rows": [],
        "merchant_reason_rows": [],
        "merchant_reason_rows_month": [],
        "whatsapp_readiness_card": {},
        "merchant_setup_experience": {},
        "merchant_activation": {},
        "store_connection_status": {},
    }


def _degraded_normal_carts_payload(*, reason: str) -> dict[str, Any]:
    stage = (reason or "snapshot_degraded")[:64]
    return {
        "snapshot_mode": True,
        "snapshot_degraded": True,
        "snapshot_reason": reason,
        "dashboard_partial": True,
        "dashboard_timeout": True,
        "dashboard_timeout_stage": stage,
        "merchant_table_rows": [],
        "merchant_carts_page_rows": [],
        "merchant_archived_carts_page_rows": [],
        "merchant_archived_cart_count": 0,
        "merchant_cart_filter_counts": {},
        "merchant_nav_badge_abandoned": 0,
        "merchant_dashboard_refresh_token": "",
        "merchant_dashboard_refresh_last_log_id": 0,
        "merchant_dashboard_refresh_last_sent_log_id": 0,
        "merchant_dashboard_refresh_sent_total": 0,
        "merchant_dashboard_refresh_archive_rev": 0,
        "_perf": {
            "query_count": 1,
            "duration_ms": 0,
            "candidate_rows": 0,
            "visible_rows": 0,
            "partial": True,
            "degraded": True,
            "timeout_stage": stage,
        },
    }


def apply_normal_carts_snapshot_client_guards(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Empty snapshot/degraded normal-carts payloads must expose live-style partial flags
    so merchant_dashboard_lazy.js retains prior rows.
    """
    if payload.get("merchant_carts_page_rows"):
        return payload
    snap = payload.get("_snapshot") if isinstance(payload.get("_snapshot"), dict) else {}
    perf = payload.get("_perf") if isinstance(payload.get("_perf"), dict) else {}
    degraded = bool(
        payload.get("snapshot_degraded")
        or payload.get("snapshot_stale")
        or snap.get("degraded")
        or snap.get("stale")
        or perf.get("degraded")
        or perf.get("partial")
    )
    if not degraded:
        return payload
    stage = str(
        payload.get("dashboard_timeout_stage")
        or payload.get("snapshot_reason")
        or perf.get("timeout_stage")
        or "snapshot_degraded"
    )[:64]
    payload.setdefault("dashboard_partial", True)
    payload.setdefault("dashboard_timeout", True)
    payload["dashboard_timeout_stage"] = stage
    return payload


def read_dashboard_snapshot_payload(
    *,
    store_slug: str,
    snapshot_type: str,
    degraded_builder: Any,
    t0: Optional[float] = None,
    endpoint: str = "",
) -> dict[str, Any]:
    """
    Single indexed read from ``dashboard_snapshots``.

    Returns payload dict with ``_snapshot`` metadata. Never scans cart/history tables.
    """
    wall0 = t0 if t0 is not None else time.perf_counter()
    slug = canonical_snapshot_store_slug(store_slug=store_slug)
    stype = (snapshot_type or "").strip()

    if not slug:
        emit_dashboard_degraded(
            store_slug="-", snapshot_type=stype, reason="missing_store_slug"
        )
        body = degraded_builder(reason="missing_store_slug")
        body["_snapshot"] = {
            "degraded": True,
            "stale": False,
            "reason": "missing_store_slug",
            "read_ms": round((time.perf_counter() - wall0) * 1000.0, 1),
        }
        return body

    row = fetch_latest_snapshot_row(store_slug=slug, snapshot_type=stype)
    read_ms = (time.perf_counter() - wall0) * 1000.0

    if row is None:
        emit_snapshot_miss(store_slug=slug, snapshot_type=stype)
        emit_dashboard_degraded(
            store_slug=slug, snapshot_type=stype, reason="no_snapshot"
        )
        body = degraded_builder(reason="no_snapshot")
        body.update(
            _snapshot_meta(
                row=type("R", (), {"version": 0, "status": "miss"})(),
                stale=False,
                read_ms=read_ms,
                degraded=True,
                reason="no_snapshot",
            )
        )
        return body

    stale = snapshot_row_is_stale(row)
    payload = decode_snapshot_payload(row)
    payload.setdefault("snapshot_mode", True)
    payload["snapshot_stale"] = stale
    payload.update(_snapshot_meta(row=row, stale=stale, read_ms=read_ms))
    emit_snapshot_read(
        store_slug=slug,
        snapshot_type=stype,
        stale=stale,
        version=int(row.version or 0),
        read_ms=read_ms,
        endpoint=endpoint or stype,
    )
    if stale:
        payload["snapshot_degraded"] = True
        payload.setdefault("snapshot_reason", "stale_snapshot")
    return payload


def enforce_route_budget(
    payload: dict[str, Any], *, wall0: float, endpoint: str = ""
) -> dict[str, Any]:
    elapsed_ms = (time.perf_counter() - wall0) * 1000.0
    max_ms = _route_budget_ms()
    snap = dict(payload.get("_snapshot") or {})
    snap["route_ms"] = round(elapsed_ms, 1)
    if elapsed_ms > max_ms:
        snap["budget_exceeded"] = True
        payload["snapshot_degraded"] = True
        payload["snapshot_reason"] = "route_budget_exceeded"
        emit_dashboard_degraded(
            store_slug=str(payload.get("store_slug") or "-"),
            snapshot_type=str(snap.get("type") or "-"),
            reason=f"route_budget_exceeded_{round(elapsed_ms)}ms",
        )
    payload["_snapshot"] = snap
    _record_read_observability(payload, endpoint=endpoint, route_ms=elapsed_ms, snap=snap)
    return payload


def _record_read_observability(
    payload: dict[str, Any],
    *,
    endpoint: str,
    route_ms: float,
    snap: dict[str, Any],
) -> None:
    """
    Feed one production read-path observation into the read-model observability
    layer (Dashboard Read Model Observability V1 — I1/I2/I5). Fully defensive:
    observability must never change or break a dashboard response.
    """
    try:
        from services.dashboard_read_observability_v1 import (  # noqa: PLC0415
            classify_read_branch,
            classify_read_path,
            record_dashboard_read_sample,
        )

        record_dashboard_read_sample(
            endpoint=endpoint or "",
            route_ms=route_ms,
            snapshot_read_ms=snap.get("read_ms"),
            read_path=classify_read_path(endpoint or ""),
            branch=classify_read_branch(snap),
            hot_slice_ms=payload.get("hot_slice_ms"),
            hot_slice_queries=payload.get("hot_slice_queries"),
            hot_slice_degraded=bool(payload.get("hot_slice_degraded")),
            hot_slice_reason=str(payload.get("hot_slice_reason") or ""),
            data_freshness=payload.get("data_freshness"),
        )
    except Exception:  # noqa: BLE001
        pass


def _degraded_widget_panel_payload(*, reason: str) -> dict[str, Any]:
    return {
        "snapshot_mode": True,
        "snapshot_degraded": True,
        "snapshot_reason": reason,
        "merchant_widget_panel": {},
        "merchant_widget_title_ar": "مساعد المتجر",
        "merchant_widget_question_ar": "ما الذي منعك من إكمال الطلب؟",
        "merchant_widget_reason_rows": [],
        "merchant_widget_installed": False,
    }


def _degraded_store_connection_payload(*, reason: str) -> dict[str, Any]:
    return {
        "snapshot_mode": True,
        "snapshot_degraded": True,
        "snapshot_reason": reason,
        "store_connection": {
            "connected": False,
            "status_label_ar": "—",
            "status_description_ar": "",
            "store_name": "",
            "platform_ar": "—",
            "connected_at_ar": "—",
            "zid_connect_available": False,
            "zid_connect_url": "/api/merchant/store-connection/zid/connect",
            "salla_connect_available": False,
            "shopify_note_ar": "Shopify قريباً",
            "pending_setup_message_ar": "",
            "store_connected_ok": False,
            "widget_installed_ok": False,
        },
    }


def build_summary_from_snapshot(
    *,
    store_slug: str,
    path: str = "/api/dashboard/summary",
) -> dict[str, Any]:
    from services.merchant_home_experience_activation_v1 import (  # noqa: PLC0415
        TRANSPORT_DEGRADED,
        TRANSPORT_SNAPSHOT,
        finalize_dashboard_summary_payload,
    )

    wall0 = time.perf_counter()
    with dashboard_api_snapshot_request_scope(path=path):
        body = read_dashboard_snapshot_payload(
            store_slug=store_slug,
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            degraded_builder=_degraded_summary_payload,
            t0=wall0,
            endpoint="summary",
        )
        source = TRANSPORT_DEGRADED if body.get("snapshot_degraded") else TRANSPORT_SNAPSHOT
        body = finalize_dashboard_summary_payload(
            body,
            summary_source=source,
            store_slug=store_slug,
        )
        return enforce_route_budget(body, wall0=wall0, endpoint="summary")


def build_normal_carts_from_snapshot(
    *,
    store_slug: str,
    path: str = "/api/dashboard/normal-carts",
) -> dict[str, Any]:
    wall0 = time.perf_counter()
    with dashboard_api_snapshot_request_scope(path=path):
        body = read_dashboard_snapshot_payload(
            store_slug=store_slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            degraded_builder=_degraded_normal_carts_payload,
            t0=wall0,
            endpoint="normal-carts",
        )
        body = apply_normal_carts_snapshot_client_guards(body)
        slug = canonical_snapshot_store_slug(store_slug=store_slug)
        try:
            from services.dashboard_hot_slice_v1 import (  # noqa: PLC0415
                apply_hot_slice_to_normal_carts_payload,
            )

            body = apply_hot_slice_to_normal_carts_payload(body, store_slug=slug)
        except Exception as exc:  # noqa: BLE001
            import logging

            logging.getLogger("cartflow").warning(
                "dashboard hot slice merge skipped: %s", exc
            )
        try:
            from services.customer_movement_visibility_v1 import (  # noqa: PLC0415
                enrich_normal_carts_payload_customer_movement_v1,
            )

            body = enrich_normal_carts_payload_customer_movement_v1(body)
        except Exception as exc:  # noqa: BLE001
            log.warning("customer movement visibility enrich skipped: %s", exc)
        try:
            from services.dashboard_counter_totals_v1 import (  # noqa: PLC0415
                apply_counter_health_from_snapshot_meta,
                emit_counter_page_audit_logs,
                visible_page_counts_from_rows,
            )
            from services.normal_carts_dashboard_batch_v1 import (  # noqa: PLC0415
                emit_counter_row_audit_logs,
            )

            snap_meta = body.get("_snapshot") if isinstance(body.get("_snapshot"), dict) else {}
            body = apply_counter_health_from_snapshot_meta(body, snapshot_meta=snap_meta)
            active_rows = list(body.get("merchant_carts_page_rows") or [])
            archived_rows = list(body.get("merchant_archived_carts_page_rows") or [])
            page_counts = visible_page_counts_from_rows(
                active_rows,
                archived_rows=archived_rows,
            )
            if "merchant_visible_page_counts" not in body:
                body["merchant_visible_page_counts"] = page_counts
            store_counts = dict(body.get("merchant_store_cart_counts") or {})
            merchant = str(store_slug or "")[:64] or "-"
            emit_counter_page_audit_logs(
                merchant=merchant,
                visible_page_counts=page_counts,
                visible_page_rows=len(active_rows),
            )
            emit_counter_row_audit_logs(
                active_rows=active_rows,
                archived_rows=archived_rows,
                store_counts=store_counts,
                page_counts=page_counts,
                source="snapshot",
                page_limit=50,
            )
        except Exception:  # noqa: BLE001
            pass
        return enforce_route_budget(body, wall0=wall0, endpoint="normal-carts")


def resolve_merchant_store_slug_for_snapshot() -> str:
    from services.dashboard_snapshot_v1 import (
        resolve_merchant_store_slug_for_snapshot as _resolve,
    )

    return _resolve()


def _degraded_refresh_state_payload(*, reason: str) -> dict[str, Any]:
    return {
        "snapshot_mode": True,
        "snapshot_degraded": True,
        "snapshot_reason": reason,
        "merchant_dashboard_refresh_token": "",
        "merchant_dashboard_refresh_last_log_id": 0,
        "merchant_dashboard_refresh_last_sent_log_id": 0,
        "merchant_dashboard_refresh_sent_total": 0,
        "merchant_dashboard_refresh_archive_rev": 0,
    }


def build_refresh_state_from_snapshot(
    *,
    store_slug: str,
    path: str = "/api/dashboard/refresh-state",
) -> dict[str, Any]:
    from services.dashboard_snapshot_v1 import SNAPSHOT_TYPE_REFRESH_STATE

    wall0 = time.perf_counter()
    with dashboard_api_snapshot_request_scope(path=path):
        body = read_dashboard_snapshot_payload(
            store_slug=store_slug,
            snapshot_type=SNAPSHOT_TYPE_REFRESH_STATE,
            degraded_builder=_degraded_refresh_state_payload,
            t0=wall0,
            endpoint="refresh-state",
        )
        return enforce_route_budget(body, wall0=wall0, endpoint="refresh-state")


def build_widget_panel_from_snapshot(
    *,
    store_slug: str,
    path: str = "/api/dashboard/widget-panel",
) -> dict[str, Any]:
    wall0 = time.perf_counter()
    with dashboard_api_snapshot_request_scope(path=path):
        body = read_dashboard_snapshot_payload(
            store_slug=store_slug,
            snapshot_type=SNAPSHOT_TYPE_WIDGET_PANEL,
            degraded_builder=_degraded_widget_panel_payload,
            t0=wall0,
            endpoint="widget-panel",
        )
        return enforce_route_budget(body, wall0=wall0, endpoint="widget-panel")


def build_store_connection_from_snapshot(
    *,
    store_slug: str,
    path: str = "/api/merchant/store-connection",
) -> dict[str, Any]:
    wall0 = time.perf_counter()
    with dashboard_api_snapshot_request_scope(path=path):
        body = read_dashboard_snapshot_payload(
            store_slug=store_slug,
            snapshot_type=SNAPSHOT_TYPE_STORE_CONNECTION,
            degraded_builder=_degraded_store_connection_payload,
            t0=wall0,
            endpoint="store-connection",
        )
        return enforce_route_budget(body, wall0=wall0, endpoint="store-connection")


__all__ = [
    "DASHBOARD_ROUTE_MAX_MS",
    "DASHBOARD_ROUTE_TARGET_MS",
    "_degraded_refresh_state_payload",
    "apply_normal_carts_snapshot_client_guards",
    "build_normal_carts_from_snapshot",
    "build_refresh_state_from_snapshot",
    "build_store_connection_from_snapshot",
    "build_summary_from_snapshot",
    "build_widget_panel_from_snapshot",
    "enforce_route_budget",
    "read_dashboard_snapshot_payload",
    "resolve_merchant_store_slug_for_snapshot",
]
