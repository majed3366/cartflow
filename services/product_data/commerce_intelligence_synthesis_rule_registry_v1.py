# -*- coding: utf-8 -*-
"""
Commerce Intelligence Synthesis — rule registry (cisyn_v1).

Code-owned. No page/SQL/frontend/Guidance scattering of pattern logic.
"""
from __future__ import annotations

from typing import Any

from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    PATTERN_CONFLICTING_EVIDENCE,
    PATTERN_DISCOUNT_MESSAGE_WEAKNESS,
    PATTERN_HIGH_TRAFFIC_WEAK_CONVERSION,
    PATTERN_INSUFFICIENT_EVIDENCE,
    PATTERN_PRODUCT_INTEREST_WITHOUT_PURCHASE,
    PATTERN_RECOVERY_INFLUENCE_BOUNDARY,
    PATTERN_REPEATED_INTEREST,
    PATTERN_SHIPPING_HESITATION_RECOVERY,
    PATTERN_VIP_FOLLOWUP_OUTCOME,
    PATTERN_WHATSAPP_RETURN_WITHOUT_PURCHASE,
    RULE_REGISTRY_VERSION_V1,
    SUBJECT_HESITATION,
    SUBJECT_PRODUCT,
    SUBJECT_RECOVERY_STRATEGY,
    SUBJECT_STORE,
    SUBJECT_VIP_COHORT,
)

