# -*- coding: utf-8 -*-
"""Commerce Intelligence Synthesis Foundation V1 — catalog constants."""
from __future__ import annotations

SYNTHESIS_VERSION_V1 = "cisyn_v1"
GENERATION_VERSION_V1 = "cisyn_v1_gen"
RULE_REGISTRY_VERSION_V1 = "cisyn_v1"
SOURCE_CONTRACT_REGISTRY_VERSION_V1 = "cisrc_v1"
OUTPUT_CONTRACT_VERSION_V1 = "commerce_intelligence_synthesis_v1"

STATE_QUALIFIED = "qualified"
STATE_OBSERVING = "observing"
STATE_INSUFFICIENT = "insufficient_evidence"
STATE_CONFLICTING = "conflicting_evidence"
STATE_BLOCKED = "blocked"
STATE_EXPIRED = "expired"
STATE_SUPERSEDED = "superseded"
STATE_FAILED = "failed"

SYNTHESIS_STATES = frozenset(
    {
        STATE_QUALIFIED,
        STATE_OBSERVING,
        STATE_INSUFFICIENT,
        STATE_CONFLICTING,
        STATE_BLOCKED,
        STATE_EXPIRED,
        STATE_SUPERSEDED,
        STATE_FAILED,
    }
)

SUBJECT_STORE = "store"
SUBJECT_PRODUCT = "product"
SUBJECT_HESITATION = "hesitation_reason"
SUBJECT_RECOVERY_STRATEGY = "recovery_strategy"
SUBJECT_VIP_COHORT = "vip_cohort"
SUBJECT_COMMUNICATION = "communication_cohort"

SUBJECT_TYPES = frozenset(
    {
        SUBJECT_STORE,
        SUBJECT_PRODUCT,
        SUBJECT_HESITATION,
        SUBJECT_RECOVERY_STRATEGY,
        SUBJECT_VIP_COHORT,
        SUBJECT_COMMUNICATION,
    }
)

PATTERN_PRODUCT_INTEREST_WITHOUT_PURCHASE = "product_interest_without_purchase"
PATTERN_HIGH_TRAFFIC_WEAK_CONVERSION = "high_traffic_weak_conversion"
PATTERN_WHATSAPP_RETURN_WITHOUT_PURCHASE = "whatsapp_return_without_purchase"
PATTERN_SHIPPING_HESITATION_RECOVERY = "shipping_hesitation_recovery_outcome"
PATTERN_REPEATED_INTEREST = "repeated_interest_pattern"
PATTERN_DISCOUNT_MESSAGE_WEAKNESS = "discount_message_weakness"
PATTERN_VIP_FOLLOWUP_OUTCOME = "vip_followup_outcome"
PATTERN_INSUFFICIENT_EVIDENCE = "insufficient_evidence_pattern"
PATTERN_CONFLICTING_EVIDENCE = "conflicting_evidence_pattern"
PATTERN_RECOVERY_INFLUENCE_BOUNDARY = "recovery_influence_boundary"

PATTERN_TYPES = frozenset(
    {
        PATTERN_PRODUCT_INTEREST_WITHOUT_PURCHASE,
        PATTERN_HIGH_TRAFFIC_WEAK_CONVERSION,
        PATTERN_WHATSAPP_RETURN_WITHOUT_PURCHASE,
        PATTERN_SHIPPING_HESITATION_RECOVERY,
        PATTERN_REPEATED_INTEREST,
        PATTERN_DISCOUNT_MESSAGE_WEAKNESS,
        PATTERN_VIP_FOLLOWUP_OUTCOME,
        PATTERN_INSUFFICIENT_EVIDENCE,
        PATTERN_CONFLICTING_EVIDENCE,
        PATTERN_RECOVERY_INFLUENCE_BOUNDARY,
    }
)

DIRECTION_GAP = "conversion_gap"
DIRECTION_RETURN_WITHOUT_PURCHASE = "return_without_purchase"
DIRECTION_REPEATED_INTEREST = "repeated_interest"
DIRECTION_INSUFFICIENT = "insufficient"
DIRECTION_CONFLICTING = "conflicting"
DIRECTION_INFLUENCE_BOUNDARY = "influence_boundary"
DIRECTION_COMPARISON = "cohort_comparison"
DIRECTION_OBSERVING = "observing"

WINDOW_LENGTH_DAYS: dict[str, int] = {
    "d7": 7,
    "d14": 14,
    "d30": 30,
    "d60": 60,
}

# Map synthesis windows onto Knowledge Foundation windows (canonical upstream).
KNOWLEDGE_WINDOW_MAP: dict[str, str] = {
    "d7": "d7",
    "d14": "d7",
    "d30": "d30",
    "d60": "d90",
}

SHIPPING_REASON_TOKENS = frozenset(
    {
        "shipping",
        "shipping_cost",
        "shipping_price",
        "delivery",
        "delivery_cost",
        "delivery_fee",
        "high_shipping",
    }
)

RECOVERY_CLASSIFICATIONS = (
    "confirmed_recovery",
    "high_confidence",
    "possible_influence",
    "unattributed_purchase",
)

__all__ = [
    "SYNTHESIS_VERSION_V1",
    "GENERATION_VERSION_V1",
    "RULE_REGISTRY_VERSION_V1",
    "SOURCE_CONTRACT_REGISTRY_VERSION_V1",
    "OUTPUT_CONTRACT_VERSION_V1",
    "STATE_QUALIFIED",
    "STATE_OBSERVING",
    "STATE_INSUFFICIENT",
    "STATE_CONFLICTING",
    "STATE_BLOCKED",
    "STATE_EXPIRED",
    "STATE_SUPERSEDED",
    "STATE_FAILED",
    "SYNTHESIS_STATES",
    "SUBJECT_STORE",
    "SUBJECT_PRODUCT",
    "SUBJECT_HESITATION",
    "SUBJECT_RECOVERY_STRATEGY",
    "SUBJECT_VIP_COHORT",
    "SUBJECT_COMMUNICATION",
    "SUBJECT_TYPES",
    "PATTERN_PRODUCT_INTEREST_WITHOUT_PURCHASE",
    "PATTERN_HIGH_TRAFFIC_WEAK_CONVERSION",
    "PATTERN_WHATSAPP_RETURN_WITHOUT_PURCHASE",
    "PATTERN_SHIPPING_HESITATION_RECOVERY",
    "PATTERN_REPEATED_INTEREST",
    "PATTERN_DISCOUNT_MESSAGE_WEAKNESS",
    "PATTERN_VIP_FOLLOWUP_OUTCOME",
    "PATTERN_INSUFFICIENT_EVIDENCE",
    "PATTERN_CONFLICTING_EVIDENCE",
    "PATTERN_RECOVERY_INFLUENCE_BOUNDARY",
    "PATTERN_TYPES",
    "DIRECTION_GAP",
    "DIRECTION_RETURN_WITHOUT_PURCHASE",
    "DIRECTION_REPEATED_INTEREST",
    "DIRECTION_INSUFFICIENT",
    "DIRECTION_CONFLICTING",
    "DIRECTION_INFLUENCE_BOUNDARY",
    "DIRECTION_COMPARISON",
    "DIRECTION_OBSERVING",
    "WINDOW_LENGTH_DAYS",
    "KNOWLEDGE_WINDOW_MAP",
    "SHIPPING_REASON_TOKENS",
    "RECOVERY_CLASSIFICATIONS",
]
