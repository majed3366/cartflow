# -*- coding: utf-8 -*-
"""
C-13 Purchase Truth Authority — Evidence publisher wrap (WP-ET-05).

Elevates purchase observations into Purchase Evidence versions without
changing Purchase Truth semantics or recovery terminal stop authority.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.eligibility_freshness_v1 import EvidenceStampCandidateV1
from services.evidence_truth.evidence_publisher_core_v1 import (
    publish_evidence_from_observation_v1,
)
from services.evidence_truth.families_v1 import FAMILY_PURCHASE
from services.evidence_truth.kernel_v1 import CONFIDENCE_CONFIRMED
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1

EVIDENCE_TYPE_PURCHASE_CONFIRMED = "purchase_confirmed_v1"


def purchase_eligibility_predicate_v1(candidate: EvidenceStampCandidateV1) -> bool:
    """
    Wrap-not-rewrite: Ready when identity + ≥1 source present.

    Never invents purchase from cart disappearance (no cart family inputs here).
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


def _purchase_payload(observation: CanonicalObservationV1) -> dict[str, Any]:
    """
    Purchase Evidence payload — facts only.

    ``terminal_for_recovery`` documents Evidence meaning; legacy Purchase Truth
    remains the production stop authority (no consumer cutover in WP-ET-05).
    """
    payload = dict(observation.payload or {})
    return {
        "purchase_confirmed": True,
        "terminal_for_recovery": True,
        "recovery_key": payload.get("recovery_key") or observation.subject,
        "observation_type": observation.observation_type,
        "raw_kind": observation.raw_kind,
        # Explicit: Evidence does not drive recovery stop in this package
        "production_stop_authority": "purchase_truth_legacy",
    }


def publish_purchase_evidence_v1(
    observation: CanonicalObservationV1,
) -> tuple[Any, bool]:
    """Publish Purchase Evidence from a purchase-family observation."""
    return publish_evidence_from_observation_v1(
        observation,
        evidence_type=EVIDENCE_TYPE_PURCHASE_CONFIRMED,
        family=FAMILY_PURCHASE,
        payload_builder=_purchase_payload,
        eligibility_predicate=purchase_eligibility_predicate_v1,
        confidence_when_ready=CONFIDENCE_CONFIRMED,
    )
