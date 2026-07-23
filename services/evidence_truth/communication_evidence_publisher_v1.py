# -*- coding: utf-8 -*-
"""
C-14 Communication Truth Authority — Evidence publisher wrap (WP-ET-05).

Channel-neutral message lifecycle Evidence. Hard rule: Sent ≠ Delivered.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.eligibility_freshness_v1 import EvidenceStampCandidateV1
from services.evidence_truth.evidence_publisher_core_v1 import (
    publish_evidence_from_observation_v1,
)
from services.evidence_truth.families_v1 import FAMILY_COMMUNICATION
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1

EVIDENCE_TYPE_MESSAGE_LIFECYCLE = "message_lifecycle_v1"

# Provider-neutral lifecycle vocabulary (Architecture §2.6)
STAGE_ACCEPTED = "message_accepted"
STAGE_SENT = "message_sent"
STAGE_DELIVERED = "message_delivered"
STAGE_FAILED = "message_failed"
STAGE_REPLIED = "customer_replied"
STAGE_UNKNOWN = "message_unknown"


def _norm_status(raw: Any) -> str:
    return str(raw or "").strip().lower()


def classify_message_lifecycle_stage_v1(status: Any) -> str:
    """
    Map observation status → lifecycle stage.

    Delivery claims require delivery-class statuses only (Proof of Value).
    """
    raw = _norm_status(status)
    if raw in ("queued", "accepted", "receiving"):
        return STAGE_ACCEPTED
    if raw in ("sending", "sent", "sent_to_network"):
        return STAGE_SENT
    if raw in ("delivered", "delivered_to_customer", "read", "read_by_customer"):
        return STAGE_DELIVERED
    if raw in ("failed", "undelivered"):
        return STAGE_FAILED
    if raw in ("replied", "inbound_reply", "customer_replied"):
        return STAGE_REPLIED
    return STAGE_UNKNOWN


def delivery_claimed_v1(stage: str) -> bool:
    """True only when stage is delivery (or read) — never for sent."""
    return stage == STAGE_DELIVERED


def sent_claimed_v1(stage: str) -> bool:
    return stage in {STAGE_SENT, STAGE_DELIVERED, STAGE_REPLIED}


def communication_eligibility_predicate_v1(candidate: EvidenceStampCandidateV1) -> bool:
    if candidate.force_conflict:
        return False
    if not candidate.channel_available:
        return False
    if int(candidate.source_count or 0) < 1:
        return False
    if not (candidate.store_slug or "").strip() or not (candidate.subject or "").strip():
        return False
    return True


def _communication_payload(observation: CanonicalObservationV1) -> dict[str, Any]:
    payload = dict(observation.payload or {})
    status = payload.get("status") or payload.get("MessageStatus") or ""
    stage = classify_message_lifecycle_stage_v1(status)
    delivered = delivery_claimed_v1(stage)
    sent = sent_claimed_v1(stage)
    return {
        "lifecycle_stage": stage,
        "provider_status": _norm_status(status),
        "sent_claimed": bool(sent),
        "delivered_claimed": bool(delivered),
        # Constitutional: sent must never imply delivered
        "sent_equals_delivered": False,
        "observation_type": observation.observation_type,
        "raw_kind": observation.raw_kind,
    }


def publish_communication_evidence_v1(
    observation: CanonicalObservationV1,
) -> tuple[Any, bool]:
    """Publish Communication Evidence from a communication-family observation."""
    return publish_evidence_from_observation_v1(
        observation,
        evidence_type=EVIDENCE_TYPE_MESSAGE_LIFECYCLE,
        family=FAMILY_COMMUNICATION,
        payload_builder=_communication_payload,
        eligibility_predicate=communication_eligibility_predicate_v1,
        confidence_when_ready="high",
    )
