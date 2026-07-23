# -*- coding: utf-8 -*-
"""
Evidence family registry — canonical families (Architecture §2).

Distinct from merchant presentation registry (merchant_evidence_registry_v1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

FAMILY_VISITOR = "visitor"
FAMILY_PRODUCT = "product"
FAMILY_CART = "cart"
FAMILY_RECOVERY = "recovery"
FAMILY_PURCHASE = "purchase"
FAMILY_COMMUNICATION = "communication"
FAMILY_BEHAVIOUR = "behaviour"

EvidenceFamily = str


@dataclass(frozen=True)
class EvidenceFamilyEntryV1:
    family: str
    primary_question: str
    owner_module: str
    status: str = "registered"  # registered | publishing (later WPs)


EVIDENCE_FAMILIES_V1: dict[str, EvidenceFamilyEntryV1] = {
    FAMILY_VISITOR: EvidenceFamilyEntryV1(
        family=FAMILY_VISITOR,
        primary_question="Who visited / how much storefront presence occurred?",
        owner_module="visitor_truth_authority",
    ),
    FAMILY_PRODUCT: EvidenceFamilyEntryV1(
        family=FAMILY_PRODUCT,
        primary_question="What product interest, view, and catalog facts occurred?",
        owner_module="product_truth_authority",
    ),
    FAMILY_CART: EvidenceFamilyEntryV1(
        family=FAMILY_CART,
        primary_question="What cart composition and abandon/active states occurred?",
        owner_module="cart_truth_authority",
    ),
    FAMILY_RECOVERY: EvidenceFamilyEntryV1(
        family=FAMILY_RECOVERY,
        primary_question="What recovery lifecycle progression occurred?",
        owner_module="recovery_truth_authority",
    ),
    FAMILY_PURCHASE: EvidenceFamilyEntryV1(
        family=FAMILY_PURCHASE,
        primary_question="What purchase / conversion facts are proven?",
        owner_module="purchase_truth_authority",
    ),
    FAMILY_COMMUNICATION: EvidenceFamilyEntryV1(
        family=FAMILY_COMMUNICATION,
        primary_question="What message send / delivery / reply facts occurred?",
        owner_module="communication_truth_authority",
    ),
    FAMILY_BEHAVIOUR: EvidenceFamilyEntryV1(
        family=FAMILY_BEHAVIOUR,
        primary_question="What hesitation, reason, return, and interaction facts occurred?",
        owner_module="behaviour_truth_authority",
    ),
}


def list_evidence_families() -> list[EvidenceFamilyEntryV1]:
    return [EVIDENCE_FAMILIES_V1[k] for k in sorted(EVIDENCE_FAMILIES_V1)]


def get_evidence_family(family: str) -> Optional[EvidenceFamilyEntryV1]:
    key = (family or "").strip().lower()
    return EVIDENCE_FAMILIES_V1.get(key)


def require_evidence_family(family: str) -> EvidenceFamilyEntryV1:
    entry = get_evidence_family(family)
    if entry is None:
        raise KeyError(f"unknown_evidence_family:{family!r}")
    return entry
