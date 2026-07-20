# -*- coding: utf-8 -*-
"""
Product Metrics Foundation V1 — deterministic metrics from Product Signals only.

No trends, scores, decisions, or presentation. Calculation ownership lives here.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ProductMetricValue, ProductSignalEvent
from schema_product_metric_values_v1 import ensure_product_metric_values_schema
from schema_product_signal_events_v1 import ensure_product_signal_events_schema
from services.product_data.product_metrics_flag_v1 import (
    product_metrics_foundation_v1_enabled,
)
from services.product_data.product_metrics_types_v1 import (
    COMPUTATION_VERSION_V1,
    METRIC_DEFINITIONS,
    METRIC_KEY_TO_DEFINITION,
    SIGNAL_TYPE_TO_METRIC_KEY,
    STORE_GRAIN_IDENTITY,
    SUPPORTED_WINDOWS,
    WINDOW_ALL,
    WINDOW_DAY,
    WINDOW_MONTH,
    WINDOW_WEEK,
)

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _window_bounds(
    window_code: str,
    *,
    as_of: Optional[datetime] = None,
) -> tuple[Optional[datetime], Optional[datetime]]:
    code = (window_code or WINDOW_ALL).strip().lower()
    if code not in SUPPORTED_WINDOWS:
        raise ValueError(f"unsupported_window:{code}")
    if code == WINDOW_ALL:
        return None, None
    end = as_of or _utc_naive_now()
    if end.tzinfo is not None:
        end = end.astimezone(timezone.utc).replace(tzinfo=None)
    if code == WINDOW_DAY:
        start = end - timedelta(days=1)
    elif code == WINDOW_WEEK:
        start = end - timedelta(days=7)
    else:  # WINDOW_MONTH
        start = end - timedelta(days=30)
    return start, end


def _window_key(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y%m%d%H%M%S")


def _content_hash(
    *,
    store_slug: str,
    stable_identity_key: str,
    metric_key: str,
    window_code: str,
    window_start: Optional[datetime],
    window_end: Optional[datetime],
    value: int,
    source_signal_type: str,
) -> str:
    payload = {
        "v": COMPUTATION_VERSION_V1,
        "store": store_slug,
        "identity": stable_identity_key,
        "metric": metric_key,
        "window": window_code,
        "start": _window_key(window_start),
        "end": _window_key(window_end),
        "value": int(value),
        "signal": source_signal_type,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_product_metrics_v1(
    store_slug: str,
    *,
    window_code: str = WINDOW_ALL,
    as_of: Optional[datetime] = None,
    include_zero_store_metrics: bool = True,
) -> dict[str, Any]:
    """
    Deterministic in-memory metrics from product_signal_events only.

    Returns a stable, JSON-serializable report suitable for equality checks.
    """
    slug = (store_slug or "").strip()[:255]
    code = (window_code or WINDOW_ALL).strip().lower() or WINDOW_ALL
    window_start, window_end = _window_bounds(code, as_of=as_of)

    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "window_code": code,
        "window_start": window_start.isoformat(sep=" ") if window_start else None,
        "window_end": window_end.isoformat(sep=" ") if window_end else None,
        "computation_version": COMPUTATION_VERSION_V1,
        "signal_row_count": 0,
        "product_metrics": [],
        "store_metrics": [],
        "by_metric_key": {},
        "canonical_fingerprint": "",
        "errors": [],
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out

    try:
        ensure_product_signal_events_schema(db)
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"signal_schema:{type(exc).__name__}")
        return out

    q = db.session.query(
        ProductSignalEvent.stable_identity_key,
        ProductSignalEvent.signal_type,
        func.count(ProductSignalEvent.id),
    ).filter(ProductSignalEvent.store_slug == slug)
    if window_start is not None:
        q = q.filter(ProductSignalEvent.observed_at >= window_start)
    if window_end is not None:
        q = q.filter(ProductSignalEvent.observed_at < window_end)
    q = q.group_by(
        ProductSignalEvent.stable_identity_key,
        ProductSignalEvent.signal_type,
    )

    try:
        rows = q.all()
        total_signals = (
            db.session.query(func.count(ProductSignalEvent.id))
            .filter(ProductSignalEvent.store_slug == slug)
        )
        if window_start is not None:
            total_signals = total_signals.filter(
                ProductSignalEvent.observed_at >= window_start
            )
        if window_end is not None:
            total_signals = total_signals.filter(
                ProductSignalEvent.observed_at < window_end
            )
        out["signal_row_count"] = int(total_signals.scalar() or 0)
    except SQLAlchemyError as exc:
        out["errors"].append(f"query:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return out

    product_acc: dict[tuple[str, str], int] = {}
    store_acc: dict[str, int] = {d.metric_key: 0 for d in METRIC_DEFINITIONS}

    for identity, signal_type, cnt in rows:
        metric_key = SIGNAL_TYPE_TO_METRIC_KEY.get(str(signal_type or "").strip())
        if not metric_key:
            continue
        ident = str(identity or "").strip()
        n = int(cnt or 0)
        product_acc[(ident, metric_key)] = product_acc.get((ident, metric_key), 0) + n
        store_acc[metric_key] = store_acc.get(metric_key, 0) + n

    product_metrics: list[dict[str, Any]] = []
    for (ident, metric_key), value in sorted(product_acc.items()):
        if value <= 0:
            continue
        definition = METRIC_KEY_TO_DEFINITION[metric_key]
        product_metrics.append(
            {
                "store_slug": slug,
                "stable_identity_key": ident,
                "metric_key": metric_key,
                "metric_family": definition.metric_family,
                "window_code": code,
                "window_start": out["window_start"],
                "window_end": out["window_end"],
                "value": int(value),
                "source_signal_type": definition.source_signal_type,
                "computation_version": COMPUTATION_VERSION_V1,
                "content_hash": _content_hash(
                    store_slug=slug,
                    stable_identity_key=ident,
                    metric_key=metric_key,
                    window_code=code,
                    window_start=window_start,
                    window_end=window_end,
                    value=int(value),
                    source_signal_type=definition.source_signal_type,
                ),
            }
        )

    store_metrics: list[dict[str, Any]] = []
    for definition in METRIC_DEFINITIONS:
        value = int(store_acc.get(definition.metric_key, 0) or 0)
        if value <= 0 and not include_zero_store_metrics:
            continue
        store_metrics.append(
            {
                "store_slug": slug,
                "stable_identity_key": STORE_GRAIN_IDENTITY,
                "metric_key": definition.metric_key,
                "metric_family": definition.metric_family,
                "window_code": code,
                "window_start": out["window_start"],
                "window_end": out["window_end"],
                "value": value,
                "source_signal_type": definition.source_signal_type,
                "computation_version": COMPUTATION_VERSION_V1,
                "content_hash": _content_hash(
                    store_slug=slug,
                    stable_identity_key=STORE_GRAIN_IDENTITY,
                    metric_key=definition.metric_key,
                    window_code=code,
                    window_start=window_start,
                    window_end=window_end,
                    value=value,
                    source_signal_type=definition.source_signal_type,
                ),
            }
        )

    by_metric_key = {
        m["metric_key"]: int(m["value"]) for m in store_metrics if int(m["value"]) > 0
    }

    canonical = {
        "computation_version": COMPUTATION_VERSION_V1,
        "store_slug": slug,
        "window_code": code,
        "window_start": out["window_start"],
        "window_end": out["window_end"],
        "product_metrics": product_metrics,
        "store_metrics": [
            {"metric_key": m["metric_key"], "value": m["value"], "content_hash": m["content_hash"]}
            for m in store_metrics
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    out["product_metrics"] = product_metrics
    out["store_metrics"] = store_metrics
    out["by_metric_key"] = by_metric_key
    out["canonical_fingerprint"] = fingerprint
    out["ok"] = True
    return out


def materialize_product_metrics_v1(
    store_slug: str,
    *,
    window_code: str = WINDOW_ALL,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Upsert computed metrics into product_metric_values (store + product grain)."""
    if not product_metrics_foundation_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "errors": ["metrics_foundation_disabled"],
        }

    report = compute_product_metrics_v1(
        store_slug,
        window_code=window_code,
        as_of=as_of,
        include_zero_store_metrics=False,
    )
    if not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_product_metric_values_schema(db)
    code = str(report["window_code"])
    window_start, window_end = _window_bounds(code, as_of=as_of)
    start_key = _window_key(window_start)
    end_key = _window_key(window_end)
    now = _utc_naive_now()
    rows = list(report.get("product_metrics") or []) + list(
        report.get("store_metrics") or []
    )
    upserted = 0
    try:
        for item in rows:
            value = int(item.get("value") or 0)
            if value <= 0:
                continue
            identity = str(item.get("stable_identity_key") or "")
            metric_key = str(item.get("metric_key") or "")
            existing = (
                db.session.query(ProductMetricValue)
                .filter(
                    ProductMetricValue.store_slug == report["store_slug"],
                    ProductMetricValue.stable_identity_key == identity,
                    ProductMetricValue.metric_key == metric_key,
                    ProductMetricValue.window_code == code,
                    ProductMetricValue.window_start_key == start_key,
                    ProductMetricValue.window_end_key == end_key,
                )
                .first()
            )
            if existing is None:
                existing = ProductMetricValue(
                    store_slug=report["store_slug"],
                    stable_identity_key=identity,
                    metric_key=metric_key,
                    metric_family=str(item.get("metric_family") or ""),
                    window_code=code,
                    window_start=window_start,
                    window_end=window_end,
                    window_start_key=start_key,
                    window_end_key=end_key,
                    value=value,
                    source_signal_type=str(item.get("source_signal_type") or ""),
                    computation_version=COMPUTATION_VERSION_V1,
                    content_hash=str(item.get("content_hash") or ""),
                    computed_at=now,
                )
                db.session.add(existing)
            else:
                existing.metric_family = str(item.get("metric_family") or "")
                existing.window_start = window_start
                existing.window_end = window_end
                existing.value = value
                existing.source_signal_type = str(item.get("source_signal_type") or "")
                existing.computation_version = COMPUTATION_VERSION_V1
                existing.content_hash = str(item.get("content_hash") or "")
                existing.computed_at = now
            upserted += 1
        db.session.commit()
    except SQLAlchemyError as exc:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.debug("product metrics materialize failed: %s", exc)
        return {
            "ok": False,
            "upserted": 0,
            "errors": [f"materialize:{type(exc).__name__}"],
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    return {
        "ok": True,
        "upserted": upserted,
        "errors": [],
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "by_metric_key": report.get("by_metric_key") or {},
        "signal_row_count": report.get("signal_row_count") or 0,
        "store_slug": report.get("store_slug"),
        "window_code": code,
    }


def verify_metrics_determinism_v1(
    store_slug: str,
    *,
    window_code: str = WINDOW_ALL,
) -> dict[str, Any]:
    """Run compute twice; require identical canonical fingerprints."""
    a = compute_product_metrics_v1(store_slug, window_code=window_code)
    b = compute_product_metrics_v1(store_slug, window_code=window_code)
    match = bool(
        a.get("ok")
        and b.get("ok")
        and a.get("canonical_fingerprint")
        and a.get("canonical_fingerprint") == b.get("canonical_fingerprint")
    )
    return {
        "ok": match,
        "deterministic": match,
        "fingerprint_a": a.get("canonical_fingerprint") or "",
        "fingerprint_b": b.get("canonical_fingerprint") or "",
        "by_metric_key": a.get("by_metric_key") or {},
        "signal_row_count": a.get("signal_row_count") or 0,
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "compute_product_metrics_v1",
    "materialize_product_metrics_v1",
    "verify_metrics_determinism_v1",
]
