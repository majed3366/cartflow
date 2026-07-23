# -*- coding: utf-8 -*-
"""
Evidence contract validation framework (WP-ET-00).

Validates envelopes against kernel + family/type/ownership registries.
Does not publish, persist, or wire into consumers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from services.evidence_truth.families_v1 import get_evidence_family
from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_GRADES_V1,
    EVIDENCE_KERNEL_SCHEMA_VERSION,
    FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1,
    READINESS_CONFLICTING,
    READINESS_INSUFFICIENT,
    READINESS_READY,
    READINESS_STATES_V1,
    READINESS_TRUSTED,
    READINESS_UNAVAILABLE,
    READINESS_UNKNOWN,
    REJECT_GUIDANCE_FIELD_FORBIDDEN,
    REJECT_MISSING_SOURCES,
    REJECT_OWNER_MISSING,
    REJECT_SCHEMA_INVALID,
    REJECT_UNKNOWN_TYPE,
    EvidenceEnvelopeV1,
    EvidenceValidationError,
)
from services.evidence_truth.ownership_v1 import owner_for_family
from services.evidence_truth.type_registry_v1 import get_evidence_type

# Architecture §6.1 allowed readiness transitions (from → frozenset[to])
_READINESS_TRANSITIONS_V1: dict[str, frozenset[str]] = {
    READINESS_UNKNOWN: frozenset(
        {
            READINESS_UNAVAILABLE,
            READINESS_INSUFFICIENT,
            READINESS_CONFLICTING,
            READINESS_READY,
        }
    ),
    READINESS_UNAVAILABLE: frozenset({READINESS_READY, READINESS_INSUFFICIENT}),
    READINESS_INSUFFICIENT: frozenset({READINESS_READY, READINESS_CONFLICTING}),
    READINESS_CONFLICTING: frozenset({READINESS_READY, READINESS_TRUSTED}),
    READINESS_READY: frozenset({READINESS_TRUSTED}),
    READINESS_TRUSTED: frozenset(),  # only via new evidence_version (supersession)
}


@dataclass
class EvidenceValidationResultV1:
    ok: bool
    errors: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.ok:
            code = self.reason_codes[0] if self.reason_codes else REJECT_SCHEMA_INVALID
            raise EvidenceValidationError(code, "; ".join(self.errors))


def validate_readiness_transition_v1(from_state: str, to_state: str) -> EvidenceValidationResultV1:
    """Validate a readiness transition on a new evidence_version path."""
    errors: list[str] = []
    codes: list[str] = []
    src = (from_state or "").strip().lower()
    dst = (to_state or "").strip().lower()
    if src not in READINESS_STATES_V1:
        errors.append(f"invalid_from_readiness:{from_state!r}")
        codes.append(REJECT_SCHEMA_INVALID)
    if dst not in READINESS_STATES_V1:
        errors.append(f"invalid_to_readiness:{to_state!r}")
        codes.append(REJECT_SCHEMA_INVALID)
    if errors:
        return EvidenceValidationResultV1(ok=False, errors=errors, reason_codes=codes)
    allowed = _READINESS_TRANSITIONS_V1.get(src, frozenset())
    if dst not in allowed:
        # Same-state is not a transition; supersession may re-emit same readiness.
        if src == dst:
            return EvidenceValidationResultV1(ok=True)
        errors.append(f"forbidden_readiness_transition:{src}->{dst}")
        codes.append(REJECT_SCHEMA_INVALID)
        return EvidenceValidationResultV1(ok=False, errors=errors, reason_codes=codes)
    return EvidenceValidationResultV1(ok=True)


def validate_evidence_envelope_v1(
    envelope: EvidenceEnvelopeV1,
    *,
    require_registered_type: bool = True,
) -> EvidenceValidationResultV1:
    """
    OE-oriented structural validation for an EvidenceEnvelopeV1.

    Does not perform eligibility/freshness stamping (C-03 — later WP).
    """
    errors: list[str] = []
    codes: list[str] = []

    def fail(code: str, msg: str) -> None:
        errors.append(msg)
        if code not in codes:
            codes.append(code)

    if not get_evidence_family(envelope.evidence_family):
        fail(REJECT_UNKNOWN_TYPE, f"unknown_family:{envelope.evidence_family!r}")

    type_entry = get_evidence_type(envelope.evidence_family, envelope.evidence_type)
    if require_registered_type and type_entry is None:
        fail(
            REJECT_UNKNOWN_TYPE,
            f"unknown_type:{envelope.evidence_family!r}:{envelope.evidence_type!r}",
        )

    owner = owner_for_family(envelope.evidence_family)
    if get_evidence_family(envelope.evidence_family) and not owner:
        fail(REJECT_OWNER_MISSING, f"owner_missing:{envelope.evidence_family!r}")
    if type_entry is not None and type_entry.owner_module and owner:
        if type_entry.owner_module != owner:
            fail(
                REJECT_OWNER_MISSING,
                f"owner_mismatch:type={type_entry.owner_module} family={owner}",
            )

    if not (envelope.evidence_id or "").strip():
        fail(REJECT_SCHEMA_INVALID, "evidence_id_required")
    if int(envelope.evidence_version or 0) < 1:
        fail(REJECT_SCHEMA_INVALID, "evidence_version_must_be_positive")
    if not (envelope.store_slug or "").strip():
        fail(REJECT_SCHEMA_INVALID, "store_slug_required")
    if not (envelope.subject or "").strip():
        fail(REJECT_SCHEMA_INVALID, "subject_required")
    if not (envelope.as_of or "").strip():
        fail(REJECT_SCHEMA_INVALID, "as_of_required")

    if envelope.readiness not in READINESS_STATES_V1:
        fail(REJECT_SCHEMA_INVALID, f"invalid_readiness:{envelope.readiness!r}")
    if envelope.confidence not in CONFIDENCE_GRADES_V1:
        fail(REJECT_SCHEMA_INVALID, f"invalid_confidence:{envelope.confidence!r}")

    if envelope.schema_version != EVIDENCE_KERNEL_SCHEMA_VERSION:
        # Spine allows only current kernel schema; later dual-read in migration.
        fail(
            REJECT_SCHEMA_INVALID,
            f"unsupported_schema_version:{envelope.schema_version!r}",
        )

    if not envelope.sources:
        fail(REJECT_MISSING_SOURCES, "sources_required")
    else:
        for idx, src in enumerate(envelope.sources):
            if not (src.observation_ref or "").strip():
                fail(REJECT_MISSING_SOURCES, f"sources[{idx}].observation_ref_required")

    if not (envelope.observed_period.start or "").strip():
        fail(REJECT_SCHEMA_INVALID, "observed_period.start_required")

    payload = dict(envelope.payload or {})
    forbidden = sorted(k for k in payload if k in FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1)
    if forbidden:
        fail(
            REJECT_GUIDANCE_FIELD_FORBIDDEN,
            f"forbidden_payload_keys:{','.join(forbidden)}",
        )

    if envelope.supersedes is not None:
        if int(envelope.supersedes) < 1:
            fail(REJECT_SCHEMA_INVALID, "supersedes_must_be_positive")
        if int(envelope.evidence_version) <= int(envelope.supersedes):
            fail(
                REJECT_SCHEMA_INVALID,
                "evidence_version_must_exceed_supersedes",
            )

    return EvidenceValidationResultV1(ok=not errors, errors=errors, reason_codes=codes)


def assert_valid_evidence_envelope_v1(envelope: EvidenceEnvelopeV1) -> None:
    validate_evidence_envelope_v1(envelope).raise_if_invalid()


def validate_observed_at_in_period_v1(
    observed_at: str,
    period_start: str,
    period_end: str | None = None,
) -> EvidenceValidationResultV1:
    """
    OE-2 structural helper: observation timestamp vs evidence observed_period.

    Lexicographic ISO-8601 comparison (callers must pass comparable stamps).
    No publisher wiring in WP-ET-01.
    """
    errors: list[str] = []
    codes: list[str] = []
    ts = (observed_at or "").strip()
    start = (period_start or "").strip()
    end = (period_end or "").strip() if period_end else ""
    if not ts:
        errors.append("observed_at_required")
        codes.append(REJECT_SCHEMA_INVALID)
    if not start:
        errors.append("period_start_required")
        codes.append(REJECT_SCHEMA_INVALID)
    if errors:
        return EvidenceValidationResultV1(ok=False, errors=errors, reason_codes=codes)
    if ts < start:
        return EvidenceValidationResultV1(
            ok=False,
            errors=[f"observed_at_before_period:{ts}<{start}"],
            reason_codes=[REJECT_SCHEMA_INVALID],
        )
    if end and ts >= end:
        return EvidenceValidationResultV1(
            ok=False,
            errors=[f"observed_at_outside_period:{ts}>={end}"],
            reason_codes=[REJECT_SCHEMA_INVALID],
        )
    return EvidenceValidationResultV1(ok=True)
