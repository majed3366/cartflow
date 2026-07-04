# -*- coding: utf-8 -*-
"""
Production snapshot enforcement — merchant dashboard API must never run live builders
when ``CARTFLOW_DASHBOARD_SNAPSHOT_MODE=1``.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Callable, Optional

log = logging.getLogger("cartflow")

DASHBOARD_SNAPSHOT_ENFORCED_PATHS: tuple[str, ...] = (
    "/api/dashboard/summary",
    "/api/dashboard/normal-carts",
    "/api/dashboard/widget-panel",
    "/api/dashboard/refresh-state",
    "/api/merchant/store-connection",
)


class DashboardSnapshotHotPathViolation(RuntimeError):
    """Live dashboard computation invoked during snapshot-mode HTTP request."""


def _env_truthy(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def dashboard_snapshot_enforcement_active() -> bool:
    """Production-like runtime with snapshot mode enabled."""
    from services.dashboard_snapshot_v1 import dashboard_snapshot_mode_enabled
    from services.recovery_scheduler_guardrails import is_production_like_runtime

    return dashboard_snapshot_mode_enabled() and is_production_like_runtime()


def should_raise_on_hot_path_violation() -> bool:
    """Raise in tests/CI when enforce flag or pytest is active."""
    from services.dashboard_snapshot_v1 import dashboard_snapshot_mode_enabled

    if not dashboard_snapshot_mode_enabled():
        return False
    explicit = (os.environ.get("CARTFLOW_DASHBOARD_SNAPSHOT_ENFORCE") or "").strip().lower()
    if explicit in ("0", "false", "no", "off"):
        return False
    if explicit in ("1", "true", "yes", "on"):
        return True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return "pytest" in sys.modules


def maybe_raise_hot_path_violation(*, operation: str, endpoint: str = "") -> None:
    if not should_raise_on_hot_path_violation():
        return
    raise DashboardSnapshotHotPathViolation(
        f"live dashboard path blocked: operation={operation} endpoint={endpoint or '-'}"
    )


def serve_enforced_snapshot_response(
    *,
    path: str,
    build_from_snapshot: Callable[..., dict[str, Any]],
    degraded_builder: Callable[..., dict[str, Any]],
    store_slug: Optional[str] = None,
) -> dict[str, Any]:
    """
    Snapshot-only HTTP payload for enforced dashboard endpoints.

    Returns degraded payload on read errors — never falls through to live builders.
    """
    from extensions import db
    from services.dashboard_snapshot_read_v1 import resolve_merchant_store_slug_for_snapshot

    slug = (store_slug or resolve_merchant_store_slug_for_snapshot()).strip()
    try:
        body = build_from_snapshot(store_slug=slug, path=path)
        return {"ok": True, **body}
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        log.warning("enforced snapshot read failed path=%s slug=%s err=%s", path, slug, exc)
        _record_snapshot_read_error_observability(path)
        degraded = degraded_builder(reason="snapshot_read_error")
        return {"ok": True, **degraded}


def _record_snapshot_read_error_observability(path: str) -> None:
    """Count the snapshot_read_error branch in the read-model observability layer.

    Defensive: observability must never mask or replace the degraded response.
    """
    try:
        from services.dashboard_read_observability_v1 import (  # noqa: PLC0415
            BRANCH_SNAPSHOT_READ_ERROR,
            record_dashboard_read_sample,
        )

        endpoint = (str(path or "").rstrip("/").rsplit("/", 1)[-1] or "unknown")[:64]
        record_dashboard_read_sample(
            endpoint=endpoint,
            branch=BRANCH_SNAPSHOT_READ_ERROR,
        )
    except Exception:  # noqa: BLE001
        pass


__all__ = [
    "DASHBOARD_SNAPSHOT_ENFORCED_PATHS",
    "DashboardSnapshotHotPathViolation",
    "dashboard_snapshot_enforcement_active",
    "maybe_raise_hot_path_violation",
    "serve_enforced_snapshot_response",
    "should_raise_on_hot_path_violation",
]
