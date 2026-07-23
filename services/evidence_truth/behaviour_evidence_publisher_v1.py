# -*- coding: utf-8 -*-
"""
C-15 Behaviour Truth Authority — Evidence publisher wrap (WP-ET-07).

Hesitation / reason capture Evidence. No confirmed-cause invention.
widget_shown remains Unavailable until impression events exist.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.eligibility_freshness_v1 import EvidenceStampCandidateV1
from services.evidence_truth.evidence_publisher_core_v1 import (
    publish_evidence_from_observation_v1,
)
from services.evidence_truth.families_v1 import FAMILY_BEHAVIOUR
from services.evidence_truth.kernel_v1 import READINESS_UNAVAILABLE
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1

EVIDENCE_TYPE_HESITATION_REASON = "hesitation_reason_v1"


def behaviour_eligibility_predicate_v1(candidate: EvidenceStampCandidateV1) -> bool:
    if candidate.force_conflict:
        return False
    if not candidate.channel_available:
        return False
    if int(candidate.source_count or 0) < 1:
        return False
    if not (candidate.store_slug or "").strip() or not (candidate.subject or "").strip():
        return False
    return True


def _behaviour_payload(observation: CanonicalObservationV1) -> dict[str, Any]:
    payload = dict(observation.payload or {})
    reason = str(payload.get("reason") or "").strip()
    sub_reason = str(payload.get("sub_reason") or "").strip()
    return {
        "reason_captured": bool(reason),
        "reason": reason or None,
        "sub_reason": sub_reason or None,
        # Architecture: no confirmed-cause invention
        "confirmed_cause_invented": False,
        "cause_confidence": "unknown",
        # widget_shown Unavailable until impression events exist
        "widget_shown_readiness": READINESS_UNAVAILABLE,
        "widget_impression_present": False,
        "observation_type": observation.observation_type,
        "raw_kind": observation.raw_kind,
        # Cross-family: never invent purchase / recovery / product views
        "purchase_invented": False,
        "recovery_invented": False,
        "product_view_invented": False,
        # Absence must not become negative evidence
        "absence_as_negative": False,
    }


def publish_behaviour_evidence_v1(
    observation: CanonicalObservationV1,
) -> tuple[Any, bool]:
    """Publish Behaviour Evidence from a behaviour-family observation."""
    return publish_evidence_from_observation_v1(
        observation,
        evidence_type=EVIDENCE_TYPE_HESITATION_REASON,
        family=FAMILY_BEHAVIOUR,
        payload_builder=_behaviour_payload,
        eligibility_predicate=behaviour_eligibility_predicate_v1,
        confidence_when_ready="high",
    )
