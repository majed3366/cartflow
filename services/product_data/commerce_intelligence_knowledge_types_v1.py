# -*- coding: utf-8 -*-
"""Commerce Intelligence → Knowledge Integration V1 — catalog constants."""
from __future__ import annotations

INTAKE_VERSION_V1 = "ciknow_v1"
GENERATION_VERSION_V1 = "ciknow_v1_gen"
INTAKE_POLICY_REGISTRY_VERSION_V1 = "ciknow_v1"
INPUT_CONTRACT_VERSION_V1 = "commerce_intelligence_synthesis_v1"
SOURCE_TYPE_CISYN = "commerce_intelligence_synthesis"
KNOWLEDGE_VERSION_CIKNOW = "ciknow_v1"

# Knowledge types produced from synthesis (not ECF types).
KT_HESITATION_RECOVERY = "hesitation_recovery_pattern"
KT_PRODUCT_INTEREST_GAP = "product_interest_conversion_gap"
KT_WA_RETURN = "communication_return_without_purchase"
KT_TRAFFIC_GAP = "traffic_conversion_gap"
KT_REPEATED_INTEREST = "repeated_interest_unresolved"
KT_RECOVERY_INFLUENCE = "recovery_influence_classification"
KT_EVIDENCE_GAP = "commercial_evidence_gap"
KT_EVIDENCE_CONFLICT = "commercial_evidence_conflict"

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

# Intake outcomes for accounting.
OUTCOME_CREATED = "created"
OUTCOME_UPDATED = "updated"
OUTCOME_UNCHANGED = "unchanged"
OUTCOME_ABSTAINED = "abstained"
OUTCOME_REJECTED = "rejected"
OUTCOME_DEFERRED = "deferred"
OUTCOME_FAILED = "failed"

# Rejection / abstention reason codes.
REASON_STATE_NOT_ELIGIBLE = "synthesis_state_not_eligible"
REASON_POLICY_MISSING = "intake_policy_missing"
REASON_COVERAGE = "evidence_coverage_below_threshold"
REASON_DIVERSITY = "source_diversity_below_threshold"
REASON_SAMPLE = "sample_not_mature"
REASON_EXPIRED = "synthesis_expired"
REASON_CLAIM_BOUNDARY = "claim_boundary_invalid"
REASON_SUBJECT = "subject_mapping_failed"
REASON_TYPE_UNSUPPORTED = "knowledge_type_unsupported"
REASON_CONTRACT = "source_contract_version_unsupported"
REASON_DUP = "duplicate_current_prevented"
REASON_TECHNICAL = "technical_failure"
REASON_DEFERRED_DEP = "deferred_dependency"
REASON_BLOCKED = "blocked_synthesis_not_eligible"
REASON_FAILED_SYN = "failed_synthesis_not_eligible"
REASON_OBSERVING = "observing_not_established_knowledge"

__all__ = [
    "INTAKE_VERSION_V1",
    "GENERATION_VERSION_V1",
    "INTAKE_POLICY_REGISTRY_VERSION_V1",
    "INPUT_CONTRACT_VERSION_V1",
    "SOURCE_TYPE_CISYN",
    "KNOWLEDGE_VERSION_CIKNOW",
    "KT_HESITATION_RECOVERY",
    "KT_PRODUCT_INTEREST_GAP",
    "KT_WA_RETURN",
    "KT_TRAFFIC_GAP",
    "KT_REPEATED_INTEREST",
    "KT_RECOVERY_INFLUENCE",
    "KT_EVIDENCE_GAP",
    "KT_EVIDENCE_CONFLICT",
    "CIKNOW_KNOWLEDGE_TYPES",
    "OUTCOME_CREATED",
    "OUTCOME_UPDATED",
    "OUTCOME_UNCHANGED",
    "OUTCOME_ABSTAINED",
    "OUTCOME_REJECTED",
    "OUTCOME_DEFERRED",
    "OUTCOME_FAILED",
    "REASON_STATE_NOT_ELIGIBLE",
    "REASON_POLICY_MISSING",
    "REASON_COVERAGE",
    "REASON_DIVERSITY",
    "REASON_SAMPLE",
    "REASON_EXPIRED",
    "REASON_CLAIM_BOUNDARY",
    "REASON_SUBJECT",
    "REASON_TYPE_UNSUPPORTED",
    "REASON_CONTRACT",
    "REASON_DUP",
    "REASON_TECHNICAL",
    "REASON_DEFERRED_DEP",
    "REASON_BLOCKED",
    "REASON_FAILED_SYN",
    "REASON_OBSERVING",
]
