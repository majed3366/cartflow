# -*- coding: utf-8 -*-
"""
Background dashboard snapshot builder — never runs on merchant HTTP path.

Computes summary, normal-carts, and card payloads using existing live builders
in an isolated DB session, then persists to ``dashboard_snapshots``.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_DASHBOARD_CARDS,
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_REFRESH_STATE,
    SNAPSHOT_TYPE_STORE_CONNECTION,
    SNAPSHOT_TYPE_SUMMARY,
    SNAPSHOT_TYPE_WIDGET_PANEL,
    STATUS_FAILED,
    list_store_slugs_for_snapshot_build,
    upsert_dashboard_snapshot,
)
from services.db_pool_pressure_v1 import evaluate_db_pool_pressure, LEVEL_HIGH, LEVEL_CRITICAL
from services.db_session_lifecycle import scoped_db_session_begin, release_scoped_db_session

log = logging.getLogger("cartflow")

_BUILDER_SOURCE = "dashboard_snapshot_builder_v1"


def _env_truthy(name: str, *, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def dashboard_snapshot_builder_enabled() -> bool:
    if not _env_truthy("CARTFLOW_DASHBOARD_SNAPSHOT_MODE"):
        return False
    if _env_truthy("CARTFLOW_DASHBOARD_SNAPSHOT_BUILDER_ENABLED"):
        return True
    try:
        from services.recovery_process_role_v1 import resolve_process_role

        return resolve_process_role() == "scheduler"
    except Exception:  # noqa: BLE001
        return False


def builder_should_skip_due_to_pool_pressure() -> tuple[bool, str]:
    pressure = evaluate_db_pool_pressure()
    level = str(pressure.get("pressure_level") or "")
    if level in (LEVEL_HIGH, LEVEL_CRITICAL):
        return True, f"pool_pressure_{level}"
    if pressure.get("circuit_breaker_open"):
        return True, "pool_circuit_breaker"
    return False, ""


def snapshot_build_store_limit() -> int:
    raw = (os.environ.get("CARTFLOW_DASHBOARD_SNAPSHOT_STORES_PER_TICK") or "5").strip()
    try:
        return max(1, min(50, int(raw)))
    except (TypeError, ValueError):
        return 5


def _resolve_store_row(store_id: int, store_slug: str) -> Optional[Any]:
    from extensions import db
    from models import Store

    row = db.session.get(Store, int(store_id))
    if row is not None:
        return row
    return (
        db.session.query(Store)
        .filter(Store.zid_store_id == store_slug)
        .first()
    )


def _build_summary_payload(dash_store: Any) -> dict[str, Any]:
    from main import _api_json_dashboard_summary  # noqa: PLC0415

    return dict(_api_json_dashboard_summary(dash_store, cookies=None))


def _build_normal_carts_payload(dash_store: Any) -> dict[str, Any]:
    from services.normal_carts_dashboard_batch_v1 import (  # noqa: PLC0415
        build_normal_carts_dashboard_api_payload,
    )

    body, _prof, _perf = build_normal_carts_dashboard_api_payload(
        dash_store,
        page_limit=50,
        page_offset=0,
        debug_perf=False,
    )
    return dict(body)


def _extract_dashboard_cards(summary_body: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "whatsapp_readiness_card",
        "merchant_setup_experience",
        "merchant_activation",
        "store_connection_status",
        "month_window",
        "kpis",
        "normal_carts_stats",
        "merchant_reason_rows",
        "merchant_reason_rows_month",
    )
    return {k: summary_body.get(k) for k in keys if k in summary_body}


def build_store_dashboard_snapshots(
    *,
    store_id: int,
    store_slug: str,
) -> dict[str, Any]:
    """
    Build all snapshot types for one store. Caller must hold a clean DB session.
    """
    from extensions import db

    t0 = time.perf_counter()
    dash_store = _resolve_store_row(store_id, store_slug)
    if dash_store is None:
        return {"ok": False, "reason": "store_not_found", "store_slug": store_slug}

    sid = int(getattr(dash_store, "id", store_id) or store_id)
    slug = (getattr(dash_store, "zid_store_id", None) or store_slug or "").strip()

    results: dict[str, Any] = {"store_slug": slug, "types": {}, "duration_ms": 0.0}

    try:
        summary_body = _build_summary_payload(dash_store)
        upsert_dashboard_snapshot(
            store_id=sid,
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload=summary_body,
        )
        results["types"][SNAPSHOT_TYPE_SUMMARY] = "ok"

        cards = _extract_dashboard_cards(summary_body)
        upsert_dashboard_snapshot(
            store_id=sid,
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_DASHBOARD_CARDS,
            payload=cards,
        )
        results["types"][SNAPSHOT_TYPE_DASHBOARD_CARDS] = "ok"

        nc_body = _build_normal_carts_payload(dash_store)
        upsert_dashboard_snapshot(
            store_id=sid,
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload=nc_body,
        )
        results["types"][SNAPSHOT_TYPE_NORMAL_CARTS] = "ok"

        from main import _merchant_dashboard_refresh_state_payload  # noqa: PLC0415

        refresh_body = dict(_merchant_dashboard_refresh_state_payload(dash_store))
        upsert_dashboard_snapshot(
            store_id=sid,
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_REFRESH_STATE,
            payload=refresh_body,
        )
        results["types"][SNAPSHOT_TYPE_REFRESH_STATE] = "ok"

        from main import _api_json_dashboard_widget_panel  # noqa: PLC0415

        widget_body = dict(_api_json_dashboard_widget_panel(dash_store))
        upsert_dashboard_snapshot(
            store_id=sid,
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_WIDGET_PANEL,
            payload=widget_body,
        )
        results["types"][SNAPSHOT_TYPE_WIDGET_PANEL] = "ok"

        from services.merchant_store_connection_v1 import (  # noqa: PLC0415
            build_merchant_store_connection_status_for_store,
        )

        conn_status = build_merchant_store_connection_status_for_store(dash_store)
        upsert_dashboard_snapshot(
            store_id=sid,
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_STORE_CONNECTION,
            payload={"store_connection": conn_status.to_api_dict()},
        )
        results["types"][SNAPSHOT_TYPE_STORE_CONNECTION] = "ok"

        results["ok"] = True
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        log.warning(
            "[%s] build failed store_slug=%s err=%s",
            _BUILDER_SOURCE,
            slug,
            exc,
            exc_info=True,
        )
        try:
            upsert_dashboard_snapshot(
                store_id=sid,
                store_slug=slug,
                snapshot_type=SNAPSHOT_TYPE_SUMMARY,
                payload={"build_error": str(exc)[:200]},
                status=STATUS_FAILED,
            )
        except Exception:  # noqa: BLE001
            db.session.rollback()
        results["ok"] = False
        results["error"] = str(exc)[:200]

    results["duration_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
    return results


def run_dashboard_snapshot_builder_tick() -> dict[str, Any]:
    """One bounded builder pass across active stores."""
    skip, reason = builder_should_skip_due_to_pool_pressure()
    if skip:
        print(
            f"[DASHBOARD SNAPSHOT BUILDER SKIP] reason={reason}",
            flush=True,
        )
        return {"skipped": True, "reason": reason, "stores_built": 0}

    scoped_db_session_begin()
    try:
        stores = list_store_slugs_for_snapshot_build(limit=snapshot_build_store_limit())
        built = 0
        errors = 0
        for store_id, store_slug in stores:
            out = build_store_dashboard_snapshots(
                store_id=store_id,
                store_slug=store_slug,
            )
            if out.get("ok"):
                built += 1
            else:
                errors += 1
        print(
            f"[DASHBOARD SNAPSHOT BUILDER TICK] stores={len(stores)} "
            f"built={built} errors={errors}",
            flush=True,
        )
        return {
            "skipped": False,
            "stores_seen": len(stores),
            "stores_built": built,
            "errors": errors,
        }
    finally:
        release_scoped_db_session()


__all__ = [
    "build_store_dashboard_snapshots",
    "builder_should_skip_due_to_pool_pressure",
    "dashboard_snapshot_builder_enabled",
    "run_dashboard_snapshot_builder_tick",
    "snapshot_build_store_limit",
]
