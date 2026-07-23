# -*- coding: utf-8 -*-
"""
C-03 Evidence Eligibility & Freshness Engine — WP-ET-04.

Readiness stamping library for Evidence candidates (Blueprint WP-ET-04).
Never fabricates Ready. Stale → Insufficient / Unavailable.
Family authorities (later WPs) call in; Composer reads stamps.

Does not publish Evidence. Does not activate consumers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Optional

from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_GRADES_V1,
    CONFIDENCE_INSUFFICIENT,
    CONFIDENCE_UNKNOWN,
    EvidenceEnvelopeV1,
    EvidenceFreshnessV1,
    READINESS_INSUFFICIENT,
    READINESS_READY,
    READINESS_STATES_V1,
    READINESS_TRUSTED,
    READINESS_UNAVAILABLE,
    READINESS_UNKNOWN,
    REJECT_SCHEMA_INVALID,
    EvidenceValidationError,
)
from services.evidence_truth.type_registry_v1 import get_evidence_type
from services.evidence_truth.validation_v1 import validate_readiness_transition_v1

# Family predicate: returns True if eligibility for Ready is met
FamilyEligibilityPredicate = Callable[["EvidenceStampCandidateV1"], bool]


@dataclass(frozen=True)
class EvidenceStampCandidateV1:
    """Input to C-03 before / while building an Evidence envelope."""

    evidence_family: str
    evidence_type: str
    store_slug: str
    subject: str
    observed_at: str
    as_of: str
    source_count: int = 1
    channel_available: bool = True
    prior_readiness: str = READINESS_UNKNOWN
    ttl_seconds: Optional[int] = None
    force_conflict: bool = False


@dataclass(frozen=True)
class EvidenceStampResultV1:
    readiness: str
    confidence: str
    freshness: EvidenceFreshnessV1
    transition_from: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness": self.readiness,
            "confidence": self.confidence,
            "freshness": self.freshness.to_dict(),
            "transition_from": self.transition_from,
            "notes": list(self.notes),
        }


def _parse_iso(ts: str) -> Optional[datetime]:
    raw = (ts or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_freshness_v1(
    *,
    observed_at: str,
    as_of: str | None = None,
    ttl_seconds: Optional[int] = None,
) -> EvidenceFreshnessV1:
    """Compute freshness stamp; does not invent readiness."""
    obs = _parse_iso(observed_at)
    asof = _parse_iso(as_of or "") or _utc_now()
    ttl = ttl_seconds
    stale_after = None
    is_stale = False
    if obs is not None and ttl is not None and int(ttl) >= 0:
        expire = obs + timedelta(seconds=int(ttl))
        stale_after = expire.replace(microsecond=0).isoformat()
        is_stale = asof >= expire
    return EvidenceFreshnessV1(
        observed_at=(observed_at or "").strip(),
        ttl_seconds=ttl,
        stale_after=stale_after,
        is_stale=is_stale,
    )


def _default_ready_predicate(candidate: EvidenceStampCandidateV1) -> bool:
    """
    Conservative default: Ready only with channel available, ≥1 source,
    identity present, and not forced conflict. Family WPs may replace.
    """
    if candidate.force_conflict:
        return False
    if not candidate.channel_available:
        return False
    if int(candidate.source_count or 0) < 1:
        return False
    if not (candidate.store_slug or "").strip() or not (candidate.subject or "").strip():
        return False
    return True


_FAMILY_PREDICATES: dict[str, FamilyEligibilityPredicate] = {}


def register_family_eligibility_predicate_v1(
    family: str, predicate: FamilyEligibilityPredicate
) -> None:
    """Family authorities register predicates (WP-ET-05+)."""
    key = (family or "").strip().lower()
    if not key:
        raise ValueError("family_required")
    _FAMILY_PREDICATES[key] = predicate


def clear_family_eligibility_predicates_v1() -> None:
    """Test helper."""
    _FAMILY_PREDICATES.clear()


def stamp_evidence_eligibility_v1(
    candidate: EvidenceStampCandidateV1,
    *,
    eligibility_predicate: FamilyEligibilityPredicate | None = None,
) -> EvidenceStampResultV1:
    """
    Apply C-03 rules → readiness + confidence + freshness.

    Never fabricates Ready when eligibility fails or data is stale.
    """
    notes: list[str] = []
    prior = (candidate.prior_readiness or READINESS_UNKNOWN).strip().lower()
    if prior not in READINESS_STATES_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, f"invalid_prior_readiness:{candidate.prior_readiness!r}"
        )

    ttl = candidate.ttl_seconds
    if ttl is None:
        type_entry = get_evidence_type(candidate.evidence_family, candidate.evidence_type)
        if type_entry is not None:
            ttl = type_entry.default_ttl_seconds

    freshness = compute_freshness_v1(
        observed_at=candidate.observed_at,
        as_of=candidate.as_of,
        ttl_seconds=ttl,
    )

    # Supersession / stale re-eval uses UNKNOWN as transition basis so we never
    # retain Ready when data is stale (Architecture: new evidence_version).
    transition_basis = prior

    if not candidate.channel_available:
        target = READINESS_UNAVAILABLE
        confidence = CONFIDENCE_UNKNOWN
        notes.append("channel_unavailable")
    elif candidate.force_conflict:
        target = "conflicting"
        confidence = CONFIDENCE_INSUFFICIENT
        notes.append("forced_conflict")
    elif freshness.is_stale:
        # Blueprint: stale → Insufficient / Unavailable (never Ready)
        target = READINESS_INSUFFICIENT
        confidence = CONFIDENCE_INSUFFICIENT
        notes.append("stale_insufficient")
        if prior in {READINESS_READY, READINESS_TRUSTED}:
            transition_basis = READINESS_UNKNOWN
            notes.append("supersession_basis_unknown_for_stale")
    else:
        pred = eligibility_predicate or _FAMILY_PREDICATES.get(
            (candidate.evidence_family or "").strip().lower()
        ) or _default_ready_predicate
        if pred(candidate):
            target = READINESS_READY
            confidence = "medium"
            notes.append("eligibility_passed")
        else:
            target = READINESS_INSUFFICIENT
            confidence = CONFIDENCE_INSUFFICIENT
            notes.append("eligibility_failed")

    # Trusted only via explicit reinforcement path (not default stamp)
    if target == READINESS_TRUSTED:
        target = READINESS_READY
        notes.append("trusted_demoted_without_reinforcement")

    transition = validate_readiness_transition_v1(transition_basis, target)
    if not transition.ok and transition_basis != target:
        # Same-state OK; illegal transitions fall back to Insufficient (fail closed)
        notes.append(f"transition_blocked:{transition_basis}->{target}")
        target = READINESS_INSUFFICIENT
        confidence = CONFIDENCE_INSUFFICIENT
        if target == READINESS_READY or target == READINESS_TRUSTED:
            target = READINESS_INSUFFICIENT
        # Never invent Ready on failure
        if prior in {READINESS_READY, READINESS_TRUSTED} and freshness.is_stale:
            target = READINESS_INSUFFICIENT
            confidence = CONFIDENCE_INSUFFICIENT
            notes.append("stale_forces_insufficient")

    if confidence not in CONFIDENCE_GRADES_V1:
        confidence = CONFIDENCE_UNKNOWN

    return EvidenceStampResultV1(
        readiness=target,
        confidence=confidence,
        freshness=freshness,
        transition_from=prior,
        notes=tuple(notes),
    )


def apply_stamp_to_envelope_v1(
    envelope: EvidenceEnvelopeV1,
    stamp: EvidenceStampResultV1,
) -> EvidenceEnvelopeV1:
    """Return a new envelope with C-03 stamps applied (immutable replace)."""
    return EvidenceEnvelopeV1(
        evidence_family=envelope.evidence_family,
        evidence_type=envelope.evidence_type,
        evidence_id=envelope.evidence_id,
        evidence_version=envelope.evidence_version,
        store_slug=envelope.store_slug,
        subject=envelope.subject,
        observed_period=envelope.observed_period,
        as_of=envelope.as_of,
        readiness=stamp.readiness,
        confidence=stamp.confidence,
        freshness=stamp.freshness,
        sources=envelope.sources,
        schema_version=envelope.schema_version,
        canonical_store_id=envelope.canonical_store_id,
        supersedes=envelope.supersedes,
        integrity=envelope.integrity,
        payload=envelope.payload,
        provenance=envelope.provenance,
    )


def assert_never_fabricate_ready_when_stale_v1(stamp: EvidenceStampResultV1) -> None:
    if stamp.freshness.is_stale and stamp.readiness in {READINESS_READY, READINESS_TRUSTED}:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "stale_must_not_be_ready"
        )
