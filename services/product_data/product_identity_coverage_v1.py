# -*- coding: utf-8 -*-
"""
Product Identity coverage v1 — read-only lines[] capture diagnostics.

Distinguishes empty foundation due to merchant inactivity vs identity capture
gaps. Diagnostic only — no widget or persistence changes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from models import AbandonedCart, CartLineSnapshot
from schema_cart_line_snapshots_v1 import ensure_cart_line_snapshots_schema
from services.product_data.product_data_types_v1 import (
    DEFAULT_HEALTH_THRESHOLDS,
    ProductDataHealthThresholds,
)
from services.recovery_product_context import line_items_from_abandoned_cart

IDENTITY_STATUS_NO_ACTIVITY = "no_activity"
IDENTITY_STATUS_OK = "ok"
IDENTITY_STATUS_PARTIAL = "partial"
IDENTITY_STATUS_FAILING = "failing"

IDENTITY_STATUS_VALUES = frozenset(
    {
        IDENTITY_STATUS_NO_ACTIVITY,
        IDENTITY_STATUS_OK,
        IDENTITY_STATUS_PARTIAL,
        IDENTITY_STATUS_FAILING,
    }
)


@dataclass
class IdentityCoverageMetrics:
    """Read-only Product Identity capture diagnostics for one store."""

    cart_sample_size: int = 0
    carts_with_lines: int = 0
    carts_without_lines: int = 0
    lines_capture_rate: float = 0.0
    payload_lines_capture_rate: float = 0.0
    foundation_snapshot_capture_rate: float = 0.0
    identity_capture_status: str = IDENTITY_STATUS_NO_ACTIVITY
    carts_with_payload_lines: int = 0
    carts_with_foundation_snapshots: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cart_sample_size": self.cart_sample_size,
            "carts_with_lines": self.carts_with_lines,
            "carts_without_lines": self.carts_without_lines,
            "lines_capture_rate": round(self.lines_capture_rate, 4),
            "payload_lines_capture_rate": round(self.payload_lines_capture_rate, 4),
            "foundation_snapshot_capture_rate": round(
                self.foundation_snapshot_capture_rate, 4
            ),
            "identity_capture_status": self.identity_capture_status,
            "carts_with_payload_lines": self.carts_with_payload_lines,
            "carts_with_foundation_snapshots": self.carts_with_foundation_snapshots,
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _window_start(*, window_days: int, now: Optional[datetime] = None) -> datetime:
    end = _naive(now or _utc_now())
    return end - timedelta(days=max(1, int(window_days)))


def _coverage_ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return float(count) / float(total)


def _payload_scope(ac: AbandonedCart) -> dict[str, Any]:
    raw = getattr(ac, "raw_payload", None)
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    inner = data.get("data")
    if isinstance(inner, dict):
        return inner
    return data


def _payload_has_widget_lines(ac: AbandonedCart) -> bool:
    scope = _payload_scope(ac)
    lines = scope.get("lines")
    if not isinstance(lines, list) or not lines:
        return False
    for line in lines:
        if not isinstance(line, dict):
            continue
        if any(
            str(line.get(k) or "").strip()
            for k in ("product_id", "variant_id", "sku", "name", "title")
        ):
            return True
    return False


def _payload_has_line_items(ac: AbandonedCart) -> bool:
    return bool(line_items_from_abandoned_cart(ac))


def _payload_has_lines(ac: AbandonedCart) -> bool:
    return _payload_has_widget_lines(ac) or _payload_has_line_items(ac)


def _cart_session_id(ac: AbandonedCart) -> str:
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    if sid:
        return sid[:512]
    scope = _payload_scope(ac)
    for key in ("session_id", "recovery_session_id"):
        val = str(scope.get(key) or "").strip()
        if val:
            return val[:512]
    return ""


def _cart_id(ac: AbandonedCart) -> str:
    cid = (getattr(ac, "zid_cart_id", None) or "").strip()
    if cid:
        return cid[:255]
    scope = _payload_scope(ac)
    for key in ("cart_id", "zid_cart_id"):
        val = str(scope.get(key) or "").strip()
        if val:
            return val[:255]
    return ""


def _classify_identity_status(
    *,
    cart_sample_size: int,
    foundation_snapshot_capture_rate: float,
    payload_lines_capture_rate: float,
    thresholds: ProductDataHealthThresholds,
) -> str:
    if cart_sample_size <= 0:
        return IDENTITY_STATUS_NO_ACTIVITY
    if foundation_snapshot_capture_rate >= thresholds.ready_min_coverage:
        return IDENTITY_STATUS_OK
    if foundation_snapshot_capture_rate >= thresholds.partial_min_coverage:
        return IDENTITY_STATUS_PARTIAL
    if payload_lines_capture_rate > 0.0 and foundation_snapshot_capture_rate == 0.0:
        return IDENTITY_STATUS_FAILING
    if payload_lines_capture_rate == 0.0 and foundation_snapshot_capture_rate == 0.0:
        return IDENTITY_STATUS_FAILING
    return IDENTITY_STATUS_PARTIAL


def assess_identity_coverage(
    db_session: Any,
    store_slug: str,
    carts: list[AbandonedCart],
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
    thresholds: ProductDataHealthThresholds = DEFAULT_HEALTH_THRESHOLDS,
) -> IdentityCoverageMetrics:
    """Read-only identity capture diagnostics for carts in the health window."""
    slug = (store_slug or "").strip()[:255]
    metrics = IdentityCoverageMetrics()
    metrics.cart_sample_size = len(carts)
    if not slug or not carts:
        return metrics

    start = _window_start(window_days=window_days, now=now)

    try:
        ensure_cart_line_snapshots_schema(db_session)
    except Exception:  # noqa: BLE001
        pass

    snapshot_sessions: set[str] = set()
    snapshot_cart_ids: set[str] = set()
    try:
        snap_rows = (
            db_session.query(CartLineSnapshot.session_id, CartLineSnapshot.cart_id)
            .filter(
                CartLineSnapshot.store_slug == slug,
                CartLineSnapshot.captured_at >= start,
            )
            .all()
        )
        for sid, cid in snap_rows:
            if sid:
                snapshot_sessions.add(str(sid).strip())
            if cid:
                snapshot_cart_ids.add(str(cid).strip())
    except SQLAlchemyError:
        db_session.rollback()

    payload_lines_n = 0
    snapshot_n = 0
    any_lines_n = 0

    for ac in carts:
        has_payload_lines = _payload_has_lines(ac)
        session_id = _cart_session_id(ac)
        cart_id = _cart_id(ac)
        has_snapshot = bool(
            (session_id and session_id in snapshot_sessions)
            or (cart_id and cart_id in snapshot_cart_ids)
        )

        if has_payload_lines:
            payload_lines_n += 1
            any_lines_n += 1
        elif has_snapshot:
            any_lines_n += 1
        if has_snapshot:
            snapshot_n += 1

    metrics.carts_with_payload_lines = payload_lines_n
    metrics.carts_with_foundation_snapshots = snapshot_n
    metrics.carts_with_lines = any_lines_n
    metrics.carts_without_lines = max(0, metrics.cart_sample_size - any_lines_n)
    metrics.payload_lines_capture_rate = _coverage_ratio(
        payload_lines_n, metrics.cart_sample_size
    )
    metrics.foundation_snapshot_capture_rate = _coverage_ratio(
        snapshot_n, metrics.cart_sample_size
    )
    metrics.lines_capture_rate = metrics.foundation_snapshot_capture_rate
    metrics.identity_capture_status = _classify_identity_status(
        cart_sample_size=metrics.cart_sample_size,
        foundation_snapshot_capture_rate=metrics.foundation_snapshot_capture_rate,
        payload_lines_capture_rate=metrics.payload_lines_capture_rate,
        thresholds=thresholds,
    )
    return metrics


__all__ = [
    "IDENTITY_STATUS_FAILING",
    "IDENTITY_STATUS_NO_ACTIVITY",
    "IDENTITY_STATUS_OK",
    "IDENTITY_STATUS_PARTIAL",
    "IDENTITY_STATUS_VALUES",
    "IdentityCoverageMetrics",
    "assess_identity_coverage",
]
