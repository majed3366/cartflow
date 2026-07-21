# -*- coding: utf-8 -*-
"""Commercial Guidance Integration Foundation V1 — Knowledge intake catalog (cguide_v1)."""
from __future__ import annotations

from services.product_data.commerce_intelligence_knowledge_types_v1 import (
    KT_EVIDENCE_CONFLICT,
    KT_EVIDENCE_GAP,
    KT_HESITATION_RECOVERY,
    KT_PRODUCT_INTEREST_GAP,
    KT_RECOVERY_INFLUENCE,
    KT_REPEATED_INTEREST,
    KT_TRAFFIC_GAP,
    KT_WA_RETURN,
)

GUIDANCE_VERSION_V1 = "cguide_v1"
GENERATION_VERSION_V1 = "cguide_v1_gen"
REGISTRY_VERSION_V1 = "cguide_v1"
INPUT_CONTRACT_VERSION_V1 = "knowledge_statements_current_v1"
SOURCE_CONTRACT_VERSION_V1 = "knowledge_statements_v1"
GUIDANCE_SCOPE_V1 = "cguide_commercial_v1"
KNOWLEDGE_VERSION_FILTER = "ciknow_v1"

# Eligibility / outcome statuses for Knowledge → Guidance.
ELIG_ELIGIBLE = "eligible"
ELIG_OBSERVE_ONLY = "observe_only"
ELIG_INSUFFICIENT = "insufficient_evidence"
ELIG_CONFLICTING = "conflicting"
ELIG_EXPIRED = "expired"
ELIG_BLOCKED = "blocked"
ELIG_ABSTAIN = "abstain"

# Accounting outcomes (every current Knowledge input maps to exactly one).
OUTCOME_CREATED = "created"
OUTCOME_UPDATED = "updated"
OUTCOME_UNCHANGED = "unchanged"
OUTCOME_OBSERVE_ONLY = "observe_only"
OUTCOME_EVIDENCE_GAP = "evidence_gap"
OUTCOME_CONFLICTING = "conflicting"
OUTCOME_ABSTAINED = "abstained"
OUTCOME_REJECTED = "rejected"
OUTCOME_EXPIRED = "expired"
OUTCOME_FAILED = "failed"

# Guidance keys (registry-owned).
KEY_INVESTIGATE_SHIPPING = "investigate_shipping_checkout_friction"
KEY_REVIEW_PRODUCT_GAP = "review_product_interest_conversion_gap"
KEY_REVIEW_WA_RETURN = "review_whatsapp_return_journey"
KEY_INVESTIGATE_CONVERSION = "investigate_conversion_bottlenecks"
KEY_REVIEW_REPEATED = "review_unresolved_hesitation"
KEY_PRESERVE_INFLUENCE = "preserve_recovery_influence_boundary"
KEY_COLLECT_EVIDENCE = "collect_additional_evidence"
KEY_DELAY_CONFLICT = "delay_until_evidence_clearer"
KEY_NO_GUIDANCE = "no_guidance"

GUIDANCE_KEYS = frozenset(
    {
        KEY_INVESTIGATE_SHIPPING,
        KEY_REVIEW_PRODUCT_GAP,
        KEY_REVIEW_WA_RETURN,
        KEY_INVESTIGATE_CONVERSION,
        KEY_REVIEW_REPEATED,
        KEY_PRESERVE_INFLUENCE,
        KEY_COLLECT_EVIDENCE,
        KEY_DELAY_CONFLICT,
        KEY_NO_GUIDANCE,
    }
)

CIKNOW_KNOWLEDGE_TYPES = frozenset(
    {
        KT_HESITATION_RECOVERY,
        KT_PRODUCT_INTEREST_GAP,
        KT_WA_RETURN,
        KT_TRAFFIC_GAP,
        KT_REPEATED_INTEREST,
        KT_RECOVERY_INFLUENCE,
        KT_EVIDENCE_GAP,
        KT_EVIDENCE_CONFLICT,
    }
)

REASON_POLICY_MISSING = "intake_policy_missing"
REASON_KNOWLEDGE_TYPE_UNSUPPORTED = "knowledge_type_unsupported"
REASON_EXPIRED = "knowledge_expired"
REASON_CLAIM_BOUNDARY = "claim_boundary_invalid"
REASON_TECHNICAL = "technical_failure"
REASON_FLAG_OFF = "guidance_integration_disabled"
REASON_NOT_CURRENT = "knowledge_not_current"
REASON_CONTRACT = "source_contract_version_unsupported"

CAUSAL_INFLATION_TOKENS = (
    "caused",
    "will increase",
    "will improve",
    "definitely",
    "guaranteed",
    "reduce shipping cost",
    "lower the price",
    "increase advertising",
    "whatsapp messages are ineffective",
)

__all__ = [
    "GUIDANCE_VERSION_V1",
    "GENERATION_VERSION_V1",
    "REGISTRY_VERSION_V1",
    "INPUT_CONTRACT_VERSION_V1",
    "SOURCE_CONTRACT_VERSION_V1",
    "GUIDANCE_SCOPE_V1",
    "KNOWLEDGE_VERSION_FILTER",
    "ELIG_ELIGIBLE",
    "ELIG_OBSERVE_ONLY",
    "ELIG_INSUFFICIENT",
    "ELIG_CONFLICTING",
    "ELIG_EXPIRED",
    "ELIG_BLOCKED",
    "ELIG_ABSTAIN",
    "OUTCOME_CREATED",
    "OUTCOME_UPDATED",
    "OUTCOME_UNCHANGED",
    "OUTCOME_OBSERVE_ONLY",
    "OUTCOME_EVIDENCE_GAP",
    "OUTCOME_CONFLICTING",
    "OUTCOME_ABSTAINED",
    "OUTCOME_REJECTED",
    "OUTCOME_EXPIRED",
    "OUTCOME_FAILED",
    "KEY_INVESTIGATE_SHIPPING",
    "KEY_REVIEW_PRODUCT_GAP",
    "KEY_REVIEW_WA_RETURN",
    "KEY_INVESTIGATE_CONVERSION",
    "KEY_REVIEW_REPEATED",
    "KEY_PRESERVE_INFLUENCE",
    "KEY_COLLECT_EVIDENCE",
    "KEY_DELAY_CONFLICT",
    "KEY_NO_GUIDANCE",
    "GUIDANCE_KEYS",
    "CIKNOW_KNOWLEDGE_TYPES",
    "REASON_POLICY_MISSING",
    "REASON_KNOWLEDGE_TYPE_UNSUPPORTED",
    "REASON_EXPIRED",
    "REASON_CLAIM_BOUNDARY",
    "REASON_TECHNICAL",
    "REASON_FLAG_OFF",
    "REASON_NOT_CURRENT",
    "REASON_CONTRACT",
    "CAUSAL_INFLATION_TOKENS",
    "KT_HESITATION_RECOVERY",
    "KT_PRODUCT_INTEREST_GAP",
    "KT_WA_RETURN",
    "KT_TRAFFIC_GAP",
    "KT_REPEATED_INTEREST",
    "KT_RECOVERY_INFLUENCE",
    "KT_EVIDENCE_GAP",
    "KT_EVIDENCE_CONFLICT",
]