SYNTHESIS_RULES_V1: tuple[dict[str, Any], ...] = (
    {
        "synthesis_rule_key": "product_interest_without_purchase",
        "description": "Products with meaningful cart interest and weak purchase completion.",
        "commercial_question": (
            "Which products attract meaningful interest but weak purchase completion?"
        ),
        "pattern_type": PATTERN_PRODUCT_INTEREST_WITHOUT_PURCHASE,
        "supported_subject_types": (SUBJECT_PRODUCT,),
        "required_source_domains": ("knowledge",),
        "optional_source_domains": ("product_purchase",),
        "prohibited_source_domains": (),
        "minimum_sample_size": 1,
        "minimum_source_coverage": 1,
        "minimum_observation_window_days": 7,
        "maximum_evidence_age_days": 90,
        "allowed_windows": ("d7", "d14", "d30", "d60"),
        "priority": 10,
        "version": "1",
        "active": True,
        "prohibited_claims": (
            "root_cause_known",
            "price_is_the_cause",
            "lowering_price_will_increase_purchases",
        ),
    },
    {
        "synthesis_rule_key": "high_traffic_weak_conversion",
        "description": "Store engagement exists while purchase conversion remains weak.",
        "commercial_question": (
            "Is commercial weakness caused by low traffic, or later in the journey?"
        ),
        "pattern_type": PATTERN_HIGH_TRAFFIC_WEAK_CONVERSION,
        "supported_subject_types": (SUBJECT_STORE,),
        "required_source_domains": ("knowledge",),
        "optional_source_domains": ("product_purchase",),
        "prohibited_source_domains": (),
        "minimum_sample_size": 1,
        "minimum_source_coverage": 1,
        "minimum_observation_window_days": 7,
        "maximum_evidence_age_days": 90,
        "allowed_windows": ("d7", "d14", "d30", "d60"),
        "priority": 20,
        "version": "1",
        "active": True,
        "prohibited_claims": (
            "root_cause_known",
            "traffic_is_insufficient",
            "funnel_stage_diagnosed",
        ),
    },
    {
        "synthesis_rule_key": "whatsapp_return_without_purchase",
        "description": "Customers return after WhatsApp contact without purchase completion.",
        "commercial_question": (
            "Are customers returning after WhatsApp but not completing purchase?"
        ),
        "pattern_type": PATTERN_WHATSAPP_RETURN_WITHOUT_PURCHASE,
        "supported_subject_types": (SUBJECT_STORE,),
        "required_source_domains": ("commerce_signals",),
        "optional_source_domains": ("knowledge", "product_purchase"),
        "prohibited_source_domains": (),
        "minimum_sample_size": 3,
        "minimum_source_coverage": 1,
        "minimum_observation_window_days": 7,
        "maximum_evidence_age_days": 60,
        "allowed_windows": ("d7", "d14", "d30", "d60"),
        "priority": 30,
        "version": "1",
        "active": True,
        "prohibited_claims": (
            "whatsapp_failed",
            "whatsapp_caused_non_purchase",
            "message_content_is_the_cause",
        ),
    },
    {
        "synthesis_rule_key": "shipping_hesitation_recovery_outcome",
        "description": "Outcomes after shipping-related hesitation expressions.",
        "commercial_question": (
            "What usually happens after customers express shipping-related hesitation?"
        ),
        "pattern_type": PATTERN_SHIPPING_HESITATION_RECOVERY,
        "supported_subject_types": (SUBJECT_HESITATION,),
        "required_source_domains": ("product_hesitation",),
        "optional_source_domains": (
            "product_purchase",
            "commerce_signals",
            "knowledge",
        ),
        "prohibited_source_domains": (),
        "minimum_sample_size": 3,
        "minimum_source_coverage": 1,
        "minimum_observation_window_days": 7,
        "maximum_evidence_age_days": 60,
        "allowed_windows": ("d7", "d14", "d30", "d60"),
        "priority": 40,
        "version": "1",
        "active": True,
        "prohibited_claims": (
            "shipping_price_is_confirmed_cause",
            "lowering_shipping_will_increase_purchases",
        ),
    },
    {
        "synthesis_rule_key": "repeated_interest_pattern",
        "description": "Repeated product/cart interest without purchase resolution.",
        "commercial_question": (
            "Are customers repeatedly returning to a product or cart without purchasing?"
        ),
        "pattern_type": PATTERN_REPEATED_INTEREST,
        "supported_subject_types": (SUBJECT_PRODUCT, SUBJECT_STORE),
        "required_source_domains": ("knowledge",),
        "optional_source_domains": ("product_purchase",),
        "prohibited_source_domains": (),
        "minimum_sample_size": 1,
        "minimum_source_coverage": 1,
        "minimum_observation_window_days": 7,
        "maximum_evidence_age_days": 90,
        "allowed_windows": ("d7", "d14", "d30", "d60"),
        "priority": 50,
        "version": "1",
        "active": True,
        "prohibited_claims": ("intent_to_purchase_confirmed", "root_cause_known"),
    },
    {
        "synthesis_rule_key": "discount_message_weakness",
        "description": "Discount-oriented recovery outcomes for a hesitation condition.",
        "commercial_question": (
            "Do discount-oriented recovery messages show weak outcomes "
            "for a specific condition?"
        ),
        "pattern_type": PATTERN_DISCOUNT_MESSAGE_WEAKNESS,
        "supported_subject_types": (SUBJECT_RECOVERY_STRATEGY,),
        "required_source_domains": ("commerce_signals", "product_hesitation"),
        "optional_source_domains": ("product_purchase",),
        "prohibited_source_domains": (),
        "minimum_sample_size": 5,
        "minimum_source_coverage": 2,
        "minimum_observation_window_days": 14,
        "maximum_evidence_age_days": 60,
        "allowed_windows": ("d14", "d30", "d60"),
        "priority": 60,
        "version": "1",
        "active": True,
        "prohibited_claims": ("discounts_never_work", "discount_is_confirmed_cause"),
    },
    {
        "synthesis_rule_key": "vip_followup_outcome",
        "description": "VIP carts after automated versus merchant-led follow-up.",
        "commercial_question": (
            "How do VIP carts behave after automated versus merchant-led follow-up?"
        ),
        "pattern_type": PATTERN_VIP_FOLLOWUP_OUTCOME,
        "supported_subject_types": (SUBJECT_VIP_COHORT,),
        "required_source_domains": ("commerce_signals",),
        "optional_source_domains": ("knowledge", "product_purchase"),
        "prohibited_source_domains": (),
        "minimum_sample_size": 5,
        "minimum_source_coverage": 1,
        "minimum_observation_window_days": 14,
        "maximum_evidence_age_days": 60,
        "allowed_windows": ("d14", "d30", "d60"),
        "priority": 70,
        "version": "1",
        "active": True,
        "requires_comparison": True,
        "prohibited_claims": (
            "merchant_followup_always_better",
            "causality_confirmed",
        ),
    },
    {
        "synthesis_rule_key": "insufficient_evidence_store",
        "description": "Store-level inability to support a commercial conclusion yet.",
        "commercial_question": "Is CartFlow able to support a commercial conclusion yet?",
        "pattern_type": PATTERN_INSUFFICIENT_EVIDENCE,
        "supported_subject_types": (SUBJECT_STORE,),
        "required_source_domains": ("knowledge",),
        "optional_source_domains": (
            "product_hesitation",
            "product_purchase",
            "commerce_signals",
        ),
        "prohibited_source_domains": (),
        "minimum_sample_size": 0,
        "minimum_source_coverage": 0,
        "minimum_observation_window_days": 1,
        "maximum_evidence_age_days": 90,
        "allowed_windows": ("d7", "d14", "d30", "d60"),
        "priority": 80,
        "version": "1",
        "active": True,
        "prohibited_claims": ("conclusion_is_reliable",),
    },
    {
        "synthesis_rule_key": "conflicting_evidence_store",
        "description": "Material disagreement across source domains.",
        "commercial_question": "Do source domains disagree materially?",
        "pattern_type": PATTERN_CONFLICTING_EVIDENCE,
        "supported_subject_types": (SUBJECT_STORE,),
        "required_source_domains": ("knowledge",),
        "optional_source_domains": ("product_hesitation", "commerce_signals"),
        "prohibited_source_domains": (),
        "minimum_sample_size": 0,
        "minimum_source_coverage": 1,
        "minimum_observation_window_days": 1,
        "maximum_evidence_age_days": 90,
        "allowed_windows": ("d7", "d14", "d30", "d60"),
        "priority": 90,
        "version": "1",
        "active": True,
        "prohibited_claims": ("single_explanation_reliable",),
    },
    {
        "synthesis_rule_key": "recovery_influence_boundary",
        "description": "Preserve purchase influence classifications without collapsing them.",
        "commercial_question": (
            "Is a purchase confirmed, plausibly influenced, or unattributed?"
        ),
        "pattern_type": PATTERN_RECOVERY_INFLUENCE_BOUNDARY,
        "supported_subject_types": (SUBJECT_STORE,),
        "required_source_domains": ("commerce_signals",),
        "optional_source_domains": ("product_purchase", "knowledge"),
        "prohibited_source_domains": (),
        "minimum_sample_size": 1,
        "minimum_source_coverage": 1,
        "minimum_observation_window_days": 7,
        "maximum_evidence_age_days": 60,
        "allowed_windows": ("d7", "d14", "d30", "d60"),
        "priority": 100,
        "version": "1",
        "active": True,
        "prohibited_claims": (
            "all_purchases_are_recovered_revenue",
            "collapsed_influence_claim",
        ),
    },
)


