# -*- coding: utf-8 -*-
"""
C-10 Product Truth Authority — Evidence publisher (WP-ET-07).

Elevates product observations into Product Evidence.
Views Ready only from view evidence — ATC is not a view.
"""
from __future__ import annotations

from typing import Any

from services.evidence_truth.eligibility_freshness_v1 import EvidenceStampCandidateV1
from services.evidence_truth.evidence_publisher_core_v1 import (
    publish_evidence_from_observation_v1,
)
from services.evidence_truth.families_v1 import FAMILY_PRODUCT
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1
from services.evidence_truth.product_signal_classification_v1 import (
    SIGNAL_ATC,
    SIGNAL_CART_LINE,
    SIGNAL_VIEW,
    classify_product_signal_v1,
    view_claimed_from_signal_class_v1,
)

EVIDENCE_TYPE_PRODUCT_INTEREST = "product_interest_window_v1"


def product_eligibility_predicate_v1(candidate: EvidenceStampCandidateV1) -> bool:
    if candidate.force_conflict:
        return False
    if not candidate.channel_available:
        return False
    if int(candidate.source_count or 0) < 1:
        return False
    if not (candidate.store_slug or "").strip() or not (candidate.subject or "").strip():
        return False
    return True


def _product_payload(observation: CanonicalObservationV1) -> dict[str, Any]:
    payload = dict(observation.payload or {})
    signal_class = classify_product_signal_v1(
        payload,
        source=str(observation.provenance or ""),
    )
    view_claimed = view_claimed_from_signal_class_v1(signal_class)
    interest_claimed = signal_class in {
        SIGNAL_VIEW,
        SIGNAL_ATC,
        SIGNAL_CART_LINE,
        "interest",
    } or bool(payload.get("product_id") or observation.subject.startswith("product:"))
    return {
        "signal_class": signal_class,
        "view_claimed": bool(view_claimed),
        "interest_claimed": bool(interest_claimed),
        # Bundle has_product_views must stay false until Composer + view Ready
        "has_product_views_ready": bool(view_claimed),
        "atc_is_not_view": signal_class in {SIGNAL_ATC, SIGNAL_CART_LINE},
        "product_id": payload.get("product_id"),
        "event": payload.get("event"),
        "capture_source": payload.get("capture_source"),
        "observation_type": observation.observation_type,
        "raw_kind": observation.raw_kind,
        # Cross-family: never invent purchase / recovery / visitor
        "purchase_invented": False,
        "recovery_invented": False,
        "visitor_invented": False,
    }


def publish_product_evidence_v1(
    observation: CanonicalObservationV1,
) -> tuple[Any, bool]:
    """Publish Product Evidence from a product-family observation."""
    return publish_evidence_from_observation_v1(
        observation,
        evidence_type=EVIDENCE_TYPE_PRODUCT_INTEREST,
        family=FAMILY_PRODUCT,
        payload_builder=_product_payload,
        eligibility_predicate=product_eligibility_predicate_v1,
        confidence_when_ready="medium",
    )
