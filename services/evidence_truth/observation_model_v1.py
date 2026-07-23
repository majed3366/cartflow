# -*- coding: utf-8 -*-
"""
Canonical Observation record (Architecture Observation stage / C-07 output).

WP-ET-04: every Observation must carry constitutional governance metadata.
Observations are NOT Evidence — readiness/confidence remain Unknown until
a Family Authority publishes Evidence (Architecture §1.3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_GRADES_V1,
    CONFIDENCE_UNKNOWN,
    READINESS_STATES_V1,
    READINESS_UNKNOWN,
    REJECT_OWNER_MISSING,
    REJECT_SCHEMA_INVALID,
    EvidenceValidationError,
)
from services.evidence_truth.observation_types_v1 import (
    OBS_ACCOUNTING_PENDING,
    OBS_ACCOUNTING_RECORDED,
    OBS_ACCOUNTING_REJECTED,
    OBS_OBSERVABILITY_HIDDEN,
    OBS_OBSERVABILITY_OPS_VISIBLE,
    OBSERVATION_GOVERNANCE_VERSION,
    TIMESTAMP_AUTHORITY_PLATFORM_QTC,
    TIMESTAMP_AUTHORITY_WALL_CLOCK_UTC,
)

_ACCOUNTING_STATUS_V1 = frozenset(
    {OBS_ACCOUNTING_RECORDED, OBS_ACCOUNTING_REJECTED, OBS_ACCOUNTING_PENDING}
)
_OBSERVABILITY_STATUS_V1 = frozenset(
    {OBS_OBSERVABILITY_OPS_VISIBLE, OBS_OBSERVABILITY_HIDDEN}
)
_TIMESTAMP_AUTHORITIES_V1 = frozenset(
    {TIMESTAMP_AUTHORITY_WALL_CLOCK_UTC, TIMESTAMP_AUTHORITY_PLATFORM_QTC}
)


@dataclass(frozen=True)
class CanonicalObservationV1:
    """
    Provider-neutral observation with constitutional metadata (WP-ET-04).

    Answers: we observed X at T for subject S on store S — with ownership
    and governance stamps. Does not assert Evidence Ready for findings.
    """

    observation_id: str
    observation_type: str
    store_slug: str
    subject: str
    observed_at: str
    source_channel: str
    raw_kind: str
    raw_ref: str
    # Constitutional metadata (required)
    owner: str
    canonical_family: str
    timestamp_authority: str
    version: int
    confidence_state: str
    readiness_state: str
    accounting_status: str
    observability_status: str
    # Optional / provenance
    provider: str = ""
    canonical_store_id: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)
    provenance: str = "shadow_dual_write"
    schema_version: str = "canonical_observation_v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "observation_type": self.observation_type,
            "store_slug": self.store_slug,
            "subject": self.subject,
            "observed_at": self.observed_at,
            "source_channel": self.source_channel,
            "raw_kind": self.raw_kind,
            "raw_ref": self.raw_ref,
            "owner": self.owner,
            "canonical_family": self.canonical_family,
            "timestamp_authority": self.timestamp_authority,
            "version": self.version,
            "confidence_state": self.confidence_state,
            "readiness_state": self.readiness_state,
            "accounting_status": self.accounting_status,
            "observability_status": self.observability_status,
            "provider": self.provider,
            "canonical_store_id": self.canonical_store_id,
            "payload": dict(self.payload or {}),
            "provenance": self.provenance,
            "schema_version": self.schema_version,
        }


def validate_observation_constitutional_metadata_v1(
    observation: CanonicalObservationV1,
) -> None:
    """
    Fail closed: no Observation may exist without constitutional metadata.

    Observation readiness/confidence must remain Unknown (not Evidence Ready).
    """
    if not (observation.owner or "").strip():
        raise EvidenceValidationError(REJECT_OWNER_MISSING, "observation_owner_required")
    if not (observation.canonical_family or "").strip():
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "observation_canonical_family_required"
        )
    if observation.timestamp_authority not in _TIMESTAMP_AUTHORITIES_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_timestamp_authority:{observation.timestamp_authority!r}",
        )
    if int(observation.version or 0) < 1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "observation_version_must_be_positive"
        )
    if observation.confidence_state not in CONFIDENCE_GRADES_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_confidence_state:{observation.confidence_state!r}",
        )
    if observation.readiness_state not in READINESS_STATES_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_readiness_state:{observation.readiness_state!r}",
        )
    # Architecture: Observation does not assert Evidence Ready for findings
    if observation.readiness_state not in {READINESS_UNKNOWN}:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "observation_readiness_must_be_unknown_until_evidence_publish",
        )
    if observation.confidence_state not in {CONFIDENCE_UNKNOWN}:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "observation_confidence_must_be_unknown_until_evidence_publish",
        )
    if observation.accounting_status not in _ACCOUNTING_STATUS_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_accounting_status:{observation.accounting_status!r}",
        )
    if observation.observability_status not in _OBSERVABILITY_STATUS_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            f"invalid_observability_status:{observation.observability_status!r}",
        )


def observation_governance_defaults_v1() -> dict[str, Any]:
    """Default constitutional stamps for newly produced Observations."""
    return {
        "version": OBSERVATION_GOVERNANCE_VERSION,
        "timestamp_authority": TIMESTAMP_AUTHORITY_WALL_CLOCK_UTC,
        "confidence_state": CONFIDENCE_UNKNOWN,
        "readiness_state": READINESS_UNKNOWN,
        "accounting_status": OBS_ACCOUNTING_PENDING,
        "observability_status": OBS_OBSERVABILITY_OPS_VISIBLE,
    }
