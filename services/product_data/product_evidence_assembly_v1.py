# -*- coding: utf-8 -*-
"""
Product Evidence Assembly Foundation V1 — Metrics + Trends only.

Assembles factual evidence bundles. No confidence, ranking, or guidance.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ProductEvidenceBundle, ProductEvidenceItem
from schema_product_evidence_assembly_v1 import ensure_product_evidence_assembly_schema
from services.product_data.product_evidence_assembly_flag_v1 import (
    product_evidence_assembly_v1_enabled,
)
from services.product_data.product_evidence_assembly_types_v1 import (
    BUNDLE_VERSION_V1,
    COMPUTATION_VERSION_V1,
    SOURCE_LAYER_BOTH,
    SOURCE_LAYER_METRICS,
    SOURCE_LAYER_TRENDS,
    SUBJECT_TYPE_PRODUCT,
    SUBJECT_TYPE_STORE,
)
from services.product_data.product_metrics_foundation_v1 import (
    compute_product_metrics_v1,
)
from services.product_data.product_metrics_types_v1 import STORE_GRAIN_IDENTITY
from services.product_data.product_trends_foundation_v1 import (
    compute_product_trends_v1,
)
from services.product_data.product_trends_types_v1 import (
    TREND_WINDOW_D7,
    TREND_WINDOW_SPECS,
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


def _sha(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_iso(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _floor_second(value)
    try:
        return _floor_second(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def _index_metrics(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in report.get("store_metrics") or []:
        key = str(row.get("metric_key") or "")
        if key:
            out[(STORE_GRAIN_IDENTITY, key)] = row
    for row in report.get("product_metrics") or []:
        identity = str(row.get("stable_identity_key") or "")
        key = str(row.get("metric_key") or "")
        if key:
            out[(identity, key)] = row
    return out


def _index_trends(report: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in list(report.get("store_trends") or []) + list(
        report.get("product_trends") or []
    ):
        identity = str(row.get("stable_identity_key") or "")
        key = str(row.get("metric_key") or "")
        if key:
            out[(identity, key)] = row
    return out


def _build_item(
    *,
    bundle_id: str,
    store_slug: str,
    subject_type: str,
    subject_id: str,
    metric_key: str,
    metric_row: Optional[dict[str, Any]],
    trend_row: Optional[dict[str, Any]],
    assembly_window: str,
    as_of: datetime,
    observed_from: Optional[datetime],
    observed_to: Optional[datetime],
) -> dict[str, Any]:
    metric_value = int(metric_row["value"]) if metric_row is not None else None
    trend_direction = (
        str(trend_row.get("trend_direction") or "") if trend_row is not None else None
    )
    metrics_hash = str(metric_row.get("content_hash") or "") if metric_row else ""
    trends_hash = str(trend_row.get("content_hash") or "") if trend_row else ""
    has_metrics_lineage = bool(metrics_hash)
    has_trends_lineage = bool(trends_hash)
    if has_metrics_lineage and has_trends_lineage:
        source_layer = SOURCE_LAYER_BOTH
        # Keep <=64 chars for column; full hashes remain in lineage.
        source_record_id = _sha(f"{metrics_hash}|{trends_hash}")[:64]
    elif has_metrics_lineage:
        source_layer = SOURCE_LAYER_METRICS
        source_record_id = metrics_hash[:64]
    elif has_trends_lineage:
        source_layer = SOURCE_LAYER_TRENDS
        source_record_id = trends_hash[:64]
        if metric_value is None and trend_row is not None:
            metric_value = int(trend_row.get("current_value") or 0)
    else:
        # Should not happen; keep assemble resilient
        source_layer = SOURCE_LAYER_METRICS if metric_row is not None else SOURCE_LAYER_TRENDS
        source_record_id = "unlined"

    lineage = {
        "originating_layer": source_layer,
        "metrics_content_hash": metrics_hash or None,
        "trends_content_hash": trends_hash or None,
        "originating_window": assembly_window,
        "originating_as_of": as_of.isoformat(sep=" "),
        "metrics_computation_version": (
            str(metric_row.get("computation_version") or "") if metric_row else None
        ),
        "trends_computation_version": (
            str(trend_row.get("computation_version") or "") if trend_row else None
        ),
    }
    item_seed = {
        "bundle": bundle_id,
        "metric": metric_key,
        "layer": source_layer,
        "source": source_record_id,
    }
    evidence_item_id = _sha(item_seed)[:32]
    content_hash = _sha(
        {
            "item": evidence_item_id,
            "metric_key": metric_key,
            "metric_value": metric_value,
            "trend_direction": trend_direction,
            "trend_window": assembly_window,
            "source_layer": source_layer,
            "source_record_id": source_record_id,
            "lineage": lineage,
        }
    )
    return {
        "evidence_item_id": evidence_item_id,
        "evidence_bundle_id": bundle_id,
        "store_slug": store_slug,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "metric_key": metric_key,
        "metric_value": metric_value,
        "trend_direction": trend_direction or None,
        "trend_window": assembly_window,
        "source_layer": source_layer,
        "source_record_id": source_record_id,
        "observed_from": observed_from.isoformat(sep=" ") if observed_from else None,
        "observed_to": observed_to.isoformat(sep=" ") if observed_to else None,
        "lineage": lineage,
        "content_hash": content_hash,
    }


def _assemble_subject_bundle(
    *,
    store_slug: str,
    subject_type: str,
    subject_id: str,
    identity_key: str,
    metrics_idx: dict[tuple[str, str], dict[str, Any]],
    trends_idx: dict[tuple[str, str], dict[str, Any]],
    assembly_window: str,
    as_of: datetime,
    assembled_at: datetime,
    observed_from: Optional[datetime],
    observed_to: Optional[datetime],
) -> Optional[dict[str, Any]]:
    metric_keys = sorted(
        {
            k
            for (ident, k) in set(metrics_idx) | set(trends_idx)
            if ident == identity_key
        }
    )
    if not metric_keys:
        return None

    bundle_id = _sha(
        {
            "v": BUNDLE_VERSION_V1,
            "store": store_slug,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "window": assembly_window,
            "as_of": _as_of_key(as_of),
        }
    )[:32]

    items: list[dict[str, Any]] = []
    for metric_key in metric_keys:
        mrow = metrics_idx.get((identity_key, metric_key))
        trow = trends_idx.get((identity_key, metric_key))
        if mrow is None and trow is None:
            continue
        mval = int(mrow["value"]) if mrow is not None else 0
        tcur = int(trow.get("current_value") or 0) if trow is not None else 0
        if mval <= 0 and trow is None:
            continue
        if mval <= 0 and tcur <= 0 and trow is not None:
            # Keep trend-only disappearance facts (current 0, previous > 0)
            if str(trow.get("trend_direction") or "") in {"", "stable"}:
                continue
        # Prefer metrics row value; else trend current_value for lineage completeness
        effective_metric_row = mrow
        if effective_metric_row is None and trow is not None:
            effective_metric_row = {
                "value": tcur,
                "content_hash": "",
                "computation_version": None,
            }
        items.append(
            _build_item(
                bundle_id=bundle_id,
                store_slug=store_slug,
                subject_type=subject_type,
                subject_id=subject_id,
                metric_key=metric_key,
                metric_row=effective_metric_row,
                trend_row=trow,
                assembly_window=assembly_window,
                as_of=as_of,
                observed_from=observed_from,
                observed_to=observed_to,
            )
        )
    items = sorted(items, key=lambda r: str(r["metric_key"]))
    if not items:
        return None

    fingerprint = _sha(
        {
            "bundle_id": bundle_id,
            "items": [
                {
                    "evidence_item_id": i["evidence_item_id"],
                    "metric_key": i["metric_key"],
                    "metric_value": i["metric_value"],
                    "trend_direction": i["trend_direction"],
                    "source_layer": i["source_layer"],
                    "source_record_id": i["source_record_id"],
                    "content_hash": i["content_hash"],
                }
                for i in items
            ],
        }
    )
    return {
        "evidence_bundle_id": bundle_id,
        "store_slug": store_slug,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "bundle_version": BUNDLE_VERSION_V1,
        "assembled_at": assembled_at.isoformat(sep=" "),
        "assembly_window": assembly_window,
        "as_of": as_of.isoformat(sep=" "),
        "source_count": len(items),
        "fingerprint": fingerprint,
        "computation_version": COMPUTATION_VERSION_V1,
        "items": items,
    }


def assemble_product_evidence_v1(
    store_slug: str,
    *,
    assembly_window: str = TREND_WINDOW_D7,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Deterministic evidence bundles from Metrics + Trends APIs only."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or TREND_WINDOW_D7).strip().lower()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "bundle_version": BUNDLE_VERSION_V1,
        "computation_version": COMPUTATION_VERSION_V1,
        "bundles": [],
        "bundle_count": 0,
        "item_count": 0,
        "canonical_fingerprint": "",
        "errors": [],
        "inputs": {"metrics_only": True, "trends_only": True, "signals": False},
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if window not in TREND_WINDOW_SPECS:
        out["errors"].append(f"unsupported_assembly_window:{window}")
        return out

    anchor = resolve_bound_as_of_v1(as_of)
    assembled_at = anchor
    out["as_of"] = anchor.isoformat(sep=" ")
    spec = TREND_WINDOW_SPECS[window]

    trends = compute_product_trends_v1(
        slug, trend_window=window, as_of=anchor, include_stable_zeros=False
    )
    metrics = compute_product_metrics_v1(
        slug,
        window_code=spec.metric_window_code,
        as_of=anchor,
        include_zero_store_metrics=False,
    )
    if not trends.get("ok"):
        out["errors"].extend(
            [f"trends:{e}" for e in (trends.get("errors") or ["failed"])]
        )
        return out
    if not metrics.get("ok"):
        out["errors"].extend(
            [f"metrics:{e}" for e in (metrics.get("errors") or ["failed"])]
        )
        return out

    observed_from = _parse_iso(metrics.get("window_start"))
    observed_to = _parse_iso(metrics.get("window_end")) or anchor
    metrics_idx = _index_metrics(metrics)
    trends_idx = _index_trends(trends)

    identities = sorted(
        {
            ident
            for (ident, _) in set(metrics_idx) | set(trends_idx)
            if ident != STORE_GRAIN_IDENTITY
        }
    )

    bundles: list[dict[str, Any]] = []
    store_bundle = _assemble_subject_bundle(
        store_slug=slug,
        subject_type=SUBJECT_TYPE_STORE,
        subject_id=slug,
        identity_key=STORE_GRAIN_IDENTITY,
        metrics_idx=metrics_idx,
        trends_idx=trends_idx,
        assembly_window=window,
        as_of=anchor,
        assembled_at=assembled_at,
        observed_from=observed_from,
        observed_to=observed_to,
    )
    if store_bundle:
        bundles.append(store_bundle)

    for identity in identities:
        bundle = _assemble_subject_bundle(
            store_slug=slug,
            subject_type=SUBJECT_TYPE_PRODUCT,
            subject_id=identity,
            identity_key=identity,
            metrics_idx=metrics_idx,
            trends_idx=trends_idx,
            assembly_window=window,
            as_of=anchor,
            assembled_at=assembled_at,
            observed_from=observed_from,
            observed_to=observed_to,
        )
        if bundle:
            bundles.append(bundle)

    bundles = sorted(
        bundles, key=lambda b: (b["subject_type"], b["subject_id"])
    )
    item_count = sum(int(b["source_count"]) for b in bundles)
    canonical_fingerprint = _sha(
        {
            "v": COMPUTATION_VERSION_V1,
            "store": slug,
            "window": window,
            "as_of": out["as_of"],
            "bundles": [
                {
                    "evidence_bundle_id": b["evidence_bundle_id"],
                    "fingerprint": b["fingerprint"],
                    "source_count": b["source_count"],
                }
                for b in bundles
            ],
        }
    )
    out["bundles"] = bundles
    out["bundle_count"] = len(bundles)
    out["item_count"] = item_count
    out["canonical_fingerprint"] = canonical_fingerprint
    out["ok"] = True
    return out


def materialize_product_evidence_v1(
    store_slug: str,
    *,
    assembly_window: str = TREND_WINDOW_D7,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not product_evidence_assembly_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted_bundles": 0,
            "upserted_items": 0,
            "errors": ["evidence_assembly_disabled"],
        }

    report = assemble_product_evidence_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    if not report.get("ok"):
        return {
            "ok": False,
            "upserted_bundles": 0,
            "upserted_items": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_product_evidence_assembly_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted_bundles = 0
    upserted_items = 0
    try:
        for bundle in report.get("bundles") or []:
            bid = str(bundle["evidence_bundle_id"])
            existing = (
                db.session.query(ProductEvidenceBundle)
                .filter(ProductEvidenceBundle.evidence_bundle_id == bid)
                .first()
            )
            if existing is None:
                existing = ProductEvidenceBundle(
                    evidence_bundle_id=bid,
                    store_slug=str(bundle["store_slug"]),
                    subject_type=str(bundle["subject_type"]),
                    subject_id=str(bundle["subject_id"]),
                    bundle_version=BUNDLE_VERSION_V1,
                    assembled_at=now,
                    assembly_window=str(bundle["assembly_window"]),
                    as_of=anchor,
                    as_of_key=as_key,
                    source_count=int(bundle["source_count"]),
                    fingerprint=str(bundle["fingerprint"]),
                    computation_version=COMPUTATION_VERSION_V1,
                )
                db.session.add(existing)
            else:
                # Same grain refresh only — never rewrite a different as_of_key row
                if existing.as_of_key != as_key:
                    continue
                existing.assembled_at = now
                existing.source_count = int(bundle["source_count"])
                existing.fingerprint = str(bundle["fingerprint"])
                existing.computation_version = COMPUTATION_VERSION_V1
            upserted_bundles += 1

            # Replace items for this bundle id (idempotent refresh)
            db.session.query(ProductEvidenceItem).filter(
                ProductEvidenceItem.evidence_bundle_id == bid
            ).delete(synchronize_session=False)
            for item in bundle.get("items") or []:
                db.session.add(
                    ProductEvidenceItem(
                        evidence_bundle_id=bid,
                        evidence_item_id=str(item["evidence_item_id"]),
                        store_slug=str(item["store_slug"]),
                        subject_type=str(item["subject_type"]),
                        subject_id=str(item["subject_id"]),
                        metric_key=str(item["metric_key"]),
                        metric_value=(
                            int(item["metric_value"])
                            if item.get("metric_value") is not None
                            else None
                        ),
                        trend_direction=item.get("trend_direction"),
                        trend_window=str(item.get("trend_window") or ""),
                        source_layer=str(item.get("source_layer") or ""),
                        source_record_id=str(item.get("source_record_id") or ""),
                        observed_from=_parse_iso(item.get("observed_from")),
                        observed_to=_parse_iso(item.get("observed_to")),
                        lineage_json=json.dumps(
                            item.get("lineage") or {}, sort_keys=True
                        ),
                        content_hash=str(item.get("content_hash") or ""),
                        assembled_at=now,
                    )
                )
                upserted_items += 1
        db.session.commit()
    except SQLAlchemyError as exc:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.debug("product evidence assembly materialize failed: %s", exc)
        return {
            "ok": False,
            "upserted_bundles": 0,
            "upserted_items": 0,
            "errors": [f"materialize:{type(exc).__name__}"],
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    return {
        "ok": True,
        "upserted_bundles": upserted_bundles,
        "upserted_items": upserted_items,
        "errors": [],
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "bundle_count": report.get("bundle_count") or 0,
        "item_count": report.get("item_count") or 0,
        "store_slug": report.get("store_slug"),
        "assembly_window": report.get("assembly_window"),
        "as_of": report.get("as_of"),
    }


def verify_evidence_assembly_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = TREND_WINDOW_D7,
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = resolve_bound_as_of_v1(as_of)
    a = assemble_product_evidence_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    b = assemble_product_evidence_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
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
        "bundle_count": a.get("bundle_count") or 0,
        "item_count": a.get("item_count") or 0,
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "assemble_product_evidence_v1",
    "materialize_product_evidence_v1",
    "verify_evidence_assembly_determinism_v1",
]