def active_synthesis_rules_v1() -> list[dict[str, Any]]:
    return [dict(r) for r in SYNTHESIS_RULES_V1 if r.get("active")]


def synthesis_rule_by_key_v1(rule_key: str) -> dict[str, Any] | None:
    key = (rule_key or "").strip()
    for row in SYNTHESIS_RULES_V1:
        if row["synthesis_rule_key"] == key:
            return dict(row)
    return None


def rule_registry_valid_v1() -> bool:
    keys = [r["synthesis_rule_key"] for r in SYNTHESIS_RULES_V1]
    if len(keys) != len(set(keys)):
        return False
    if RULE_REGISTRY_VERSION_V1 != "cisyn_v1":
        return False
    return len(active_synthesis_rules_v1()) >= 8


def rule_registry_summary_v1() -> dict[str, Any]:
    active = active_synthesis_rules_v1()
    return {
        "registry_version": RULE_REGISTRY_VERSION_V1,
        "rule_count": len(SYNTHESIS_RULES_V1),
        "active_rule_count": len(active),
        "rule_keys": [r["synthesis_rule_key"] for r in active],
        "valid": rule_registry_valid_v1(),
    }


__all__ = [
    "SYNTHESIS_RULES_V1",
    "active_synthesis_rules_v1",
    "synthesis_rule_by_key_v1",
    "rule_registry_valid_v1",
    "rule_registry_summary_v1",
]
