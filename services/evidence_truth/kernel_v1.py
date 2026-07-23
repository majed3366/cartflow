# -*- coding: utf-8 -*-
"""
C-01 Evidence Contract Kernel — shared vocabulary and envelope (WP-ET-00).

Library only. No persistence. No production publish path.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Optional

EVIDENCE_PLATFORM_VERSION = "evidence_truth_platform_v1"
EVIDENCE_KERNEL_SCHEMA_VERSION = "evidence_envelope_v1"

# Architecture §6 readiness vocabulary (platform-wide)
READINESS_UNKNOWN = "unknown"
READINESS_UNAVAILABLE = "unavailable"
READINESS_INSUFFICIENT = "insufficient"
READINESS_CONFLICTING = "conflicting"
READINESS_READY = "ready"
READINESS_TRUSTED = "trusted"

READINESS_STATES_V1: frozenset[str] = frozenset(
    {
        READINESS_UNKNOWN,
        READINESS_UNAVAILABLE,
        READINESS_INSUFFICIENT,
        READINESS_CONFLICTING,
        READINESS_READY,
        READINESS_TRUSTED,
    }
)

ReadinessState = str

# Proof of Value–compatible confidence grades
CONFIDENCE_CONFIRMED = "confirmed"
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_UNKNOWN = "unknown"
CONFIDENCE_INSUFFICIENT = "insufficient"

CONFIDENCE_GRADES_V1: frozenset[str] = frozenset(
    {
        CONFIDENCE_CONFIRMED,
        CONFIDENCE_HIGH,
        CONFIDENCE_MEDIUM,
        CONFIDENCE_LOW,
        CONFIDENCE_UNKNOWN,
        CONFIDENCE_INSUFFICIENT,
    }
)

ConfidenceGrade = str

# Blueprint §7.1 reject reason codes
REJECT_MISSING_SOURCES = "missing_sources"
REJECT_IDENTITY_MISMATCH = "identity_mismatch"
REJECT_UNKNOWN_TYPE = "unknown_type"
REJECT_SCHEMA_INVALID = "schema_invalid"
REJECT_DUPLICATE_SUPPRESSED = "duplicate_suppressed"
REJECT_CONFLICT_UNRESOLVED = "conflict_unresolved"
REJECT_STALE_FORBIDDEN_FOR_LIVE = "stale_forbidden_for_live"
REJECT_GUIDANCE_FIELD_FORBIDDEN = "guidance_field_forbidden"
REJECT_OWNER_MISSING = "owner_missing"

REJECT_REASON_CODES_V1: frozenset[str] = frozenset(
    {
        REJECT_MISSING_SOURCES,
        REJECT_IDENTITY_MISMATCH,
        REJECT_UNKNOWN_TYPE,
        REJECT_SCHEMA_INVALID,
        REJECT_DUPLICATE_SUPPRESSED,
        REJECT_CONFLICT_UNRESOLVED,
        REJECT_STALE_FORBIDDEN_FOR_LIVE,
        REJECT_GUIDANCE_FIELD_FORBIDDEN,
        REJECT_OWNER_MISSING,
    }
)

RejectReasonCode = str


class EvidenceValidationError(ValueError):
    """Envelope, registry, or transition failed contract validation."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


# Fields forbidden on Evidence records (Architecture ET-7 / §2.0)
FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1: frozenset[str] = frozenset(
    {
        "recommendation",
        "recommendation_text",
        "finding_title",
        "ui_label",
        "label_ar",
        "ranking_score",
        "priority",
        "ai_prompt",
        "eligible_surfaces",
        "routing_priority",
        "guidance",
        "merchant_action",
    }
)


@dataclass(frozen=True)
class ObservedPeriodV1:
    """Inclusive start / exclusive end, or point-in-time when end is None."""

    start: str
    end: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end}


@dataclass(frozen=True)
class EvidenceFreshnessV1:
    """Freshness metadata — readiness ≠ confidence ≠ freshness."""

    observed_at: str
    ttl_seconds: Optional[int] = None
    stale_after: Optional[str] = None
    is_stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceSourceRefV1:
    """Pointer to a Canonical Observation (or Raw ref during later WPs only)."""

    observation_ref: str
    channel: str = ""
    provider: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceEnvelopeV1:
    """
    Normative Evidence Truth record shape (Architecture §2.0).

    Immutable value object for validation and future publishers.
    WP-ET-00 does not persist or publish envelopes.
    """

    evidence_family: str
    evidence_type: str
    evidence_id: str
    evidence_version: int
    store_slug: str
    subject: str
    observed_period: ObservedPeriodV1
    as_of: str
    readiness: str
    confidence: str
    freshness: EvidenceFreshnessV1
    sources: tuple[EvidenceSourceRefV1, ...]
    schema_version: str = EVIDENCE_KERNEL_SCHEMA_VERSION
    canonical_store_id: str = ""
    supersedes: Optional[int] = None
    integrity: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)
    provenance: str = "unset"

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_family": self.evidence_family,
            "evidence_type": self.evidence_type,
            "evidence_id": self.evidence_id,
            "evidence_version": self.evidence_version,
            "canonical_store_id": self.canonical_store_id,
            "store_slug": self.store_slug,
            "subject": self.subject,
            "observed_period": self.observed_period.to_dict(),
            "as_of": self.as_of,
            "readiness": self.readiness,
            "confidence": self.confidence,
            "freshness": self.freshness.to_dict(),
            "sources": [s.to_dict() for s in self.sources],
            "schema_version": self.schema_version,
            "supersedes": self.supersedes,
            "integrity": self.integrity,
            "payload": dict(self.payload or {}),
            "provenance": self.provenance,
        }
