# -*- coding: utf-8 -*-
"""
Ownership Constitution registry — exactly one owner per evidence question.

Architecture §4. Spine only: declarations, not runtime authorities.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.evidence_truth.families_v1 import (
    FAMILY_BEHAVIOUR,
    FAMILY_CART,
    FAMILY_COMMUNICATION,
    FAMILY_PRODUCT,
    FAMILY_PURCHASE,
    FAMILY_RECOVERY,
    FAMILY_VISITOR,
)

QUESTION_VISITOR_TRUTH = "visitor_truth"
QUESTION_PRODUCT_VIEW_TRUTH = "product_view_truth"
QUESTION_TRAFFIC_TRUTH = "traffic_truth"
QUESTION_BEHAVIOUR_TRUTH = "behaviour_truth"
QUESTION_PURCHASE_TRUTH = "purchase_truth"
QUESTION_CART_TRUTH = "cart_truth"
QUESTION_RECOVERY_TRUTH = "recovery_truth"
QUESTION_COMMUNICATION_TRUTH = "communication_truth"
QUESTION_EVIDENCE_FRESHNESS = "evidence_freshness"
QUESTION_EVIDENCE_ELIGIBILITY = "evidence_eligibility"
QUESTION_EVIDENCE_CONFIDENCE = "evidence_confidence"
QUESTION_EVIDENCE_BUNDLE_COMPOSITION = "evidence_bundle_composition"

EvidenceQuestion = str
EvidenceOwner = str


@dataclass(frozen=True)
class EvidenceOwnershipEntryV1:
    question: str
    owner: str
    primary_family: str
    notes: str = ""


EVIDENCE_OWNERSHIP_V1: dict[str, EvidenceOwnershipEntryV1] = {
    QUESTION_VISITOR_TRUTH: EvidenceOwnershipEntryV1(
        question=QUESTION_VISITOR_TRUTH,
        owner="visitor_truth_authority",
        primary_family=FAMILY_VISITOR,
        notes="Closes INV-008; no other module may define visitor totals",
    ),
    QUESTION_TRAFFIC_TRUTH: EvidenceOwnershipEntryV1(
        question=QUESTION_TRAFFIC_TRUTH,
        owner="visitor_truth_authority",
        primary_family=FAMILY_VISITOR,
        notes="Traffic is a Visitor Evidence concern — not a parallel owner",
    ),
    QUESTION_PRODUCT_VIEW_TRUTH: EvidenceOwnershipEntryV1(
        question=QUESTION_PRODUCT_VIEW_TRUTH,
        owner="product_truth_authority",
        primary_family=FAMILY_PRODUCT,
        notes="ProductSignalEvents are sources under this owner (later WPs)",
    ),
    QUESTION_BEHAVIOUR_TRUTH: EvidenceOwnershipEntryV1(
        question=QUESTION_BEHAVIOUR_TRUTH,
        owner="behaviour_truth_authority",
        primary_family=FAMILY_BEHAVIOUR,
    ),
    QUESTION_PURCHASE_TRUTH: EvidenceOwnershipEntryV1(
        question=QUESTION_PURCHASE_TRUTH,
        owner="purchase_truth_authority",
        primary_family=FAMILY_PURCHASE,
    ),
    QUESTION_CART_TRUTH: EvidenceOwnershipEntryV1(
        question=QUESTION_CART_TRUTH,
        owner="cart_truth_authority",
        primary_family=FAMILY_CART,
    ),
    QUESTION_RECOVERY_TRUTH: EvidenceOwnershipEntryV1(
        question=QUESTION_RECOVERY_TRUTH,
        owner="recovery_truth_authority",
        primary_family=FAMILY_RECOVERY,
    ),
    QUESTION_COMMUNICATION_TRUTH: EvidenceOwnershipEntryV1(
        question=QUESTION_COMMUNICATION_TRUTH,
        owner="communication_truth_authority",
        primary_family=FAMILY_COMMUNICATION,
    ),
    QUESTION_EVIDENCE_FRESHNESS: EvidenceOwnershipEntryV1(
        question=QUESTION_EVIDENCE_FRESHNESS,
        owner="evidence_truth_platform",
        primary_family="",
        notes="Cross-cutting governance; does not invent family facts",
    ),
    QUESTION_EVIDENCE_ELIGIBILITY: EvidenceOwnershipEntryV1(
        question=QUESTION_EVIDENCE_ELIGIBILITY,
        owner="evidence_truth_platform",
        primary_family="",
        notes="Readiness gates; families supply type-specific predicates later",
    ),
    QUESTION_EVIDENCE_CONFIDENCE: EvidenceOwnershipEntryV1(
        question=QUESTION_EVIDENCE_CONFIDENCE,
        owner="evidence_truth_platform",
        primary_family="",
        notes="Confidence vocabulary alignment with Proof of Value",
    ),
    QUESTION_EVIDENCE_BUNDLE_COMPOSITION: EvidenceOwnershipEntryV1(
        question=QUESTION_EVIDENCE_BUNDLE_COMPOSITION,
        owner="evidence_bundle_composer",
        primary_family="",
        notes="Consumption-only projection; cannot create unpublished evidence",
    ),
}


def list_evidence_ownership() -> list[EvidenceOwnershipEntryV1]:
    return [EVIDENCE_OWNERSHIP_V1[k] for k in sorted(EVIDENCE_OWNERSHIP_V1)]


def get_evidence_owner(question: str) -> Optional[EvidenceOwnershipEntryV1]:
    key = (question or "").strip().lower()
    return EVIDENCE_OWNERSHIP_V1.get(key)


def require_evidence_owner(question: str) -> EvidenceOwnershipEntryV1:
    entry = get_evidence_owner(question)
    if entry is None:
        raise KeyError(f"unknown_evidence_question:{question!r}")
    return entry


def owner_for_family(family: str) -> Optional[str]:
    """Return the family authority owner module for a registered family."""
    fam = (family or "").strip().lower()
    for entry in EVIDENCE_OWNERSHIP_V1.values():
        if entry.primary_family == fam and entry.owner.endswith("_authority"):
            return entry.owner
    return None
