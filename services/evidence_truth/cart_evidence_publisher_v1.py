# -*- coding: utf-8 -*-
"""
C-11 Cart Truth Authority — Evidence publisher wrap (WP-ET-06).

Elevates cart-event observations into Cart Evidence versions.
Identity conflicts fail closed at Observation normalize (no silent rewrite).
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.eligibility_freshness_v1 import EvidenceStampCandidateV1
from services.evidence_truth.evidence_publisher_core_v1 import (
    publish_evidence_from_observation_v1,
)
from services.evidence_truth.families_v1 import FAMILY_CART
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1

EVIDENCE_TYPE_CART_STATE = "cart_state_v1"


def cart_eligibility_predicate_v1(candidate: EvidenceStampCandidateV1) -> bool:
    if candidate.force_conflict:
        return False
    if not candidate.channel_available:
        return False
    if int(candidate.source_count or 0) < 1:
        return False
    if not (candidate.store_slug or "").strip() or not (candidate.subject or "").strip():
        return False
    return True


def _cart_payload(observation: CanonicalObservationV1) -> dict[str, Any]:
    payload = dict(observation.payload or {})
    event = str(payload.get("event") or "").strip().lower()
    abandon_like = event in {
        "cart_abandoned",
        "abandoned",
        "abandon",
        "cart_abandon",
    }
    active_like = event in {
        "cart_updated",
        "cart_state_sync",
        "add",
        "cart_active",
    }
    return {
        "cart_event": event,
        "abandon_signal": bool(abandon_like),
        "active_signal": bool(active_like),
        "session_id": payload.get("session_id"),
        "cart_id": payload.get("cart_id"),
        "recovery_key": payload.get("recovery_key"),
        "observation_type": observation.observation_type,
        "raw_kind": observation.raw_kind,
        # Cart Evidence must not invent purchase / visitor / delivery
        "purchase_invented": False,
        "visitor_invented": False,
    }


def publish_cart_evidence_v1(
    observation: CanonicalObservationV1,
) -> tuple[Any, bool]:
    """Publish Cart Evidence from a cart-family observation."""
    return publish_evidence_from_observation_v1(
        observation,
        evidence_type=EVIDENCE_TYPE_CART_STATE,
        family=FAMILY_CART,
        payload_builder=_cart_payload,
        eligibility_predicate=cart_eligibility_predicate_v1,
        confidence_when_ready="high",
    )
