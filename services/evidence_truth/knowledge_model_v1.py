# -*- coding: utf-8 -*-
"""
Knowledge Record DTO — WP-ET-10 (C-18 shadow foundation).

Pattern / understanding states only. No Findings, Guidance, or merchant speech.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from services.evidence_truth.kernel_v1 import (
    FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1,
    EvidenceValidationError,
    REJECT_MISSING_SOURCES,
    REJECT_SCHEMA_INVALID,
)

KNOWLEDGE_SCHEMA_VERSION_V1 = "knowledge_record_v1"
KNOWLEDGE_GOVERNANCE_VERSION = 1
KNOWLEDGE_COMPOSER_OWNER = "knowledge_composer"

KNOWLEDGE_LIFECYCLE_SHADOW = "shadow_composed"
KNOWLEDGE_ELIGIBILITY_SHADOW_ONLY = "shadow_only"

# Pattern kinds allowed in WP-ET-10 (no commercial meaning).
KNOWLEDGE_TYPE_FAMILY_PRESENCE = "family_presence_pattern_v1"
KNOWLEDGE_TYPE_READY_FAMILY_SET = "ready_family_set_pattern_v1"

KNOWLEDGE_TYPES_V1: frozenset[str] = frozenset(
    {
        KNOWLEDGE_TYPE_FAMILY_PRESENCE,
        KNOWLEDGE_TYPE_READY_FAMILY_SET,
    }
)

# Additional forbidden intelligence / Findings keys on Knowledge payloads
FORBIDDEN_KNOWLEDGE_PAYLOAD_KEYS_V1: frozenset[str] = FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1 | frozenset(
    {
        "finding_id",
        "business_meaning",
        "opportunity_rank",
        "recommended_action",
        "merchant_priority",
        "roi_estimate",
        "cause",
        "dominant_cause",
        "why",
        "because",
        "should",
        "intervention",
    }
)


@dataclass(frozen=True)
class KnowledgeBundleRefV1:
    """Traceable pointer Knowledge → Evidence Bundle."""

    bundle_id: str
    bundle_version: int
    store_slug: str
    schema_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "bundle_version": int(self.bundle_version),
            "store_slug": self.store_slug,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class KnowledgeEvidenceRefV1:
    """Traceable pointer Knowledge → Evidence Truth (via Bundle)."""

    evidence_id: str
    evidence_version: int
    family: str
    readiness: str
    confidence: str
    bundle_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_version": int(self.evidence_version),
            "family": self.family,
            "readiness": self.readiness,
            "confidence": self.confidence,
            "bundle_id": self.bundle_id,
        }


@dataclass(frozen=True)
class KnowledgeClaimRefV1:
    """
    BK-3: every Knowledge claim carries Evidence identity.

    Claims are pattern assertions, not commercial findings.
    """

    claim_id: str
    claim_kind: str
    evidence_ids: tuple[str, ...]
    bundle_ids: tuple[str, ...]
    readiness: str
    confidence: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_kind": self.claim_kind,
            "evidence_ids": list(self.evidence_ids),
            "bundle_ids": list(self.bundle_ids),
            "readiness": self.readiness,
            "confidence": self.confidence,
            "payload": dict(self.payload or {}),
        }


@dataclass(frozen=True)
class KnowledgeRecordV1:
    """
    Governed Knowledge Record (pattern layer).

    Consumes Evidence Bundle only. Never Consumable for Findings/UI in WP-ET-10.
    """

    knowledge_id: str
    knowledge_version: int
    knowledge_type: str
    schema_version: str
    store_slug: str
    window_start: str
    window_end: Optional[str]
    as_of: str
    composer_owner: str
    bundle_refs: tuple[KnowledgeBundleRefV1, ...]
    evidence_refs: tuple[KnowledgeEvidenceRefV1, ...]
    claims: tuple[KnowledgeClaimRefV1, ...]
    readiness: str
    confidence: str
    pattern_summary: Mapping[str, Any]
    provenance: str
    governance_version: int = KNOWLEDGE_GOVERNANCE_VERSION
    eligibility: str = KNOWLEDGE_ELIGIBILITY_SHADOW_ONLY
    lifecycle_state: str = KNOWLEDGE_LIFECYCLE_SHADOW
    consumable: bool = False
    composition_notes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_version": int(self.knowledge_version),
            "knowledge_type": self.knowledge_type,
            "schema_version": self.schema_version,
            "store_slug": self.store_slug,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "as_of": self.as_of,
            "composer_owner": self.composer_owner,
            "bundle_refs": [r.to_dict() for r in self.bundle_refs],
            "evidence_refs": [r.to_dict() for r in self.evidence_refs],
            "claims": [c.to_dict() for c in self.claims],
            "readiness": self.readiness,
            "confidence": self.confidence,
            "pattern_summary": dict(self.pattern_summary or {}),
            "provenance": self.provenance,
            "governance_version": int(self.governance_version),
            "eligibility": self.eligibility,
            "lifecycle_state": self.lifecycle_state,
            "consumable": bool(self.consumable),
            "composition_notes": dict(self.composition_notes or {}),
        }


def validate_knowledge_record_constitutional_v1(record: KnowledgeRecordV1) -> None:
    """Fail closed: Knowledge must remain Bundle-backed pattern composition."""
    if not (record.knowledge_id or "").strip():
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "knowledge_id_required")
    if record.schema_version != KNOWLEDGE_SCHEMA_VERSION_V1:
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "knowledge_schema_version")
    if record.knowledge_type not in KNOWLEDGE_TYPES_V1:
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "unknown_knowledge_type")
    if record.composer_owner != KNOWLEDGE_COMPOSER_OWNER:
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "knowledge_composer_owner")
    if record.consumable or record.lifecycle_state != KNOWLEDGE_LIFECYCLE_SHADOW:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "knowledge_consumable_forbidden_until_consumer_cutover",
        )
    if not record.bundle_refs:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES, "knowledge_requires_bundle_ref"
        )
    if not record.evidence_refs:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES, "knowledge_requires_evidence_refs"
        )
    if not record.claims:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES, "knowledge_requires_claims"
        )
    for claim in record.claims:
        if not claim.evidence_ids:
            raise EvidenceValidationError(
                REJECT_MISSING_SOURCES,
                f"claim_missing_evidence_id:{claim.claim_id}",
            )
        for key in (claim.payload or {}):
            if key in FORBIDDEN_KNOWLEDGE_PAYLOAD_KEYS_V1:
                raise EvidenceValidationError(
                    REJECT_SCHEMA_INVALID,
                    f"knowledge_forbidden_key:{claim.claim_id}:{key}",
                )
    for key in (record.pattern_summary or {}):
        if key in FORBIDDEN_KNOWLEDGE_PAYLOAD_KEYS_V1:
            raise EvidenceValidationError(
                REJECT_SCHEMA_INVALID,
                f"knowledge_forbidden_summary_key:{key}",
            )
