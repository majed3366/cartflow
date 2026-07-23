# -*- coding: utf-8 -*-
"""
Evidence Truth record with constitutional metadata — WP-ET-05.

Wraps the kernel EvidenceEnvelopeV1 and requires governance fields that
no Evidence Truth object may omit (Truth Before Consumption).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from services.evidence_truth.evidence_governance_v1 import (
    ELIGIBILITY_NOT_CONSUMABLE,
    ELIGIBILITY_SHADOW_ONLY,
    EVIDENCE_ACCOUNTING_RECORDED,
    EVIDENCE_ACCOUNTING_STATUS_V1,
    EVIDENCE_GOVERNANCE_VERSION,
    EVIDENCE_LIFECYCLE_STATES_V1,
    EVIDENCE_OBSERVABILITY_OPS_VISIBLE,
    EVIDENCE_OBSERVABILITY_STATUS_V1,
    LIFECYCLE_CONSUMABLE,
    LIFECYCLE_ELIGIBLE,
    TIMESTAMP_AUTHORITIES_V1,
)
from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_GRADES_V1,
    READINESS_STATES_V1,
    REJECT_MISSING_SOURCES,
    REJECT_OWNER_MISSING,
    REJECT_SCHEMA_INVALID,
    EvidenceEnvelopeV1,
    EvidenceValidationError,
)
from services.evidence_truth.ownership_v1 import owner_for_family
from services.evidence_truth.validation_v1 import validate_evidence_envelope_v1


@dataclass(frozen=True)
class EvidenceTruthRecordV1:
    """
    Governed Evidence Truth object (Architecture Evidence stage).

    Constitutional fields are first-class; envelope carries the normative
    §2.0 shape. Consumption is never authorized by this package alone.
    """

    envelope: EvidenceEnvelopeV1
    owner: str
    canonical_family: str
    source_observations: tuple[str, ...]
    timestamp_authority: str
    accounting_identity: str
    accounting_status: str
    observability_identity: str
    observability_status: str
    eligibility: str
    lifecycle_state: str
    governance_version: int = EVIDENCE_GOVERNANCE_VERSION
    consumable: bool = False
    payload_notes: Mapping[str, Any] = field(default_factory=dict)

    @property
    def evidence_id(self) -> str:
        return self.envelope.evidence_id

    @property
    def evidence_version(self) -> int:
        return int(self.envelope.evidence_version)

    @property
    def evidence_family(self) -> str:
        return self.envelope.evidence_family

    @property
    def evidence_type(self) -> str:
        return self.envelope.evidence_type

    @property
    def readiness(self) -> str:
        return self.envelope.readiness

    @property
    def confidence(self) -> str:
        return self.envelope.confidence

    @property
    def version(self) -> int:
        """Published evidence_version (Architecture versioning)."""
        return self.evidence_version

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "canonical_family": self.canonical_family,
            "source_observations": list(self.source_observations),
            "timestamp_authority": self.timestamp_authority,
            "confidence": self.confidence,
            "readiness": self.readiness,
            "accounting_identity": self.accounting_identity,
            "accounting_status": self.accounting_status,
            "observability_identity": self.observability_identity,
            "observability_status": self.observability_status,
            "eligibility": self.eligibility,
            "version": self.version,
            "governance_version": self.governance_version,
            "lifecycle_state": self.lifecycle_state,
            "consumable": self.consumable,
            "envelope": self.envelope.to_dict(),
            "payload_notes": dict(self.payload_notes or {}),
        }


def validate_evidence_constitutional_metadata_v1(record: EvidenceTruthRecordV1) -> None:
    """Fail closed: no Evidence Truth object without complete constitutional metadata."""
    if not (record.owner or "").strip():
        raise EvidenceValidationError(REJECT_OWNER_MISSING, "evidence_owner_required")
    expected = owner_for_family(record.canonical_family) or ""
    if expected and record.owner != expected:
        raise EvidenceValidationError(
            REJECT_OWNER_MISSING,
            f"owner_mismatch:got={record.owner!r} expected={expected!r}",
        )
    if not (record.canonical_family or "").strip():
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "canonical_family_required"
        )
    if record.canonical_family != record.envelope.evidence_family:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "canonical_family_must_match_envelope_family",
        )
    if not record.source_observations:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES, "source_observations_required"
        )
    for idx, oid in enumerate(record.source_observations):
        if not (oid or "").strip():
            raise EvidenceValidationError(
                REJECT_MISSING_SOURCES, f"source_observations[{idx}]_empty"
            )
    if record.timestamp_authority not in TIMESTAMP_AUTHORITIES_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_timestamp_authority:{record.timestamp_authority!r}",
        )
    if record.envelope.confidence not in CONFIDENCE_GRADES_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, f"invalid_confidence:{record.envelope.confidence!r}"
        )
    if record.envelope.readiness not in READINESS_STATES_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, f"invalid_readiness:{record.envelope.readiness!r}"
        )
    if not (record.accounting_identity or "").strip():
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "accounting_identity_required"
        )
    if record.accounting_status not in EVIDENCE_ACCOUNTING_STATUS_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_accounting_status:{record.accounting_status!r}",
        )
    if not (record.observability_identity or "").strip():
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "observability_identity_required"
        )
    if record.observability_status not in EVIDENCE_OBSERVABILITY_STATUS_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_observability_status:{record.observability_status!r}",
        )
    if not (record.eligibility or "").strip():
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "eligibility_required")
    if int(record.governance_version or 0) < 1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "governance_version_must_be_positive"
        )
    if int(record.envelope.evidence_version or 0) < 1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "evidence_version_must_be_positive"
        )
    if record.lifecycle_state not in EVIDENCE_LIFECYCLE_STATES_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_lifecycle_state:{record.lifecycle_state!r}",
        )
    # WP-ET-05: consumption never authorized
    if record.consumable or record.lifecycle_state == LIFECYCLE_CONSUMABLE:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "consumable_lifecycle_forbidden_until_consumer_cutover",
        )
    if record.eligibility not in {ELIGIBILITY_NOT_CONSUMABLE, ELIGIBILITY_SHADOW_ONLY}:
        # Allow readiness-qualified shadow eligibility strings only
        if not record.eligibility.startswith("shadow_"):
            raise EvidenceValidationError(
                REJECT_SCHEMA_INVALID,
                f"invalid_eligibility:{record.eligibility!r}",
            )

    env_result = validate_evidence_envelope_v1(record.envelope)
    env_result.raise_if_invalid()


def build_accounting_identity_v1(*, evidence_id: str, evidence_version: int) -> str:
    return f"acct:ev:{evidence_id}:v{int(evidence_version)}"


def build_observability_identity_v1(*, evidence_id: str, evidence_version: int) -> str:
    return f"ops:ev:{evidence_id}:v{int(evidence_version)}"


def evidence_governance_defaults_v1(
    *,
    evidence_id: str,
    evidence_version: int,
    lifecycle_state: str = LIFECYCLE_ELIGIBLE,
) -> dict[str, Any]:
    """Default constitutional stamps after successful publish + stamp."""
    return {
        "governance_version": EVIDENCE_GOVERNANCE_VERSION,
        "accounting_identity": build_accounting_identity_v1(
            evidence_id=evidence_id, evidence_version=evidence_version
        ),
        "accounting_status": EVIDENCE_ACCOUNTING_RECORDED,
        "observability_identity": build_observability_identity_v1(
            evidence_id=evidence_id, evidence_version=evidence_version
        ),
        "observability_status": EVIDENCE_OBSERVABILITY_OPS_VISIBLE,
        "eligibility": ELIGIBILITY_SHADOW_ONLY,
        "lifecycle_state": lifecycle_state,
        "consumable": False,
    }
