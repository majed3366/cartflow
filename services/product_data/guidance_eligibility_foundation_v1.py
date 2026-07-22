# -*- coding: utf-8 -*-
"""
Guidance Eligibility Foundation V1 — Knowledge-only permission governance.

Does not generate guidance, recommendations, or business advice.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import GuidanceEligibilityEvaluation
from schema_guidance_eligibility_v1 import ensure_guidance_eligibility_schema
from services.product_data.guidance_eligibility_flag_v1 import (
    guidance_eligibility_v1_enabled,
)
from services.product_data.guidance_eligibility_types_v1 import (
    BLOCK_BELOW_COUNT,
    BLOCK_CONFIDENCE,
    BLOCK_CONFLICT,
    BLOCK_EXPIRED,
    BLOCK_MISSING_QUALITY,
    BLOCK_MISSING_TREND,
    BLOCK_NO_KNOWLEDGE,
    ELIGIBILITY_VERSION_V1,
    EVALUATOR_VERSION_V1,
    HIGH_CONFIDENCE_LEVELS,
    REQUIRED_KNOWLEDGE_COUNT_V1,
    STATUS_CONFLICTING_KNOWLEDGE,
    STATUS_ELIGIBLE,
    STATUS_EXPIRED_KNOWLEDGE,
    STATUS_INSUFFICIENT_CONFIDENCE,
    STATUS_INSUFFICIENT_KNOWLEDGE,
    STATUS_PENDING_OBSERVATION,
)
from services.product_data.knowledge_foundation_types_v1 import (
    KNOWLEDGE_TYPE_EVIDENCE_CONFLICT,
    KNOWLEDGE_TYPE_EVIDENCE_QUALITY,
    KNOWLEDGE_TYPE_METRIC_TREND,
)
from services.product_data.knowledge_foundation_v1 import generate_knowledge_v1
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


def _knowledge_context_from_statements(
    statements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Governed knowledge digest for downstream Commercial Guidance (contract only)."""
    ctx: list[dict[str, Any]] = []
    ordered = sorted(
        statements,
        key=lambda s: (
            str(s.get("knowledge_type") or ""),
            str(s.get("knowledge_id") or ""),
        ),
    )
    for s in ordered:
        kid = str(s.get("knowledge_id") or "")
        if not kid:
            continue
        ctx.append(
            {
                "knowledge_id": kid,
                "knowledge_type": str(s.get("knowledge_type") or ""),
                "statement": str(s.get("statement") or ""),
                "confidence_level": str(s.get("confidence_level") or ""),
                "valid_until": str(s.get("valid_until") or ""),
                "assembly_window": str(s.get("assembly_window") or ""),
                "metric_key": str(s.get("metric_key") or ""),
                "trend_direction": str(s.get("trend_direction") or ""),
                "gap_key": str(s.get("gap_key") or ""),
            }
        )
    return ctx


def evaluate_subject_eligibility_v1(
    *,
    store_slug: str,
    subject_type: str,
    subject_id: str,
    statements: list[dict[str, Any]],
    as_of: datetime,
    evaluated_at: datetime,
) -> dict[str, Any]:
    """One canonical eligibility status for a subject from knowledge statements."""
    required = REQUIRED_KNOWLEDGE_COUNT_V1
    knowledge_ids = sorted(
        str(s.get("knowledge_id") or "") for s in statements if s.get("knowledge_id")
    )
    knowledge_count = len(statements)
    knowledge_context = _knowledge_context_from_statements(statements)
    blocking: list[str] = []
    status = STATUS_ELIGIBLE
    reason = "required_knowledge_present_and_current"

    if knowledge_count == 0:
        status = STATUS_PENDING_OBSERVATION
        blocking = [BLOCK_NO_KNOWLEDGE]
        reason = "no_knowledge_statements_for_subject"
    else:
        expired = False
        for s in statements:
            until = _parse_iso(s.get("valid_until"))
            if until is not None and until < as_of:
                expired = True
                break
        has_conflict = any(
            str(s.get("knowledge_type") or "") == KNOWLEDGE_TYPE_EVIDENCE_CONFLICT
            for s in statements
        )
        quality = [
            s
            for s in statements
            if str(s.get("knowledge_type") or "") == KNOWLEDGE_TYPE_EVIDENCE_QUALITY
        ]
        trends = [
            s
            for s in statements
            if str(s.get("knowledge_type") or "") == KNOWLEDGE_TYPE_METRIC_TREND
        ]
        quality_level = ""
        if quality:
            quality_level = str(quality[0].get("confidence_level") or "").strip()

        if expired:
            status = STATUS_EXPIRED_KNOWLEDGE
            blocking = [BLOCK_EXPIRED]
            reason = "one_or_more_knowledge_statements_expired"
        elif has_conflict:
            status = STATUS_CONFLICTING_KNOWLEDGE
            blocking = [BLOCK_CONFLICT]
            reason = "conflict_flag_knowledge_present"
        elif quality and quality_level not in HIGH_CONFIDENCE_LEVELS:
            status = STATUS_INSUFFICIENT_CONFIDENCE
            blocking = [BLOCK_CONFIDENCE]
            reason = f"evidence_quality_confidence_is_{quality_level or 'unknown'}"
        else:
            if not quality:
                blocking.append(BLOCK_MISSING_QUALITY)
            if not trends:
                blocking.append(BLOCK_MISSING_TREND)
            if knowledge_count < required:
                blocking.append(BLOCK_BELOW_COUNT)
            if blocking:
                status = STATUS_INSUFFICIENT_KNOWLEDGE
                reason = "required_knowledge_not_satisfied"
            else:
                status = STATUS_ELIGIBLE
                blocking = []
                reason = "required_knowledge_present_and_current"

    eligibility_id = _sha(
        {
            "v": ELIGIBILITY_VERSION_V1,
            "eval": EVALUATOR_VERSION_V1,
            "store": store_slug,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "as_of": _as_of_key(as_of),
            "status": status,
            "knowledge_ids": knowledge_ids,
        }
    )[:32]
    payload = {
        "eligibility_id": eligibility_id,
        "store_slug": store_slug,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "eligibility_status": status,
        "eligibility_reason": reason,
        "knowledge_count": knowledge_count,
        "required_knowledge_count": required,
        "blocking_conditions": blocking,
        "knowledge_ids": knowledge_ids,
        "knowledge_context": knowledge_context,
        "evaluated_at": evaluated_at.isoformat(sep=" "),
        "as_of": as_of.isoformat(sep=" "),
        "eligibility_version": ELIGIBILITY_VERSION_V1,
        "contract_version": "gef_v1_guidance_context",
    }
    payload["fingerprint"] = _sha(payload)
    return payload


