# -*- coding: utf-8 -*-
"""
Merchant Claim Evidence v1 — claim-level evidence ownership (presentation).

Architectural rule: evidence belongs to the claim, not the section.
Each merchant insight resolves its own evidence_id through the registry.

Does not modify Knowledge Layer insight generation, metrics, or confidence logic.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.merchant_evidence_registry_v1 import (
    EVIDENCE_HESITATION_REASON,
    EVIDENCE_PURCHASE_RECORD,
    EVIDENCE_RECOVERY_RECORD,
    EVIDENCE_STORE_ACTIVITY,
    EVIDENCE_VISITOR_BEHAVIOR,
    REGISTRY_VERSION,
    build_merchant_evidence_registry_payload,
    get_merchant_evidence_entry,
    merchant_evidence_label_ar,
    merchant_evidence_section_source_ar,
)

# Knowledge insight_key → registry evidence_id (presentation mapping only)
INSIGHT_CLAIM_EVIDENCE_ID: dict[str, str] = {
    "traffic_visitor_unavailable": EVIDENCE_VISITOR_BEHAVIOR,
    "traffic_cart_demand_trend": EVIDENCE_STORE_ACTIVITY,
    "conversion_funnel_gaps": EVIDENCE_STORE_ACTIVITY,
    "conversion_cart_to_purchase": EVIDENCE_PURCHASE_RECORD,
    "conversion_no_carts": EVIDENCE_STORE_ACTIVITY,
    "hesitation_insufficient_sample": EVIDENCE_HESITATION_REASON,
    "hesitation_top_reason": EVIDENCE_HESITATION_REASON,
    "hesitation_distribution": EVIDENCE_HESITATION_REASON,
    "recovery_insufficient_sample": EVIDENCE_RECOVERY_RECORD,
    "recovery_activity_summary": EVIDENCE_RECOVERY_RECORD,
    "recovery_bottleneck": EVIDENCE_RECOVERY_RECORD,
    "store_health_overview": EVIDENCE_STORE_ACTIVITY,
}

# Category fallback when insight_key is not yet mapped (future insights)
CATEGORY_CLAIM_EVIDENCE_ID: dict[str, str] = {
    "traffic": EVIDENCE_VISITOR_BEHAVIOR,
    "conversion": EVIDENCE_STORE_ACTIVITY,
    "hesitation": EVIDENCE_HESITATION_REASON,
    "recovery": EVIDENCE_RECOVERY_RECORD,
    "store_health": EVIDENCE_STORE_ACTIVITY,
}

DEFAULT_CLAIM_EVIDENCE_ID = EVIDENCE_STORE_ACTIVITY


def resolve_claim_evidence_id(
    *,
    insight_key: str = "",
    category: str = "",
) -> str:
    """Map one insight claim to a governed registry evidence_id."""
    key = (insight_key or "").strip()
    if key and key in INSIGHT_CLAIM_EVIDENCE_ID:
        return INSIGHT_CLAIM_EVIDENCE_ID[key]
    cat = (category or "").strip().lower()
    if cat and cat in CATEGORY_CLAIM_EVIDENCE_ID:
        return CATEGORY_CLAIM_EVIDENCE_ID[cat]
    return DEFAULT_CLAIM_EVIDENCE_ID


def enrich_claim_evidence_fields(
    target: dict[str, Any],
    *,
    insight_key: str = "",
    category: str = "",
) -> None:
    """Attach claim-owned evidence metadata to one insight dict (in-place)."""
    eid = resolve_claim_evidence_id(
        insight_key=insight_key or str(target.get("insight_key") or ""),
        category=category or str(target.get("category") or ""),
    )
    entry = get_merchant_evidence_entry(eid)
    label = merchant_evidence_label_ar(eid)
    target["evidence_id"] = eid
    target["evidence_label_ar"] = label
    target["evidence_source_ar"] = label
    target["claim_evidence_source_ar"] = merchant_evidence_section_source_ar(eid)
    if entry is not None:
        target["evidence_origin"] = entry.evidence_origin


def enrich_knowledge_report_claim_evidence_v1(
    target: Mapping[str, Any] | dict[str, Any],
) -> None:
    """
    Enrich KL report payload: per-insight claim evidence + registry catalog.

    No section-level evidence ownership — each card is self-contained.
    """
    if not isinstance(target, dict):
        return
    insights = target.get("insights")
    if isinstance(insights, list):
        for raw in insights:
            if isinstance(raw, dict):
                enrich_claim_evidence_fields(raw)
    target["merchant_evidence_registry_v1"] = build_merchant_evidence_registry_payload(
        claim_catalog_only=True,
    )
    target["merchant_claim_evidence_v1"] = {
        "version": REGISTRY_VERSION,
        "ownership": "claim",
    }


__all__ = [
    "CATEGORY_CLAIM_EVIDENCE_ID",
    "DEFAULT_CLAIM_EVIDENCE_ID",
    "INSIGHT_CLAIM_EVIDENCE_ID",
    "enrich_claim_evidence_fields",
    "enrich_knowledge_report_claim_evidence_v1",
    "resolve_claim_evidence_id",
]
