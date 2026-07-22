# -*- coding: utf-8 -*-
"""
Product Trends Foundation V1 — temporal change from Product Metrics only.

No why, ranking, health, guidance, or signal/provider reads.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ProductTrendValue
from schema_product_trend_values_v1 import ensure_product_trend_values_schema
from services.product_data.product_metrics_foundation_v1 import (
    compute_product_metrics_v1,
)
from services.product_data.product_metrics_types_v1 import (
    METRIC_KEY_TO_DEFINITION,
    STORE_GRAIN_IDENTITY,
)
from services.product_data.product_trends_flag_v1 import (
    product_trends_foundation_v1_enabled,
)
from services.product_data.product_trends_types_v1 import (
    COMPUTATION_VERSION_V1,
    SUPPORTED_TREND_WINDOWS,
    TREND_WINDOW_D7,
    TREND_WINDOW_SPECS,
    classify_trend_direction,
)
from services.product_data.time_authority_binding_resolve_v1 import resolve_bound_as_of_v1

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _floor_second(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def _as_of_key(dt: datetime) -> str:
    return _floor_second(dt).strftime("%Y%m%d%H%M%S")


def _content_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _metric_maps(
    report: dict[str, Any],
) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    store_map: dict[str, int] = {}
    for row in report.get("store_metrics") or []:
        key = str(row.get("metric_key") or "")
        if key:
            store_map[key] = int(row.get("value") or 0)
    product_map: dict[tuple[str, str], int] = {}
    for row in report.get("product_metrics") or []:
        identity = str(row.get("stable_identity_key") or "")
        key = str(row.get("metric_key") or "")
        if key:
            product_map[(identity, key)] = int(row.get("value") or 0)
    return store_map, product_map


def _build_trend_row(
    *,
    store_slug: str,
    stable_identity_key: str,
    metric_key: str,
    trend_window: str,
    as_of: datetime,
    current_value: int,
    previous_value: int,
) -> dict[str, Any]:
    definition = METRIC_KEY_TO_DEFINITION.get(metric_key)
    family = definition.metric_family if definition else ""
    direction = classify_trend_direction(previous_value, current_value)
    delta = int(current_value) - int(previous_value)
    factual = {
        "v": COMPUTATION_VERSION_V1,
        "store": store_slug,
        "identity": stable_identity_key,
        "metric": metric_key,
        "window": trend_window,
        "as_of": _as_of_key(as_of),
        "current": int(current_value),
        "previous": int(previous_value),
        "delta": delta,
        "direction": direction,
    }
    return {
        "store_slug": store_slug,
        "stable_identity_key": stable_identity_key,
        "metric_key": metric_key,
        "metric_family": family,
        "trend_window": trend_window,
        "as_of": as_of.isoformat(sep=" "),
        "current_value": int(current_value),
        "previous_value": int(previous_value),
        "delta_abs": delta,
        "trend_direction": direction,
        "computation_version": COMPUTATION_VERSION_V1,
        "content_hash": _content_hash(factual),
    }


def compute_product_trends_v1(
    store_slug: str,
    *,
    trend_window: str = TREND_WINDOW_D7,
    as_of: Optional[datetime] = None,
    include_stable_zeros: bool = False,
) -> dict[str, Any]:
    """
    Deterministic trends from Product Metrics Foundation only.

    Compares current vs previous equal-length metric windows.
    """
    slug = (store_slug or "").strip()[:255]
    window = (trend_window or TREND_WINDOW_D7).strip().lower()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "trend_window": window,
        "as_of": None,
        "computation_version": COMPUTATION_VERSION_V1,
        "store_trends": [],
        "product_trends": [],
        "by_direction": {},
        "canonical_fingerprint": "",
        "errors": [],
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if window not in SUPPORTED_TREND_WINDOWS:
        out["errors"].append(f"unsupported_trend_window:{window}")
        return out

    spec = TREND_WINDOW_SPECS[window]
    anchor = resolve_bound_as_of_v1(as_of)
    prev_anchor = anchor - timedelta(days=spec.length_days)
    out["as_of"] = anchor.isoformat(sep=" ")

    current = compute_product_metrics_v1(
        slug,
        window_code=spec.metric_window_code,
        as_of=anchor,
        include_zero_store_metrics=True,
    )
    previous = compute_product_metrics_v1(
        slug,
        window_code=spec.metric_window_code,
        as_of=prev_anchor,
        include_zero_store_metrics=True,
    )
    if not current.get("ok"):
        out["errors"].extend(
            [f"metrics_current:{e}" for e in (current.get("errors") or ["failed"])]
        )
        return out
    if not previous.get("ok"):
        out["errors"].extend(
            [f"metrics_previous:{e}" for e in (previous.get("errors") or ["failed"])]
        )
        return out

    cur_store, cur_prod = _metric_maps(current)
    prev_store, prev_prod = _metric_maps(previous)

    store_trends: list[dict[str, Any]] = []
    metric_keys = sorted(set(cur_store) | set(prev_store) | set(METRIC_KEY_TO_DEFINITION))
    for metric_key in metric_keys:
        curr_v = int(cur_store.get(metric_key, 0) or 0)
        prev_v = int(prev_store.get(metric_key, 0) or 0)
        if not include_stable_zeros and curr_v == 0 and prev_v == 0:
            continue
        store_trends.append(
            _build_trend_row(
                store_slug=slug,
                stable_identity_key=STORE_GRAIN_IDENTITY,
                metric_key=metric_key,
                trend_window=window,
                as_of=anchor,
                current_value=curr_v,
                previous_value=prev_v,
            )
        )

    identities_keys = sorted(set(cur_prod) | set(prev_prod))
    product_trends: list[dict[str, Any]] = []
    for identity, metric_key in identities_keys:
        curr_v = int(cur_prod.get((identity, metric_key), 0) or 0)
        prev_v = int(prev_prod.get((identity, metric_key), 0) or 0)
        if curr_v == 0 and prev_v == 0:
            continue
        product_trends.append(
            _build_trend_row(
                store_slug=slug,
                stable_identity_key=identity,
                metric_key=metric_key,
                trend_window=window,
                as_of=anchor,
                current_value=curr_v,
                previous_value=prev_v,
            )
        )

    by_direction: dict[str, int] = {}
    for row in store_trends + product_trends:
        d = str(row["trend_direction"])
        by_direction[d] = by_direction.get(d, 0) + 1

    canonical = {
        "computation_version": COMPUTATION_VERSION_V1,
        "store_slug": slug,
        "trend_window": window,
        "as_of": out["as_of"],
        "store_trends": [
            {
                "metric_key": r["metric_key"],
                "current_value": r["current_value"],
                "previous_value": r["previous_value"],
                "trend_direction": r["trend_direction"],
                "content_hash": r["content_hash"],
            }
            for r in store_trends
        ],
        "product_trends": [
            {
                "stable_identity_key": r["stable_identity_key"],
                "metric_key": r["metric_key"],
                "current_value": r["current_value"],
                "previous_value": r["previous_value"],
                "trend_direction": r["trend_direction"],
                "content_hash": r["content_hash"],
            }
            for r in product_trends
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    out["store_trends"] = store_trends
    out["product_trends"] = product_trends
    out["by_direction"] = by_direction
    out["canonical_fingerprint"] = fingerprint
    out["ok"] = True
    return out


def materialize_product_trends_v1(
    store_slug: str,
    *,
    trend_window: str = TREND_WINDOW_D7,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not product_trends_foundation_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "errors": ["trends_foundation_disabled"],
        }

    report = compute_product_trends_v1(
        store_slug,
        trend_window=trend_window,
        as_of=as_of,
        include_stable_zeros=False,
    )
    if not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_product_trend_values_schema(db)
    anchor = _floor_second(
        datetime.fromisoformat(str(report["as_of"]))
        if report.get("as_of")
        else (as_of or _utc_naive_now())
    )
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    rows = list(report.get("store_trends") or []) + list(
        report.get("product_trends") or []
    )
    upserted = 0
    try:
        for item in rows:
            identity = str(item.get("stable_identity_key") or "")
            metric_key = str(item.get("metric_key") or "")
            window = str(item.get("trend_window") or "")
            existing = (
                db.session.query(ProductTrendValue)
                .filter(
                    ProductTrendValue.store_slug == report["store_slug"],
                    ProductTrendValue.stable_identity_key == identity,
                    ProductTrendValue.metric_key == metric_key,
                    ProductTrendValue.trend_window == window,
                    ProductTrendValue.as_of_key == as_key,
                )
                .first()
            )
            if existing is None:
                existing = ProductTrendValue(
                    store_slug=report["store_slug"],
                    stable_identity_key=identity,
                    metric_key=metric_key,
                    metric_family=str(item.get("metric_family") or ""),
                    trend_window=window,
                    as_of=anchor,
                    as_of_key=as_key,
                    current_value=int(item.get("current_value") or 0),
                    previous_value=int(item.get("previous_value") or 0),
                    delta_abs=int(item.get("delta_abs") or 0),
                    trend_direction=str(item.get("trend_direction") or ""),
                    computation_version=COMPUTATION_VERSION_V1,
                    content_hash=str(item.get("content_hash") or ""),
                    computed_at=now,
                )
                db.session.add(existing)
            else:
                existing.metric_family = str(item.get("metric_family") or "")
                existing.as_of = anchor
                existing.current_value = int(item.get("current_value") or 0)
                existing.previous_value = int(item.get("previous_value") or 0)
                existing.delta_abs = int(item.get("delta_abs") or 0)
                existing.trend_direction = str(item.get("trend_direction") or "")
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
        log.debug("product trends materialize failed: %s", exc)
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
        "by_direction": report.get("by_direction") or {},
        "store_slug": report.get("store_slug"),
        "trend_window": report.get("trend_window"),
        "as_of": report.get("as_of"),
    }


def verify_trends_determinism_v1(
    store_slug: str,
    *,
    trend_window: str = TREND_WINDOW_D7,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = resolve_bound_as_of_v1(as_of)
    a = compute_product_trends_v1(
        store_slug, trend_window=trend_window, as_of=anchor
    )
    b = compute_product_trends_v1(
        store_slug, trend_window=trend_window, as_of=anchor
    )
    match = bool(
        a.get("ok")
        and b.get("ok")
        and a.get("canonical_fingerprint")
        and a.get("canonical_fingerprint") == b.get("canonical_fingerprint")
    )
    return {
        "ok": match,
        "deterministic": match,
        "as_of": anchor.isoformat(sep=" "),
        "fingerprint_a": a.get("canonical_fingerprint") or "",
        "fingerprint_b": b.get("canonical_fingerprint") or "",
        "by_direction": a.get("by_direction") or {},
        "store_trend_count": len(a.get("store_trends") or []),
        "product_trend_count": len(a.get("product_trends") or []),
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "compute_product_trends_v1",
    "materialize_product_trends_v1",
    "verify_trends_determinism_v1",
]
