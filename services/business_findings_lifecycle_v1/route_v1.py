# -*- coding: utf-8 -*-
"""
Routing stages for BFL — advances lifecycle without rewriting KF/OT/SCF generators.

Knowledge: parallel statement write (ciknow-style) with finding lineage.
Operational Truth: commercial findings are not OT packages — record explicit route decision.
Surface: mark destinations eligible for composition/consumption.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.business_findings_lifecycle_v1.lifecycle_v1 import advance_state
from services.business_findings_lifecycle_v1.types_v1 import (
    KNOWLEDGE_TYPE_BFE,
    LS_KNOWLEDGE_ROUTED,
    LS_OT_ROUTED,
    LS_SURFACE_ELIGIBLE,
    SOURCE_TYPE_BFE,
    VIS_ELIGIBLE,
    VIS_SUPPRESSED,
)

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def route_knowledge_v1(record: dict[str, Any]) -> dict[str, Any]:
    """Advance to knowledge_routed; optionally materialize a KF observation row."""
    routing = dict(record.get("routing") or {})
    diag = dict(record.get("diagnostics") or {})
    knowledge_id = f"bfe_kn:{record.get('finding_id')}"[:64]
    wrote = False
    error = ""
    try:
        from extensions import db
        from models import KnowledgeStatement
        from schema_knowledge_foundation_v1 import ensure_knowledge_foundation_schema

        ensure_knowledge_foundation_schema(db)
        now = _utc_naive_now()
        gen = record.get("generated_at")
        if isinstance(gen, str):
            gen = datetime.fromisoformat(gen)
        if not isinstance(gen, datetime):
            gen = now
        valid_until = record.get("expires_at")
        if isinstance(valid_until, str) and valid_until:
            valid_until = datetime.fromisoformat(valid_until)
        if not isinstance(valid_until, datetime):
            valid_until = gen + timedelta(days=14)
        statement = (
            str(record.get("title") or "")
            + " — "
            + str(record.get("merchant_summary") or "")
        )[:2000]
        existing = (
            db.session.query(KnowledgeStatement)
            .filter(KnowledgeStatement.knowledge_id == knowledge_id)
            .first()
        )
        fields = dict(
            store_slug=str(record.get("store_slug") or ""),
            subject_type="product" if record.get("product_id") else "store",
            subject_id=str(
                record.get("product_id") or record.get("store_slug") or ""
            )[:256],
            knowledge_type=KNOWLEDGE_TYPE_BFE,
            statement=statement or "business_finding",
            evidence_confidence_id=f"bfe:{record.get('finding_id')}"[:64],
            confidence_level=str(record.get("confidence") or "unknown")[:32],
            assembly_window="d14",
            valid_from=gen,
            valid_until=valid_until,
            generated_at=now,
            as_of=gen,
            as_of_key=str(record.get("as_of_key") or "")[:32],
            knowledge_version="bfl_v1",
            fingerprint=str(record.get("fingerprint") or "")[:64],
            source_type=SOURCE_TYPE_BFE,
            source_contract_version="business_finding_v1",
            source_synthesis_id=str(record.get("finding_id") or "")[:64],
            source_synthesis_key=str(record.get("finding_type") or "")[:64],
            source_rule_key=str(record.get("finding_type") or "")[:64],
            source_rule_version="bfe_v1",
            source_fingerprint=str(record.get("fingerprint") or "")[:64],
            is_current=True,
            superseded_at=None,
        )
        if existing is None:
            db.session.add(KnowledgeStatement(knowledge_id=knowledge_id, **fields))
        else:
            for k, v in fields.items():
                setattr(existing, k, v)
        db.session.commit()
        wrote = True
    except Exception as exc:  # noqa: BLE001
        error = type(exc).__name__
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        log.warning("bfl knowledge route failed: %s", exc)

    routing["knowledge"] = {
        "routed": True,
        "wrote_statement": wrote,
        "knowledge_id": knowledge_id if wrote else None,
        "error": error or None,
    }
    record["routing"] = routing
    ok, code = advance_state(
        record, LS_KNOWLEDGE_ROUTED, reason="route_knowledge_v1"
    )
    diag["routed_knowledge"] = bool(wrote or ok)
    diag["stopped_at"] = record.get("lifecycle_state")
    if not ok:
        diag["route_knowledge_error"] = code
    record["diagnostics"] = diag
    return record


def route_guidance_v1(record: dict[str, Any]) -> dict[str, Any]:
    """
    Record Guidance-path eligibility without generating Guidance.

    Guidance layers consume Knowledge / commercial guidance foundations —
    they must never invent findings. Not a lifecycle stage (see types_v1).
    """
    routing = dict(record.get("routing") or {})
    kn = routing.get("knowledge") or {}
    routing["guidance"] = {
        "routed": True,
        "generates_guidance": False,
        "consumable_via_knowledge": bool(kn.get("wrote_statement") or kn.get("routed")),
        "knowledge_id": kn.get("knowledge_id"),
        "reason": "surfaces_and_guidance_consume_findings_only",
    }
    record["routing"] = routing
    diag = dict(record.get("diagnostics") or {})
    diag["routed_guidance"] = True
    diag["stopped_at"] = record.get("lifecycle_state")
    record["diagnostics"] = diag
    return record


def route_operational_truth_v1(record: dict[str, Any]) -> dict[str, Any]:
    """
    Commercial findings are not Operational Truth packages.
    Explicitly record the route decision and advance lifecycle (no silent skip).
    """
    routing = dict(record.get("routing") or {})
    routing["operational_truth"] = {
        "routed": True,
        "eligible_as_ot_package": False,
        "reason": "commercial_finding_not_operational_truth",
        "note": "OTIF remains durable counts only; finding stays on commercial path.",
    }
    record["routing"] = routing
    ok, code = advance_state(
        record, LS_OT_ROUTED, reason="route_operational_truth_v1"
    )
    diag = dict(record.get("diagnostics") or {})
    diag["routed_operational_truth"] = True
    diag["routed"] = bool(
        diag.get("routed_knowledge") and diag.get("routed_guidance")
    )
    diag["stopped_at"] = record.get("lifecycle_state")
    if not ok:
        diag["route_ot_error"] = code
    record["diagnostics"] = diag
    return record


def route_surface_eligible_v1(record: dict[str, Any]) -> dict[str, Any]:
    """Mark surface destinations for composition/Home consumption."""
    routing = dict(record.get("routing") or {})
    home_eligible = bool(record.get("home_eligible"))
    auth = str(record.get("authoritative_surface") or "merchant_home")
    destinations = ["merchant_home"]
    if auth and auth not in destinations:
        destinations.append(auth)
    # Decision workspace may consume commercial findings later via SCF.
    if home_eligible:
        destinations.append("decision_workspace")
    routing["surface"] = {
        "eligible": home_eligible,
        "destinations": destinations,
        "authoritative_surface": auth,
    }
    record["routing"] = routing
    if home_eligible:
        record["visibility_state"] = VIS_ELIGIBLE
    else:
        record["visibility_state"] = VIS_SUPPRESSED
    ok, code = advance_state(
        record, LS_SURFACE_ELIGIBLE, reason="route_surface_eligible_v1"
    )
    diag = dict(record.get("diagnostics") or {})
    diag["surface_eligible"] = bool(home_eligible)
    diag["stopped_at"] = record.get("lifecycle_state")
    if not ok:
        diag["route_surface_error"] = code
    record["diagnostics"] = diag
    return record


__all__ = [
    "route_knowledge_v1",
    "route_guidance_v1",
    "route_operational_truth_v1",
    "route_surface_eligible_v1",
]
