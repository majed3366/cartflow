# -*- coding: utf-8 -*-
"""
C-09 Visitor Truth Authority — Evidence publisher (WP-ET-08).

Sole owner of Visitor/Traffic Truth. Never cart proxies.
Unavailable when channel absent. Bundle visitor fields remain unauthorized.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.eligibility_freshness_v1 import EvidenceStampCandidateV1
from services.evidence_truth.evidence_publisher_core_v1 import (
    publish_evidence_from_observation_v1,
)
from services.evidence_truth.families_v1 import FAMILY_VISITOR
from services.evidence_truth.kernel_v1 import (
    READINESS_READY,
    REJECT_CONFLICT_UNRESOLVED,
    EvidenceValidationError,
)
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1
from services.evidence_truth.observation_types_v1 import RAW_KIND_TRAFFIC
from services.evidence_truth.visitor_proxy_detection_v1 import (
    detect_visitor_proxy_v1,
    visitor_channel_available_v1,
)

EVIDENCE_TYPE_STORE_VISITOR_WINDOW = "store_visitor_window_v1"


def visitor_eligibility_predicate_v1(candidate: EvidenceStampCandidateV1) -> bool:
    if candidate.force_conflict:
        return False
    if not candidate.channel_available:
        return False
    if int(candidate.source_count or 0) < 1:
        return False
    if not (candidate.store_slug or "").strip() or not (candidate.subject or "").strip():
        return False
    return True


def _visitor_payload(
    observation: CanonicalObservationV1,
    *,
    channel_available: bool,
) -> dict[str, Any]:
    payload = dict(observation.payload or {})
    return {
        "presence_claimed": bool(channel_available),
        "channel_available": bool(channel_available),
        "visitor_id": payload.get("visitor_id") or payload.get("anonymous_id"),
        "session_id": payload.get("session_id"),
        "event": payload.get("event"),
        "observation_type": observation.observation_type,
        "raw_kind": observation.raw_kind,
        # Hard rules
        "cart_proxy": False,
        "abandoned_cart_proxy": False,
        "recovery_proxy": False,
        # Bundle consumption not authorized in WP-ET-08 (Stage 5)
        "bundle_visitor_fields_authorized": False,
        "has_visitor_truth_for_bundle": False,
        # Cross-family
        "purchase_invented": False,
        "cart_invented": False,
        "absence_as_negative": False,
    }


def publish_visitor_evidence_v1(
    observation: CanonicalObservationV1,
    *,
    channel_available: bool | None = None,
) -> tuple[Any, bool]:
    """
    Publish Visitor Evidence from a visitor-family traffic observation.

    Rejects cart/recovery proxies. Stamps Unavailable when channel absent.
    """
    if observation.raw_kind != RAW_KIND_TRAFFIC:
        raise EvidenceValidationError(
            REJECT_CONFLICT_UNRESOLVED,
            f"visitor_requires_traffic_raw:{observation.raw_kind!r}",
        )
    proxy = detect_visitor_proxy_v1(
        observation.payload,
        observation=observation,
        raw_kind=observation.raw_kind,
    )
    if proxy:
        raise EvidenceValidationError(
            REJECT_CONFLICT_UNRESOLVED,
            f"visitor_proxy_rejected:{proxy}",
        )

    ch_ok = (
        bool(channel_available)
        if channel_available is not None
        else visitor_channel_available_v1(
            observation.payload,
            source_channel=observation.source_channel,
        )
    )

    def _builder(obs: CanonicalObservationV1) -> dict[str, Any]:
        return _visitor_payload(obs, channel_available=ch_ok)

    record, created = publish_evidence_from_observation_v1(
        observation,
        evidence_type=EVIDENCE_TYPE_STORE_VISITOR_WINDOW,
        family=FAMILY_VISITOR,
        payload_builder=_builder,
        eligibility_predicate=visitor_eligibility_predicate_v1,
        confidence_when_ready="medium",
        channel_available=ch_ok,
    )
    # Reinforce bundle non-authorization regardless of readiness
    if record.readiness == READINESS_READY and record.envelope.payload.get(
        "bundle_visitor_fields_authorized"
    ):
        raise EvidenceValidationError(
            REJECT_CONFLICT_UNRESOLVED,
            "bundle_visitor_fields_must_remain_unauthorized",
        )
    return record, created
