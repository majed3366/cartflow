# -*- coding: utf-8 -*-
"""
Evidence Confidence Foundation V1 — evaluate Evidence Assembly bundles only.

No guidance, ranking, health, knowledge, or provider/signal/metric/trend reads.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import EvidenceConfidenceEvaluation
from schema_evidence_confidence_v1 import ensure_evidence_confidence_schema
from services.product_data.evidence_confidence_flag_v1 import (
    evidence_confidence_v1_enabled,
)
from services.product_data.evidence_confidence_types_v1 import (
    CONFIDENCE_VERSION_V1,
    CORE_EVIDENCE_METRIC_KEYS,
    EVALUATOR_VERSION_V1,
    confidence_level_for_score,
)
from services.product_data.product_evidence_assembly_v1 import (
    assemble_product_evidence_v1,
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


def _sample_size_score(total_metric_value: int) -> int:
    n = int(total_metric_value or 0)
    if n <= 0:
        return 0
    if n == 1:
        return 40
    if n <= 4:
        return 60
    if n <= 9:
        return 80
    return 100


def evaluate_bundle_confidence_v1(
    bundle: dict[str, Any],
    *,
    evaluated_at: datetime,
) -> dict[str, Any]:
    """Evaluate one assembled evidence bundle. Bundle-only input."""
    items = list(bundle.get("items") or [])
    present_keys = {
        str(i.get("metric_key") or "") for i in items if i.get("metric_key")
    }
    core = list(CORE_EVIDENCE_METRIC_KEYS)
    missing = [k for k in core if k not in present_keys]
    completeness = int(round(100.0 * (len(core) - len(missing)) / max(1, len(core))))

    layers: set[str] = set()
    for item in items:
        lineage = item.get("lineage") or {}
        layer = str(
            lineage.get("originating_layer") or item.get("source_layer") or ""
        )
        if "metrics" in layer:
            layers.add("metrics")
        if "trends" in layer:
            layers.add("trends")
    if len(layers) >= 2:
        source_diversity = 100
    elif len(layers) == 1:
        source_diversity = 50
    else:
        source_diversity = 0

    bundle_window = str(bundle.get("assembly_window") or "")
    bundle_as_of = str(bundle.get("as_of") or "")
    consistency = 100
    conflicting = False
    notes: list[str] = []
    for item in items:
        if str(item.get("trend_window") or "") not in {"", bundle_window}:
            consistency = min(consistency, 60)
            notes.append("trend_window_mismatch")
        lineage = item.get("lineage") or {}
        if lineage.get("originating_as_of") and str(
            lineage.get("originating_as_of")
        ) != bundle_as_of:
            consistency = min(consistency, 70)
            notes.append("as_of_mismatch")
        mv = item.get("metric_value")
        td = str(item.get("trend_direction") or "")
        if mv is not None and int(mv) > 0 and td == "disappeared":
            conflicting = True
            consistency = min(consistency, 40)
            notes.append(f"conflict:{item.get('metric_key')}:value_vs_disappeared")
        if mv is not None and int(mv) == 0 and td == "newly_appeared":
            conflicting = True
            consistency = min(consistency, 50)
            notes.append(f"conflict:{item.get('metric_key')}:zero_vs_newly_appeared")

    total_value = sum(
        int(i.get("metric_value") or 0)
        for i in items
        if i.get("metric_value") is not None
    )
    sample_size = _sample_size_score(total_value)

    freshness = 100
    missing_bounds = 0
    for item in items:
        obs_to = _parse_iso(item.get("observed_to"))
        if obs_to is None:
            missing_bounds += 1
        else:
            anchor = _parse_iso(bundle.get("as_of"))
            if anchor is not None and obs_to != anchor:
                # Windowed assemblies often have observed_to == as_of; mismatch softens.
                if abs((obs_to - anchor).total_seconds()) > 1:
                    freshness = min(freshness, 70)
    if items and missing_bounds == len(items):
        freshness = min(freshness, 70)
    elif missing_bounds:
        freshness = min(freshness, 85)

    if missing:
        notes.append("missing:" + ",".join(missing))
    if not items:
        notes.append("empty_bundle")
        completeness = 0
        sample_size = 0

    factors = {
        "completeness": completeness,
        "freshness": freshness,
        "consistency": consistency,
        "source_diversity": source_diversity,
        "sample_size": sample_size,
    }
    score = int(
        round(
            sum(factors.values()) / max(1, len(factors))
        )
    )
    level = confidence_level_for_score(score)
    notes = sorted(set(notes))

    as_of = _parse_iso(bundle.get("as_of")) or evaluated_at
    confidence_id = _sha(
        {
            "v": CONFIDENCE_VERSION_V1,
            "evaluator": EVALUATOR_VERSION_V1,
            "bundle": str(bundle.get("evidence_bundle_id") or ""),
            "as_of": _as_of_key(as_of),
        }
    )[:32]

    # Compact factual digest for Knowledge consumers (not interpretation).
    evidence_summary = {
        "assembly_window": str(bundle.get("assembly_window") or ""),
        "source_count": int(bundle.get("source_count") or len(items)),
        "items": [
            {
                "metric_key": str(i.get("metric_key") or ""),
                "metric_value": (
                    int(i["metric_value"]) if i.get("metric_value") is not None else None
                ),
                "trend_direction": i.get("trend_direction"),
                "trend_window": str(i.get("trend_window") or bundle.get("assembly_window") or ""),
            }
            for i in sorted(items, key=lambda r: str(r.get("metric_key") or ""))
            if i.get("metric_key")
        ],
    }

    payload = {
        "confidence_id": confidence_id,
        "evidence_bundle_id": str(bundle.get("evidence_bundle_id") or ""),
        "store_slug": str(bundle.get("store_slug") or ""),
        "subject_type": str(bundle.get("subject_type") or ""),
        "subject_id": str(bundle.get("subject_id") or ""),
        "confidence_level": level,
        "confidence_score": score,
        "confidence_version": CONFIDENCE_VERSION_V1,
        "evaluator_version": EVALUATOR_VERSION_V1,
        "evaluated_at": evaluated_at.isoformat(sep=" "),
        "as_of": as_of.isoformat(sep=" "),
        "factors": factors,
        "missing_sources": missing,
        "conflicting_signals": conflicting,
        "confidence_notes": notes,
        "evidence_summary": evidence_summary,
    }
    payload["content_hash"] = _sha(payload)
    return payload


def evaluate_evidence_confidence_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Assemble evidence via PEA API, then evaluate each bundle."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "confidence_version": CONFIDENCE_VERSION_V1,
        "evaluator_version": EVALUATOR_VERSION_V1,
        "evaluations": [],
        "evaluation_count": 0,
        "canonical_fingerprint": "",
        "errors": [],
        "inputs": {"evidence_assembly_only": True},
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out

    anchor = resolve_bound_as_of_v1(as_of)
    out["as_of"] = anchor.isoformat(sep=" ")
    assembled = assemble_product_evidence_v1(
        slug, assembly_window=window, as_of=anchor
    )
    if not assembled.get("ok"):
        out["errors"].extend(
            [f"evidence:{e}" for e in (assembled.get("errors") or ["failed"])]
        )
        return out

    evaluations = [
        evaluate_bundle_confidence_v1(bundle, evaluated_at=anchor)
        for bundle in (assembled.get("bundles") or [])
    ]
    evaluations = sorted(
        evaluations,
        key=lambda e: (e.get("subject_type") or "", e.get("subject_id") or ""),
    )
    fingerprint = _sha(
        {
            "v": EVALUATOR_VERSION_V1,
            "store": slug,
            "window": window,
            "as_of": out["as_of"],
            "evaluations": [
                {
                    "confidence_id": e["confidence_id"],
                    "evidence_bundle_id": e["evidence_bundle_id"],
                    "confidence_score": e["confidence_score"],
                    "confidence_level": e["confidence_level"],
                    "content_hash": e["content_hash"],
                }
                for e in evaluations
            ],
        }
    )
    out["evaluations"] = evaluations
    out["evaluation_count"] = len(evaluations)
    out["canonical_fingerprint"] = fingerprint
    out["ok"] = True
    return out


def materialize_evidence_confidence_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not evidence_confidence_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "errors": ["evidence_confidence_disabled"],
        }

    report = evaluate_evidence_confidence_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    if not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_evidence_confidence_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted = 0
    try:
        for ev in report.get("evaluations") or []:
            cid = str(ev["confidence_id"])
            existing = (
                db.session.query(EvidenceConfidenceEvaluation)
                .filter(EvidenceConfidenceEvaluation.confidence_id == cid)
                .first()
            )
            fields = dict(
                evidence_bundle_id=str(ev["evidence_bundle_id"]),
                store_slug=str(ev["store_slug"]),
                subject_type=str(ev.get("subject_type") or ""),
                subject_id=str(ev.get("subject_id") or ""),
                confidence_level=str(ev["confidence_level"]),
                confidence_score=int(ev["confidence_score"]),
                confidence_version=CONFIDENCE_VERSION_V1,
                evaluator_version=EVALUATOR_VERSION_V1,
                evaluated_at=now,
                as_of=anchor,
                as_of_key=as_key,
                completeness=int(ev["factors"]["completeness"]),
                freshness=int(ev["factors"]["freshness"]),
                consistency=int(ev["factors"]["consistency"]),
                source_diversity=int(ev["factors"]["source_diversity"]),
                sample_size=int(ev["factors"]["sample_size"]),
                missing_sources_json=json.dumps(
                    ev.get("missing_sources") or [], sort_keys=True
                ),
                conflicting_signals=bool(ev.get("conflicting_signals")),
                confidence_notes_json=json.dumps(
                    ev.get("confidence_notes") or [], sort_keys=True
                ),
                factors_json=json.dumps(ev.get("factors") or {}, sort_keys=True),
                content_hash=str(ev.get("content_hash") or ""),
            )
            if existing is None:
                db.session.add(
                    EvidenceConfidenceEvaluation(confidence_id=cid, **fields)
                )
            else:
                if existing.as_of_key != as_key:
                    continue
                for k, v in fields.items():
                    setattr(existing, k, v)
            upserted += 1
        db.session.commit()
    except SQLAlchemyError as exc:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.debug("evidence confidence materialize failed: %s", exc)
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
        "evaluation_count": report.get("evaluation_count") or 0,
        "store_slug": report.get("store_slug"),
        "assembly_window": report.get("assembly_window"),
        "as_of": report.get("as_of"),
    }


def verify_evidence_confidence_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = resolve_bound_as_of_v1(as_of)
    a = evaluate_evidence_confidence_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    b = evaluate_evidence_confidence_v1(
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
        "evaluation_count": a.get("evaluation_count") or 0,
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "evaluate_bundle_confidence_v1",
    "evaluate_evidence_confidence_v1",
    "materialize_evidence_confidence_v1",
    "verify_evidence_confidence_determinism_v1",
]
