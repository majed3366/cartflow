# -*- coding: utf-8 -*-
"""
Knowledge Foundation V1 — factual statements from Evidence Confidence only.

No advice, recommendations, decisions, or lower-layer reads.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import KnowledgeStatement
from schema_knowledge_foundation_v1 import ensure_knowledge_foundation_schema
from services.product_data.evidence_confidence_foundation_v1 import (
    evaluate_evidence_confidence_v1,
)
from services.product_data.knowledge_foundation_flag_v1 import (
    knowledge_foundation_v1_enabled,
)
from services.product_data.knowledge_foundation_types_v1 import (
    GENERATOR_VERSION_V1,
    HIGH_CONFIDENCE_LEVELS,
    KNOWLEDGE_TYPE_EVIDENCE_CONFLICT,
    KNOWLEDGE_TYPE_EVIDENCE_GAP,
    KNOWLEDGE_TYPE_EVIDENCE_QUALITY,
    KNOWLEDGE_TYPE_METRIC_TREND,
    KNOWLEDGE_VERSION_V1,
    WINDOW_LENGTH_DAYS,
    trend_statement,
)

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


def _build_record(
    *,
    store_slug: str,
    subject_type: str,
    subject_id: str,
    knowledge_type: str,
    statement: str,
    evidence_confidence_id: str,
    confidence_level: str,
    assembly_window: str,
    as_of: datetime,
    generated_at: datetime,
    seed_extra: str = "",
    metric_key: str = "",
    trend_direction: str = "",
    gap_key: str = "",
) -> dict[str, Any]:
    days = WINDOW_LENGTH_DAYS.get(assembly_window, 7)
    valid_until = as_of + timedelta(days=days)
    knowledge_id = _sha(
        {
            "v": KNOWLEDGE_VERSION_V1,
            "gen": GENERATOR_VERSION_V1,
            "confidence": evidence_confidence_id,
            "type": knowledge_type,
            "statement": statement,
            "extra": seed_extra,
            "as_of": _as_of_key(as_of),
        }
    )[:32]
    fingerprint = _sha(
        {
            "knowledge_id": knowledge_id,
            "store_slug": store_slug,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "knowledge_type": knowledge_type,
            "statement": statement,
            "evidence_confidence_id": evidence_confidence_id,
            "confidence_level": confidence_level,
            "assembly_window": assembly_window,
            "as_of": as_of.isoformat(sep=" "),
            "knowledge_version": KNOWLEDGE_VERSION_V1,
        }
    )
    return {
        "knowledge_id": knowledge_id,
        "store_slug": store_slug,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "knowledge_type": knowledge_type,
        "statement": statement,
        "evidence_confidence_id": evidence_confidence_id,
        "confidence_level": confidence_level,
        "assembly_window": assembly_window,
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": valid_until.isoformat(sep=" "),
        "generated_at": generated_at.isoformat(sep=" "),
        "as_of": as_of.isoformat(sep=" "),
        "knowledge_version": KNOWLEDGE_VERSION_V1,
        "fingerprint": fingerprint,
        # Structured facets for Guidance Eligibility → Commercial Guidance contract.
        "metric_key": str(metric_key or ""),
        "trend_direction": str(trend_direction or ""),
        "gap_key": str(gap_key or ""),
    }


def statements_from_confidence_evaluation_v1(
    evaluation: dict[str, Any],
    *,
    generated_at: datetime,
) -> list[dict[str, Any]]:
    """Derive knowledge records from a single confidence evaluation dict only."""
    cid = str(evaluation.get("confidence_id") or "")
    if not cid:
        return []
    store_slug = str(evaluation.get("store_slug") or "")
    subject_type = str(evaluation.get("subject_type") or "")
    subject_id = str(evaluation.get("subject_id") or "")
    level = str(evaluation.get("confidence_level") or "")
    as_of = _parse_iso(evaluation.get("as_of")) or generated_at
    summary = evaluation.get("evidence_summary") or {}
    window = str(
        summary.get("assembly_window")
        or evaluation.get("assembly_window")
        or "d7"
    )

    out: list[dict[str, Any]] = []
    out.append(
        _build_record(
            store_slug=store_slug,
            subject_type=subject_type,
            subject_id=subject_id,
            knowledge_type=KNOWLEDGE_TYPE_EVIDENCE_QUALITY,
            statement=f"Evidence quality is {level}.",
            evidence_confidence_id=cid,
            confidence_level=level,
            assembly_window=window,
            as_of=as_of,
            generated_at=generated_at,
            seed_extra="quality",
        )
    )

    if evaluation.get("conflicting_signals"):
        out.append(
            _build_record(
                store_slug=store_slug,
                subject_type=subject_type,
                subject_id=subject_id,
                knowledge_type=KNOWLEDGE_TYPE_EVIDENCE_CONFLICT,
                statement=(
                    "Conflicting signals were flagged in the evidence evaluation."
                ),
                evidence_confidence_id=cid,
                confidence_level=level,
                assembly_window=window,
                as_of=as_of,
                generated_at=generated_at,
                seed_extra="conflict",
            )
        )

    for missing in evaluation.get("missing_sources") or []:
        key = str(missing or "").strip()
        if not key:
            continue
        out.append(
            _build_record(
                store_slug=store_slug,
                subject_type=subject_type,
                subject_id=subject_id,
                knowledge_type=KNOWLEDGE_TYPE_EVIDENCE_GAP,
                statement=f"Evidence does not include {key}.",
                evidence_confidence_id=cid,
                confidence_level=level,
                assembly_window=window,
                as_of=as_of,
                generated_at=generated_at,
                seed_extra=f"gap:{key}",
                gap_key=key,
            )
        )

    if level in HIGH_CONFIDENCE_LEVELS:
        for item in summary.get("items") or []:
            metric_key = str(item.get("metric_key") or "")
            direction = str(item.get("trend_direction") or "")
            item_window = str(item.get("trend_window") or window)
            stmt = trend_statement(metric_key, direction, item_window)
            if not stmt:
                continue
            out.append(
                _build_record(
                    store_slug=store_slug,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    knowledge_type=KNOWLEDGE_TYPE_METRIC_TREND,
                    statement=stmt,
                    evidence_confidence_id=cid,
                    confidence_level=level,
                    assembly_window=item_window,
                    as_of=as_of,
                    generated_at=generated_at,
                    seed_extra=f"trend:{metric_key}:{direction}",
                    metric_key=metric_key,
                    trend_direction=direction,
                )
            )

    return out


def generate_knowledge_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Generate knowledge exclusively via Evidence Confidence API."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "knowledge_version": KNOWLEDGE_VERSION_V1,
        "generator_version": GENERATOR_VERSION_V1,
        "statements": [],
        "statement_count": 0,
        "canonical_fingerprint": "",
        "errors": [],
        "inputs": {"evidence_confidence_only": True},
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out

    anchor = _floor_second(as_of or _utc_naive_now())
    out["as_of"] = anchor.isoformat(sep=" ")
    confidence = evaluate_evidence_confidence_v1(
        slug, assembly_window=window, as_of=anchor
    )
    if not confidence.get("ok"):
        out["errors"].extend(
            [f"confidence:{e}" for e in (confidence.get("errors") or ["failed"])]
        )
        return out

    statements: list[dict[str, Any]] = []
    for evaluation in confidence.get("evaluations") or []:
        statements.extend(
            statements_from_confidence_evaluation_v1(
                evaluation, generated_at=anchor
            )
        )
    statements = sorted(
        statements,
        key=lambda s: (
            s.get("subject_type") or "",
            s.get("subject_id") or "",
            s.get("knowledge_type") or "",
            s.get("statement") or "",
        ),
    )
    fingerprint = _sha(
        {
            "v": GENERATOR_VERSION_V1,
            "store": slug,
            "window": window,
            "as_of": out["as_of"],
            "statements": [
                {
                    "knowledge_id": s["knowledge_id"],
                    "fingerprint": s["fingerprint"],
                    "evidence_confidence_id": s["evidence_confidence_id"],
                    "statement": s["statement"],
                }
                for s in statements
            ],
        }
    )
    out["statements"] = statements
    out["statement_count"] = len(statements)
    out["canonical_fingerprint"] = fingerprint
    out["ok"] = True
    return out


def materialize_knowledge_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not knowledge_foundation_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "errors": ["knowledge_foundation_disabled"],
        }

    report = generate_knowledge_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    if not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_knowledge_foundation_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted = 0
    try:
        for stmt in report.get("statements") or []:
            kid = str(stmt["knowledge_id"])
            existing = (
                db.session.query(KnowledgeStatement)
                .filter(KnowledgeStatement.knowledge_id == kid)
                .first()
            )
            fields = dict(
                store_slug=str(stmt["store_slug"]),
                subject_type=str(stmt.get("subject_type") or ""),
                subject_id=str(stmt.get("subject_id") or ""),
                knowledge_type=str(stmt["knowledge_type"]),
                statement=str(stmt["statement"]),
                evidence_confidence_id=str(stmt["evidence_confidence_id"]),
                confidence_level=str(stmt.get("confidence_level") or ""),
                assembly_window=str(stmt.get("assembly_window") or ""),
                valid_from=_parse_iso(stmt.get("valid_from")) or anchor,
                valid_until=_parse_iso(stmt.get("valid_until"))
                or (anchor + timedelta(days=7)),
                generated_at=now,
                as_of=anchor,
                as_of_key=as_key,
                knowledge_version=KNOWLEDGE_VERSION_V1,
                fingerprint=str(stmt.get("fingerprint") or ""),
            )
            if existing is None:
                db.session.add(KnowledgeStatement(knowledge_id=kid, **fields))
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
        log.debug("knowledge foundation materialize failed: %s", exc)
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
        "statement_count": report.get("statement_count") or 0,
        "store_slug": report.get("store_slug"),
        "assembly_window": report.get("assembly_window"),
        "as_of": report.get("as_of"),
    }


def verify_knowledge_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = _floor_second(as_of or _utc_naive_now())
    a = generate_knowledge_v1(store_slug, assembly_window=assembly_window, as_of=anchor)
    b = generate_knowledge_v1(store_slug, assembly_window=assembly_window, as_of=anchor)
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
        "statement_count": a.get("statement_count") or 0,
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "statements_from_confidence_evaluation_v1",
    "generate_knowledge_v1",
    "materialize_knowledge_v1",
    "verify_knowledge_determinism_v1",
]
