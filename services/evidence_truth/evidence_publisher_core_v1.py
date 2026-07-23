# -*- coding: utf-8 -*-
"""
Shared Evidence publish path — Observation → Evidence Truth (WP-ET-05).

Lifecycle: Produced → Accounted → Observable → Verified → Eligible.
Consumable is forbidden until a later consumer-cutover package.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from services.evidence_truth.accounting_v1 import (
    STAGE_EVIDENCE_OUT,
    get_evidence_accounting_ledger_v1,
)
from services.evidence_truth.eligibility_freshness_v1 import (
    EvidenceStampCandidateV1,
    apply_stamp_to_envelope_v1,
    stamp_evidence_eligibility_v1,
)
from services.evidence_truth.evidence_governance_v1 import LIFECYCLE_ELIGIBLE
from services.evidence_truth.evidence_model_v1 import (
    EvidenceTruthRecordV1,
    evidence_governance_defaults_v1,
    validate_evidence_constitutional_metadata_v1,
)
from services.evidence_truth.evidence_store_v1 import get_evidence_truth_store_v1
from services.evidence_truth.kernel_v1 import (
    EvidenceEnvelopeV1,
    EvidenceFreshnessV1,
    EvidenceSourceRefV1,
    EvidenceValidationError,
    ObservedPeriodV1,
    READINESS_READY,
)
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1
from services.evidence_truth.observation_types_v1 import TIMESTAMP_AUTHORITY_WALL_CLOCK_UTC
from services.evidence_truth.ownership_v1 import owner_for_family
from services.evidence_truth.type_registry_v1 import require_evidence_type_for_publish_v1
from services.evidence_truth.versioning_v1 import (
    build_evidence_id_v1,
    content_integrity_hash_v1,
    next_evidence_version_v1,
)

FamilyPayloadBuilder = Callable[[CanonicalObservationV1], dict[str, Any]]
FamilyEligibilityPredicate = Callable[[EvidenceStampCandidateV1], bool]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _replace_envelope(
    envelope: EvidenceEnvelopeV1,
    *,
    confidence: str | None = None,
    integrity: str | None = None,
) -> EvidenceEnvelopeV1:
    return EvidenceEnvelopeV1(
        evidence_family=envelope.evidence_family,
        evidence_type=envelope.evidence_type,
        evidence_id=envelope.evidence_id,
        evidence_version=envelope.evidence_version,
        store_slug=envelope.store_slug,
        subject=envelope.subject,
        observed_period=envelope.observed_period,
        as_of=envelope.as_of,
        readiness=envelope.readiness,
        confidence=confidence if confidence is not None else envelope.confidence,
        freshness=envelope.freshness,
        sources=envelope.sources,
        schema_version=envelope.schema_version,
        canonical_store_id=envelope.canonical_store_id,
        supersedes=envelope.supersedes,
        integrity=integrity if integrity is not None else envelope.integrity,
        payload=envelope.payload,
        provenance=envelope.provenance,
    )


def publish_evidence_from_observation_v1(
    observation: CanonicalObservationV1,
    *,
    evidence_type: str,
    family: str,
    payload_builder: FamilyPayloadBuilder,
    eligibility_predicate: FamilyEligibilityPredicate | None = None,
    window_key: str = "",
    as_of: str | None = None,
    confidence_when_ready: str = "medium",
    channel_available: bool = True,
    force_conflict: bool = False,
) -> tuple[EvidenceTruthRecordV1, bool]:
    """
    Publish one Evidence Truth version from a Canonical Observation.

    Returns ``(record, created)`` where ``created`` is False on idempotent
    re-delivery of the same source observation for the latest version.

    Completes lifecycle through Eligible. Never sets consumable=True.
    ``channel_available=False`` stamps Unavailable (Visitor / no-channel honesty).
    """
    require_evidence_type_for_publish_v1(family, evidence_type)

    owner = owner_for_family(family) or ""
    if not owner:
        raise EvidenceValidationError("owner_missing", f"owner_missing:{family!r}")
    if observation.canonical_family != family:
        raise EvidenceValidationError(
            "schema_invalid",
            f"observation_family_mismatch:{observation.canonical_family!r}!={family!r}",
        )

    evidence_id = build_evidence_id_v1(
        evidence_family=family,
        evidence_type=evidence_type,
        store_slug=observation.store_slug,
        subject=observation.subject,
        window_key=window_key,
    )
    store = get_evidence_truth_store_v1()
    prior = store.get(evidence_id)
    if prior is not None and observation.observation_id in prior.source_observations:
        # Idempotent: same observation already published into latest version
        return prior, False

    type_entry = require_evidence_type_for_publish_v1(family, evidence_type)
    prior_version = prior.evidence_version if prior is not None else None
    prior_readiness = prior.readiness if prior is not None else "unknown"
    if prior_version is not None:
        version = next_evidence_version_v1(supersedes=prior_version)
        supersedes = prior_version
    else:
        version = next_evidence_version_v1(None)
        supersedes = None

    as_of_ts = (as_of or "").strip() or _utc_now_iso()
    payload = dict(payload_builder(observation) or {})

    stamp = stamp_evidence_eligibility_v1(
        EvidenceStampCandidateV1(
            evidence_family=family,
            evidence_type=evidence_type,
            store_slug=observation.store_slug,
            subject=observation.subject,
            observed_at=observation.observed_at,
            as_of=as_of_ts,
            source_count=1,
            channel_available=bool(channel_available),
            prior_readiness=prior_readiness,
            ttl_seconds=type_entry.default_ttl_seconds,
            force_conflict=bool(force_conflict),
        ),
        eligibility_predicate=eligibility_predicate,
    )

    envelope = EvidenceEnvelopeV1(
        evidence_family=family,
        evidence_type=evidence_type,
        evidence_id=evidence_id,
        evidence_version=int(version),
        store_slug=observation.store_slug,
        subject=observation.subject,
        observed_period=ObservedPeriodV1(start=observation.observed_at, end=None),
        as_of=as_of_ts,
        readiness=stamp.readiness,
        confidence=stamp.confidence,
        freshness=stamp.freshness
        if stamp.freshness.observed_at
        else EvidenceFreshnessV1(observed_at=observation.observed_at),
        sources=(
            EvidenceSourceRefV1(
                observation_ref=observation.observation_id,
                channel=observation.source_channel,
                provider=observation.provider,
            ),
        ),
        canonical_store_id=observation.canonical_store_id or "",
        supersedes=int(supersedes) if supersedes is not None else None,
        integrity="",
        payload=payload,
        provenance="evidence_dual_write",
    )
    envelope = apply_stamp_to_envelope_v1(envelope, stamp)
    if stamp.readiness == READINESS_READY and confidence_when_ready:
        envelope = _replace_envelope(envelope, confidence=confidence_when_ready)

    integrity = content_integrity_hash_v1(
        {
            "evidence_id": envelope.evidence_id,
            "evidence_version": envelope.evidence_version,
            "payload": dict(envelope.payload or {}),
            "readiness": envelope.readiness,
            "sources": [s.to_dict() for s in envelope.sources],
        }
    )
    envelope = _replace_envelope(envelope, integrity=integrity)

    gov = evidence_governance_defaults_v1(
        evidence_id=evidence_id,
        evidence_version=int(version),
        lifecycle_state=LIFECYCLE_ELIGIBLE,
    )
    record = EvidenceTruthRecordV1(
        envelope=envelope,
        owner=owner,
        canonical_family=family,
        source_observations=(observation.observation_id,),
        timestamp_authority=TIMESTAMP_AUTHORITY_WALL_CLOCK_UTC,
        accounting_identity=str(gov["accounting_identity"]),
        accounting_status=str(gov["accounting_status"]),
        observability_identity=str(gov["observability_identity"]),
        observability_status=str(gov["observability_status"]),
        eligibility=str(gov["eligibility"]),
        lifecycle_state=str(gov["lifecycle_state"]),
        governance_version=int(gov["governance_version"]),
        consumable=False,
        payload_notes={
            "lifecycle_complete_through": LIFECYCLE_ELIGIBLE,
            "consumable_authorized": False,
        },
    )
    validate_evidence_constitutional_metadata_v1(record)
    stored = store.put(record)

    get_evidence_accounting_ledger_v1().increment_stage(
        STAGE_EVIDENCE_OUT,
        n=1,
        detail=f"evidence:{family}:{evidence_type}:v{version}",
    )
    return stored, True