def evaluate_guidance_eligibility_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Evaluate eligibility exclusively via Knowledge Foundation API."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "eligibility_version": ELIGIBILITY_VERSION_V1,
        "evaluator_version": EVALUATOR_VERSION_V1,
        "evaluations": [],
        "evaluation_count": 0,
        "canonical_fingerprint": "",
        "errors": [],
        "inputs": {"knowledge_foundation_only": True},
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out

    anchor = resolve_bound_as_of_v1(as_of)
    out["as_of"] = anchor.isoformat(sep=" ")
    knowledge = generate_knowledge_v1(slug, assembly_window=window, as_of=anchor)
    if not knowledge.get("ok"):
        out["errors"].extend(
            [f"knowledge:{e}" for e in (knowledge.get("errors") or ["failed"])]
        )
        return out

    by_subject: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for stmt in knowledge.get("statements") or []:
        key = (
            str(stmt.get("subject_type") or ""),
            str(stmt.get("subject_id") or ""),
        )
        by_subject.setdefault(key, []).append(stmt)

    evaluations = [
        evaluate_subject_eligibility_v1(
            store_slug=slug,
            subject_type=stype,
            subject_id=sid,
            statements=stmts,
            as_of=anchor,
            evaluated_at=anchor,
        )
        for (stype, sid), stmts in sorted(by_subject.items())
    ]
    # If knowledge returned zero statements overall, still emit store pending.
    if not evaluations:
        evaluations = [
            evaluate_subject_eligibility_v1(
                store_slug=slug,
                subject_type="store",
                subject_id=slug,
                statements=[],
                as_of=anchor,
                evaluated_at=anchor,
            )
        ]

    fingerprint = _sha(
        {
            "v": EVALUATOR_VERSION_V1,
            "store": slug,
            "window": window,
            "as_of": out["as_of"],
            "evaluations": [
                {
                    "eligibility_id": e["eligibility_id"],
                    "subject_type": e["subject_type"],
                    "subject_id": e["subject_id"],
                    "eligibility_status": e["eligibility_status"],
                    "fingerprint": e["fingerprint"],
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


def materialize_guidance_eligibility_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not guidance_eligibility_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "errors": ["guidance_eligibility_disabled"],
        }

    report = evaluate_guidance_eligibility_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    if not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_guidance_eligibility_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted = 0
    try:
        for ev in report.get("evaluations") or []:
            eid = str(ev["eligibility_id"])
            existing = (
                db.session.query(GuidanceEligibilityEvaluation)
                .filter(GuidanceEligibilityEvaluation.eligibility_id == eid)
                .first()
            )
            fields = dict(
                store_slug=str(ev["store_slug"]),
                subject_type=str(ev.get("subject_type") or ""),
                subject_id=str(ev.get("subject_id") or ""),
                eligibility_status=str(ev["eligibility_status"]),
                eligibility_reason=str(ev.get("eligibility_reason") or ""),
                knowledge_count=int(ev.get("knowledge_count") or 0),
                required_knowledge_count=int(
                    ev.get("required_knowledge_count") or REQUIRED_KNOWLEDGE_COUNT_V1
                ),
                blocking_conditions_json=json.dumps(
                    ev.get("blocking_conditions") or [], sort_keys=True
                ),
                knowledge_ids_json=json.dumps(
                    ev.get("knowledge_ids") or [], sort_keys=True
                ),
                evaluated_at=now,
                as_of=anchor,
                as_of_key=as_key,
                eligibility_version=ELIGIBILITY_VERSION_V1,
                fingerprint=str(ev.get("fingerprint") or ""),
            )
            if existing is None:
                db.session.add(
                    GuidanceEligibilityEvaluation(eligibility_id=eid, **fields)
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
        log.debug("guidance eligibility materialize failed: %s", exc)
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


def verify_guidance_eligibility_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    anchor = resolve_bound_as_of_v1(as_of)
    a = evaluate_guidance_eligibility_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    b = evaluate_guidance_eligibility_v1(
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
    "evaluate_subject_eligibility_v1",
    "evaluate_guidance_eligibility_v1",
    "materialize_guidance_eligibility_v1",
    "verify_guidance_eligibility_determinism_v1",
]
