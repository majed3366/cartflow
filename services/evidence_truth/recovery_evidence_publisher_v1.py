# -*- coding: utf-8 -*-
"""
C-12 Recovery Truth Authority — Evidence publisher wrap (WP-ET-06).

Publishes Recovery Evidence from recovery timeline observations, aligned to
the Lifecycle Truth Contract. Must not weaken terminal purchase stop.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.eligibility_freshness_v1 import EvidenceStampCandidateV1
from services.evidence_truth.evidence_publisher_core_v1 import (
    publish_evidence_from_observation_v1,
)
from services.evidence_truth.families_v1 import FAMILY_RECOVERY
from services.evidence_truth.lifecycle_truth_alignment_v1 import (
    build_recovery_lifecycle_payload_v1,
)
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1

EVIDENCE_TYPE_RECOVERY_PROGRESSION = "recovery_progression_v1"


def recovery_eligibility_predicate_v1(candidate: EvidenceStampCandidateV1) -> bool:
    if candidate.force_conflict:
        return False
    if not candidate.channel_available:
        return False
    if int(candidate.source_count or 0) < 1:
        return False
    if not (candidate.store_slug or "").strip() or not (candidate.subject or "").strip():
        return False
    return True


def _recovery_payload(observation: CanonicalObservationV1) -> dict[str, Any]:
    payload = dict(observation.payload or {})
    timeline_status = str(
        payload.get("timeline_status")
        or payload.get("status")
        or ""
    ).strip()
    recovery_key = str(
        payload.get("recovery_key") or observation.subject or ""
    ).strip()
    return build_recovery_lifecycle_payload_v1(
        timeline_status=timeline_status,
        recovery_key=recovery_key,
        observation_type=observation.observation_type,
        raw_kind=observation.raw_kind,
    )


def publish_recovery_evidence_v1(
    observation: CanonicalObservationV1,
) -> tuple[Any, bool]:
    """Publish Recovery Evidence from a recovery-family observation."""
    return publish_evidence_from_observation_v1(
        observation,
        evidence_type=EVIDENCE_TYPE_RECOVERY_PROGRESSION,
        family=FAMILY_RECOVERY,
        payload_builder=_recovery_payload,
        eligibility_predicate=recovery_eligibility_predicate_v1,
        confidence_when_ready="high",
    )
