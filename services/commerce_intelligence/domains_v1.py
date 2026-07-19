# -*- coding: utf-8 -*-
"""
Four canonical Commerce Intelligence domains.

Overlays Commercial Question Registry dimensions — does not replace CQ IDs.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.business_findings_contract_v1 import norm as _norm
from services.commercial_question_registry_v1 import (
    DIM_CONTACT,
    DIM_DATA,
    DIM_GUIDANCE,
    DIM_HESITATION,
    DIM_KNOWLEDGE,
    DIM_PRODUCTS,
    DIM_RECOVERY,
    DIM_TRAFFIC,
    DIM_WHATSAPP,
)

DOMAIN_PRODUCT = "product_intelligence"
DOMAIN_CUSTOMER = "customer_intelligence"
DOMAIN_STORE = "store_intelligence"
DOMAIN_GUIDANCE = "commercial_guidance"

DOMAIN_LABELS_AR = {
    DOMAIN_PRODUCT: "ذكاء المنتجات",
    DOMAIN_CUSTOMER: "ذكاء العملاء",
    DOMAIN_STORE: "ذكاء المتجر",
    DOMAIN_GUIDANCE: "التوجيه التجاري",
}

DOMAIN_QUESTIONS_EN = {
    DOMAIN_PRODUCT: (
        "Which products attract customers?",
        "Which products fail to convert?",
        "Which products recover?",
        "Which products repeatedly fail?",
        "Which products deserve attention?",
    ),
    DOMAIN_CUSTOMER: (
        "Which customer behaviors repeat?",
        "What hesitation patterns exist?",
        "What purchase patterns exist?",
        "What return patterns exist?",
    ),
    DOMAIN_STORE: (
        "What is changing in the store?",
        "Is conversion improving?",
        "Is recovery improving?",
        "Is customer quality changing?",
        "Is evidence growing?",
    ),
    DOMAIN_GUIDANCE: (
        "What should the merchant do — only with sufficient evidence?",
    ),
}

# Registry dimension → primary intelligence domain
DIMENSION_TO_DOMAIN: dict[str, str] = {
    DIM_PRODUCTS: DOMAIN_PRODUCT,
    DIM_HESITATION: DOMAIN_CUSTOMER,
    DIM_RECOVERY: DOMAIN_CUSTOMER,  # return / recovery patterns are customer behavior
    DIM_TRAFFIC: DOMAIN_STORE,
    DIM_KNOWLEDGE: DOMAIN_STORE,
    DIM_DATA: DOMAIN_STORE,
    DIM_GUIDANCE: DOMAIN_GUIDANCE,
    DIM_WHATSAPP: DOMAIN_GUIDANCE,
    DIM_CONTACT: DOMAIN_GUIDANCE,  # act-now gate → guidance when evidenced
}

# Finding family / type hints → domains (multi-source allowed)
FINDING_TYPE_SOURCE_HINTS: dict[str, tuple[str, ...]] = {
    "high_interest_low_purchase_product_v1": (DOMAIN_PRODUCT,),
    "repeated_interest_v1": (DOMAIN_PRODUCT, DOMAIN_CUSTOMER),
    "low_product_interest_v1": (DOMAIN_PRODUCT,),
    "dominant_hesitation_reason_v1": (DOMAIN_CUSTOMER,),
    "hesitation_resolution_effectiveness_v1": (DOMAIN_CUSTOMER, DOMAIN_STORE),
    "return_without_purchase_v1": (DOMAIN_CUSTOMER, DOMAIN_STORE),
    "recovery_channel_effectiveness_v1": (DOMAIN_STORE, DOMAIN_GUIDANCE),
    "whatsapp_message_timing_test_v1": (DOMAIN_GUIDANCE,),
    "traffic_versus_conversion_v1": (DOMAIN_STORE,),
    "missing_contact_blocks_recovery_v1": (DOMAIN_GUIDANCE, DOMAIN_STORE),
    "insufficient_or_conflicting_evidence_v1": (DOMAIN_STORE, DOMAIN_GUIDANCE),
}


def domain_for_dimension_v1(dimension: str) -> str:
    dim = _norm(dimension).lower()
    return DIMENSION_TO_DOMAIN.get(dim, DOMAIN_STORE)


def source_domains_for_finding_v1(
    finding: Mapping[str, Any],
    *,
    question_dimension: str = "",
) -> list[str]:
    """Deterministic multi-domain provenance for a finding-backed record."""
    ftype = _norm(finding.get("finding_type") or finding.get("commercial_interpretation_id"))
    hinted = list(FINDING_TYPE_SOURCE_HINTS.get(ftype, ()))
    primary = domain_for_dimension_v1(question_dimension) if question_dimension else ""
    out: list[str] = []
    for d in hinted + ([primary] if primary else []):
        if d and d not in out:
            out.append(d)
    if not out:
        out.append(DOMAIN_STORE)
    return out


def is_guidance_eligible_v1(
    *,
    confidence: str,
    status: str,
    recommendation_type: str,
) -> bool:
    """
    Commercial Guidance may speak only with sufficient evidence.

    Insufficient / conflicting findings become 'collect more evidence' guidance
    records — not action recommendations.
    """
    conf = _norm(confidence).lower()
    st = _norm(status).lower()
    rec = _norm(recommendation_type).lower()
    if st in ("insufficient_evidence", "conflicting_evidence") or conf == "insufficient":
        return True  # honest “collect more evidence” is guidance
    if rec in ("act_now", "test", "monitor", "investigate", "no_action"):
        return conf in ("high", "medium", "confirmed") or st in (
            "confirmed",
            "emerging",
            "strengthening",
        )
    return False


def all_domains_v1() -> Sequence[str]:
    return (
        DOMAIN_PRODUCT,
        DOMAIN_CUSTOMER,
        DOMAIN_STORE,
        DOMAIN_GUIDANCE,
    )


__all__ = [
    "DIMENSION_TO_DOMAIN",
    "DOMAIN_CUSTOMER",
    "DOMAIN_GUIDANCE",
    "DOMAIN_LABELS_AR",
    "DOMAIN_PRODUCT",
    "DOMAIN_QUESTIONS_EN",
    "DOMAIN_STORE",
    "FINDING_TYPE_SOURCE_HINTS",
    "all_domains_v1",
    "domain_for_dimension_v1",
    "is_guidance_eligible_v1",
    "source_domains_for_finding_v1",
]
