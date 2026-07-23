# -*- coding: utf-8 -*-
"""
CIS → Knowledge intake policy registry (ciknow_v1).

Code-owned. No page/service scattering of mapping logic.
"""
from __future__ import annotations

from typing import Any

from services.product_data.commerce_intelligence_knowledge_types_v1 import (
    INTAKE_POLICY_REGISTRY_VERSION_V1,
    KT_EVIDENCE_CONFLICT,
    KT_EVIDENCE_GAP,
    KT_HESITATION_RECOVERY,
    KT_PRODUCT_INTEREST_GAP,
    KT_RECOVERY_INFLUENCE,
    KT_REPEATED_INTEREST,
    KT_TRAFFIC_GAP,
    KT_WA_RETURN,
)
from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    STATE_CONFLICTING,
    STATE_INSUFFICIENT,
    STATE_QUALIFIED,
)

INTAKE_POLICIES_V1: tuple[dict[str, Any], ...] = (
    {
        "synthesis_rule_key": "product_interest_without_purchase",
        "eligible_states": (STATE_QUALIFIED,),
        "target_knowledge_type": KT_PRODUCT_INTEREST_GAP,
        "target_subject_types": ("product",),
        "minimum_evidence_coverage": 0.0,
        "minimum_source_diversity": 1,
        "minimum_sample_size": 1,
        "contradiction_tolerance": 0,
        "statement_template": (
            "This product receives repeated interest and cart additions, "
            "while observed purchase completion remains comparatively weak."
        ),
        "deferred": False,
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
    {
        "synthesis_rule_key": "high_traffic_weak_conversion",
        "eligible_states": (STATE_QUALIFIED,),
        "target_knowledge_type": KT_TRAFFIC_GAP,
        "target_subject_types": ("store",),
        "minimum_evidence_coverage": 0.0,
        "minimum_source_diversity": 1,
        "minimum_sample_size": 1,
        "contradiction_tolerance": 0,
        "statement_template": (
            "The store generates meaningful activity and cart engagement, "
            "while completed purchase conversion remains weak."
        ),
        "deferred": False,
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
    {
        "synthesis_rule_key": "whatsapp_return_without_purchase",
        "eligible_states": (STATE_QUALIFIED,),
        "target_knowledge_type": KT_WA_RETURN,
        "target_subject_types": ("store",),
        "minimum_evidence_coverage": 0.0,
        "minimum_source_diversity": 1,
        "minimum_sample_size": 3,
        "contradiction_tolerance": 0,
        "statement_template": (
            "Customers often return after WhatsApp contact, "
            "but many do not complete purchase within the observed window."
        ),
        "deferred": False,
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
    {
        "synthesis_rule_key": "shipping_hesitation_recovery_outcome",
        "eligible_states": (STATE_QUALIFIED,),
        "target_knowledge_type": KT_HESITATION_RECOVERY,
        "target_subject_types": ("hesitation_reason",),
        "minimum_evidence_coverage": 0.0,
        "minimum_source_diversity": 1,
        "minimum_sample_size": 3,
        "contradiction_tolerance": 0,
        "statement_template": (
            "Customers expressing shipping-related hesitation frequently return "
            "after recovery contact, while purchase completion remains limited "
            "in the observed window."
        ),
        "deferred": False,
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
    {
        "synthesis_rule_key": "repeated_interest_pattern",
        "eligible_states": (STATE_QUALIFIED,),
        "target_knowledge_type": KT_REPEATED_INTEREST,
        "target_subject_types": ("product", "store"),
        "minimum_evidence_coverage": 0.0,
        "minimum_source_diversity": 1,
        "minimum_sample_size": 1,
        "contradiction_tolerance": 0,
        "statement_template": (
            "Customers repeatedly return to this product or cart, "
            "while the journey frequently remains unresolved."
        ),
        "deferred": False,
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
    {
        "synthesis_rule_key": "recovery_influence_boundary",
        "eligible_states": (STATE_QUALIFIED,),
        "target_knowledge_type": KT_RECOVERY_INFLUENCE,
        "target_subject_types": ("store",),
        "minimum_evidence_coverage": 0.0,
        "minimum_source_diversity": 1,
        "minimum_sample_size": 1,
        "contradiction_tolerance": 0,
        "statement_template": (
            "Purchase influence classifications are preserved separately "
            "(confirmed recovery, high confidence, possible influence, "
            "unattributed purchase) and must not be collapsed into recovered revenue."
        ),
        "deferred": False,
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
    {
        "synthesis_rule_key": "insufficient_evidence_store",
        "eligible_states": (STATE_QUALIFIED, STATE_INSUFFICIENT),
        "target_knowledge_type": KT_EVIDENCE_GAP,
        "target_subject_types": ("store",),
        "minimum_evidence_coverage": 0.0,
        "minimum_source_diversity": 0,
        "minimum_sample_size": 0,
        "contradiction_tolerance": 0,
        "statement_template": (
            "Current evidence is not sufficient to support a reliable "
            "commercial conclusion."
        ),
        "deferred": False,
        "active": True,
        "version": "1",
        "routing_eligibility": False,
        # Only when synthesis encodes insufficiency (qualified insufficiency pattern
        # or insufficient_evidence state) — evaluator still checks summary key.
        "require_summary_contains": "insufficient",
    },
    {
        "synthesis_rule_key": "conflicting_evidence_store",
        "eligible_states": (STATE_CONFLICTING,),
        "target_knowledge_type": KT_EVIDENCE_CONFLICT,
        "target_subject_types": ("store",),
        "minimum_evidence_coverage": 0.0,
        "minimum_source_diversity": 1,
        "minimum_sample_size": 0,
        "contradiction_tolerance": 99,
        "statement_template": (
            "Available evidence supports more than one possible interpretation. "
            "No single explanation is currently reliable."
        ),
        "deferred": False,
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
    {
        "synthesis_rule_key": "discount_message_weakness",
        "eligible_states": (STATE_QUALIFIED,),
        "target_knowledge_type": KT_HESITATION_RECOVERY,
        "target_subject_types": ("recovery_strategy",),
        "minimum_evidence_coverage": 0.5,
        "minimum_source_diversity": 2,
        "minimum_sample_size": 5,
        "contradiction_tolerance": 0,
        "statement_template": "",
        "deferred": True,
        "deferred_id": "D-CISYN-01",
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
    {
        "synthesis_rule_key": "vip_followup_outcome",
        "eligible_states": (STATE_QUALIFIED,),
        "target_knowledge_type": KT_RECOVERY_INFLUENCE,
        "target_subject_types": ("vip_cohort",),
        "minimum_evidence_coverage": 0.5,
        "minimum_source_diversity": 1,
        "minimum_sample_size": 5,
        "contradiction_tolerance": 0,
        "statement_template": "",
        "deferred": True,
        "deferred_id": "D-CISYN-02",
        "active": True,
        "version": "1",
        "routing_eligibility": False,
    },
)


def active_intake_policies_v1() -> list[dict[str, Any]]:
    return [dict(p) for p in INTAKE_POLICIES_V1 if p.get("active")]


def intake_policy_for_rule_v1(rule_key: str) -> dict[str, Any] | None:
    key = (rule_key or "").strip()
    for p in INTAKE_POLICIES_V1:
        if p["synthesis_rule_key"] == key:
            return dict(p)
    return None


def intake_registry_valid_v1() -> bool:
    keys = [p["synthesis_rule_key"] for p in INTAKE_POLICIES_V1]
    if len(keys) != len(set(keys)):
        return False
    return INTAKE_POLICY_REGISTRY_VERSION_V1 == "ciknow_v1" and len(keys) >= 8


def intake_registry_summary_v1() -> dict[str, Any]:
    active = active_intake_policies_v1()
    return {
        "registry_version": INTAKE_POLICY_REGISTRY_VERSION_V1,
        "policy_count": len(INTAKE_POLICIES_V1),
        "active_policy_count": len(active),
        "deferred_policy_count": sum(1 for p in active if p.get("deferred")),
        "valid": intake_registry_valid_v1(),
    }


__all__ = [
    "INTAKE_POLICIES_V1",
    "active_intake_policies_v1",
    "intake_policy_for_rule_v1",
    "intake_registry_valid_v1",
    "intake_registry_summary_v1",
]
