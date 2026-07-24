# -*- coding: utf-8 -*-
"""Serialize/deserialize KnowledgeRecordV1 for durable shadow storage."""
from __future__ import annotations

from typing import Any, Mapping

from services.evidence_truth.knowledge_model_v1 import (
    KnowledgeBundleRefV1,
    KnowledgeClaimRefV1,
    KnowledgeEvidenceRefV1,
    KnowledgeRecordV1,
    validate_knowledge_record_constitutional_v1,
)


def knowledge_record_from_dict_v1(data: Mapping[str, Any]) -> KnowledgeRecordV1:
    """Rebuild KnowledgeRecordV1 from ``to_dict`` payload (fail closed)."""
    if not isinstance(data, Mapping):
        raise TypeError("knowledge_payload_must_be_mapping")
    bundle_refs = tuple(
        KnowledgeBundleRefV1(
            bundle_id=str(r.get("bundle_id") or ""),
            bundle_version=int(r.get("bundle_version") or 1),
            store_slug=str(r.get("store_slug") or ""),
            schema_version=str(r.get("schema_version") or ""),
        )
        for r in (data.get("bundle_refs") or [])
        if isinstance(r, Mapping)
    )
    evidence_refs = tuple(
        KnowledgeEvidenceRefV1(
            evidence_id=str(r.get("evidence_id") or ""),
            evidence_version=int(r.get("evidence_version") or 1),
            family=str(r.get("family") or ""),
            readiness=str(r.get("readiness") or ""),
            confidence=str(r.get("confidence") or ""),
            bundle_id=str(r.get("bundle_id") or ""),
        )
        for r in (data.get("evidence_refs") or [])
        if isinstance(r, Mapping)
    )
    claims = tuple(
        KnowledgeClaimRefV1(
            claim_id=str(c.get("claim_id") or ""),
            claim_kind=str(c.get("claim_kind") or ""),
            evidence_ids=tuple(str(x) for x in (c.get("evidence_ids") or [])),
            bundle_ids=tuple(str(x) for x in (c.get("bundle_ids") or [])),
            readiness=str(c.get("readiness") or ""),
            confidence=str(c.get("confidence") or ""),
            payload=dict(c.get("payload") or {})
            if isinstance(c.get("payload"), Mapping)
            else {},
        )
        for c in (data.get("claims") or [])
        if isinstance(c, Mapping)
    )
    rec = KnowledgeRecordV1(
        knowledge_id=str(data.get("knowledge_id") or ""),
        knowledge_version=int(data.get("knowledge_version") or 1),
        knowledge_type=str(data.get("knowledge_type") or ""),
        schema_version=str(data.get("schema_version") or ""),
        store_slug=str(data.get("store_slug") or ""),
        window_start=str(data.get("window_start") or ""),
        window_end=data.get("window_end"),
        as_of=str(data.get("as_of") or ""),
        composer_owner=str(data.get("composer_owner") or ""),
        bundle_refs=bundle_refs,
        evidence_refs=evidence_refs,
        claims=claims,
        readiness=str(data.get("readiness") or ""),
        confidence=str(data.get("confidence") or ""),
        pattern_summary=dict(data.get("pattern_summary") or {})
        if isinstance(data.get("pattern_summary"), Mapping)
        else {},
        provenance=str(data.get("provenance") or ""),
        governance_version=int(data.get("governance_version") or 1),
        eligibility=str(data.get("eligibility") or "shadow_only"),
        lifecycle_state=str(data.get("lifecycle_state") or "shadow_composed"),
        consumable=bool(data.get("consumable")),
        composition_notes=dict(data.get("composition_notes") or {})
        if isinstance(data.get("composition_notes"), Mapping)
        else {},
    )
    validate_knowledge_record_constitutional_v1(rec)
    return rec


__all__ = ["knowledge_record_from_dict_v1"]
