# -*- coding: utf-8 -*-
"""
Evidence Bundle DTO — WP-ET-09 (C-16).

Composition layer only. No Knowledge, Findings, Guidance, or merchant speech.
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

BUNDLE_SCHEMA_VERSION_V1 = "evidence_bundle_v1"
BUNDLE_GOVERNANCE_VERSION = 1
BUNDLE_COMPOSER_OWNER = "evidence_bundle_composer"

# Bundle lifecycle: shadow composition never authorizes consumption.
BUNDLE_LIFECYCLE_SHADOW = "shadow_composed"
BUNDLE_ELIGIBILITY_SHADOW_ONLY = "shadow_only"
BUNDLE_ELIGIBILITY_NOT_CONSUMABLE = "not_consumable"


@dataclass(frozen=True)
class BundleEvidenceRefV1:
    """Traceable pointer from Bundle → Evidence Truth (+ Observation ids)."""

    evidence_id: str
    evidence_version: int
    family: str
    evidence_type: str
    owner: str
    readiness: str
    confidence: str
    source_observations: tuple[str, ...]
    observation_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_version": int(self.evidence_version),
            "family": self.family,
            "evidence_type": self.evidence_type,
            "owner": self.owner,
            "readiness": self.readiness,
            "confidence": self.confidence,
            "source_observations": list(self.source_observations),
            "observation_refs": list(self.observation_refs),
        }


@dataclass(frozen=True)
class BundleFamilySliceV1:
    """
    Per-family projection. Missing Evidence → Unavailable/Unknown honesty
    (EB-2 no zero-fill). Never invents facts.
    """

    family: str
    present: bool
    has_ready: bool
    readiness: str
    confidence: str
    owner: str
    evidence_ref: Optional[BundleEvidenceRefV1]
    projected_facts: Mapping[str, Any] = field(default_factory=dict)
    notes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "present": bool(self.present),
            "has_ready": bool(self.has_ready),
            "readiness": self.readiness,
            "confidence": self.confidence,
            "owner": self.owner,
            "evidence_ref": self.evidence_ref.to_dict() if self.evidence_ref else None,
            "projected_facts": dict(self.projected_facts or {}),
            "notes": dict(self.notes or {}),
        }


@dataclass(frozen=True)
class EvidenceBundleRecordV1:
    """
    Governed Evidence Bundle (projection only).

    Reconstructable from Evidence Truth refs. consumable always False in WP-ET-09.
    """

    bundle_id: str
    bundle_version: int
    schema_version: str
    store_slug: str
    window_start: str
    window_end: Optional[str]
    as_of: str
    composer_owner: str
    families: Mapping[str, BundleFamilySliceV1]
    evidence_refs: tuple[BundleEvidenceRefV1, ...]
    # Visitor honesty fields (KF-3 / EB-3) — never zero-fill
    has_visitor_truth: bool
    visitor_total: Optional[Any]
    visitor_bundle_fields_authorized: bool
    readiness_summary: Mapping[str, str]
    provenance: str
    governance_version: int = BUNDLE_GOVERNANCE_VERSION
    eligibility: str = BUNDLE_ELIGIBILITY_SHADOW_ONLY
    lifecycle_state: str = BUNDLE_LIFECYCLE_SHADOW
    consumable: bool = False
    composition_notes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "bundle_version": int(self.bundle_version),
            "schema_version": self.schema_version,
            "store_slug": self.store_slug,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "as_of": self.as_of,
            "composer_owner": self.composer_owner,
            "families": {k: v.to_dict() for k, v in (self.families or {}).items()},
            "evidence_refs": [r.to_dict() for r in self.evidence_refs],
            "has_visitor_truth": bool(self.has_visitor_truth),
            "visitor_total": self.visitor_total,
            "visitor_bundle_fields_authorized": bool(
                self.visitor_bundle_fields_authorized
            ),
            "readiness_summary": dict(self.readiness_summary or {}),
            "provenance": self.provenance,
            "governance_version": int(self.governance_version),
            "eligibility": self.eligibility,
            "lifecycle_state": self.lifecycle_state,
            "consumable": bool(self.consumable),
            "composition_notes": dict(self.composition_notes or {}),
        }


def validate_evidence_bundle_constitutional_v1(bundle: EvidenceBundleRecordV1) -> None:
    """Fail closed: Bundle must remain a pure, traceable composition."""
    if not (bundle.bundle_id or "").strip():
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "bundle_id_required")
    if bundle.schema_version != BUNDLE_SCHEMA_VERSION_V1:
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "bundle_schema_version")
    if bundle.composer_owner != BUNDLE_COMPOSER_OWNER:
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "bundle_composer_owner")
    if bundle.consumable or bundle.lifecycle_state not in {
        BUNDLE_LIFECYCLE_SHADOW,
    }:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "bundle_consumable_forbidden_until_consumer_cutover",
        )
    if not bundle.evidence_refs:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES,
            "bundle_requires_at_least_one_evidence_ref",
        )
    for ref in bundle.evidence_refs:
        if not (ref.evidence_id or "").strip():
            raise EvidenceValidationError(
                REJECT_MISSING_SOURCES, "evidence_ref_missing_id"
            )
        if not ref.source_observations and not ref.observation_refs:
            raise EvidenceValidationError(
                REJECT_MISSING_SOURCES,
                f"evidence_ref_missing_observation_trace:{ref.evidence_id}",
            )
    for fam, slice_ in (bundle.families or {}).items():
        for key in (slice_.projected_facts or {}):
            if key in FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1:
                raise EvidenceValidationError(
                    REJECT_SCHEMA_INVALID,
                    f"bundle_forbidden_guidance_key:{fam}:{key}",
                )
    # EB-2 / KF-3: visitor_total must not be zero-filled when truth absent
    if not bundle.has_visitor_truth and bundle.visitor_total is not None:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "visitor_total_forbidden_without_has_visitor_truth",
        )
    if not bundle.visitor_bundle_fields_authorized and bundle.has_visitor_truth:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "has_visitor_truth_requires_visitor_bundle_fields_authorization",
        )
