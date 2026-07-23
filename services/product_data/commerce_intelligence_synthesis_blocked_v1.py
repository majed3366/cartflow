# -*- coding: utf-8 -*-
"""
Commerce Intelligence Synthesis V1 — blocked reason codes and classification.

Blocked ≠ failed. Technical failures must use synthesis_state=failed.
"""
from __future__ import annotations

from typing import Any

# Governed blocked reason codes (cisyn_v1).
REASON_REQUIRED_SOURCE_CONTRACT_MISSING = "required_source_contract_missing"
REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE = "required_source_data_unavailable"
REASON_UNSUPPORTED_SOURCE_CONTRACT_VERSION = "unsupported_source_contract_version"
REASON_SUBJECT_IDENTITY_UNRESOLVED = "subject_identity_unresolved"
REASON_TIMESTAMP_AUTHORITY_UNAVAILABLE = "timestamp_authority_unavailable"
REASON_TEMPORAL_ALIGNMENT_FAILED = "temporal_alignment_failed"
REASON_SOURCE_MAPPING_MISSING = "source_mapping_missing"
REASON_CANONICAL_FIELD_MISSING = "canonical_field_missing"
REASON_SOURCE_CONTRACT_INVALID = "source_contract_invalid"
REASON_COMPARISON_COHORT_UNAVAILABLE = "comparison_cohort_unavailable"
REASON_UPSTREAM_TRUTH_INCOMPLETE = "upstream_truth_incomplete"
REASON_FEATURE_DEPENDENCY_DISABLED = "feature_dependency_disabled"
REASON_IMPLEMENTATION_ERROR = "implementation_error"

BLOCKED_REASON_CODES = frozenset(
    {
        REASON_REQUIRED_SOURCE_CONTRACT_MISSING,
        REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE,
        REASON_UNSUPPORTED_SOURCE_CONTRACT_VERSION,
        REASON_SUBJECT_IDENTITY_UNRESOLVED,
        REASON_TIMESTAMP_AUTHORITY_UNAVAILABLE,
        REASON_TEMPORAL_ALIGNMENT_FAILED,
        REASON_SOURCE_MAPPING_MISSING,
        REASON_CANONICAL_FIELD_MISSING,
        REASON_SOURCE_CONTRACT_INVALID,
        REASON_COMPARISON_COHORT_UNAVAILABLE,
        REASON_UPSTREAM_TRUTH_INCOMPLETE,
        REASON_FEATURE_DEPENDENCY_DISABLED,
        REASON_IMPLEMENTATION_ERROR,
    }
)

# Classification categories (closure validation).
CLASS_EXPECTED = "expected_truthful_block"
CLASS_DEFERRED = "temporary_upstream_dependency_gap"
CLASS_MAPPING_DEFECT = "mapping_or_contract_defect"
CLASS_RULE_DEFECT = "synthesis_rule_defect"
CLASS_RUNTIME_MISCLASSIFIED = "technical_runtime_misclassified_as_blocked"

BLOCKED_CLASSIFICATIONS = frozenset(
    {
        CLASS_EXPECTED,
        CLASS_DEFERRED,
        CLASS_MAPPING_DEFECT,
        CLASS_RULE_DEFECT,
        CLASS_RUNTIME_MISCLASSIFIED,
    }
)

# Owner layers for remediation tracking.
OWNER_CISYN = "commerce_intelligence_synthesis"
OWNER_HESITATION = "product_hesitation_mapping"
OWNER_PURCHASE = "product_purchase_mapping"
OWNER_COMMERCE_SIGNALS = "commerce_signals_v1"
OWNER_MESSAGE_STRATEGY = "message_strategy_classification"  # not yet a canonical contract
OWNER_VIP_COMPARISON = "vip_followup_comparison_cohorts"  # not yet a canonical contract
OWNER_KNOWLEDGE = "knowledge_foundation"

REASON_DESCRIPTIONS: dict[str, str] = {
    REASON_REQUIRED_SOURCE_CONTRACT_MISSING: (
        "A required source domain has no registered/accepted contract available "
        "for this synthesis refresh."
    ),
    REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE: (
        "The required source contract loaded successfully but contributed no "
        "in-window evidence for this candidate."
    ),
    REASON_UNSUPPORTED_SOURCE_CONTRACT_VERSION: (
        "The source adapter reported a contract version that is not accepted "
        "by cisrc_v1 for this rule."
    ),
    REASON_SUBJECT_IDENTITY_UNRESOLVED: (
        "A required subject identity could not be resolved from canonical inputs."
    ),
    REASON_TIMESTAMP_AUTHORITY_UNAVAILABLE: (
        "The semantic timestamp authority required by the source contract was missing."
    ),
    REASON_TEMPORAL_ALIGNMENT_FAILED: (
        "The requested time window is not allowed for this rule, or evidence "
        "timestamps could not be aligned within the governed window."
    ),
    REASON_SOURCE_MAPPING_MISSING: (
        "Canonical upstream evidence exists, but the governed mapping/link "
        "required by synthesis is missing."
    ),
    REASON_CANONICAL_FIELD_MISSING: (
        "A required canonical field was absent from an otherwise accepted contract payload."
    ),
    REASON_SOURCE_CONTRACT_INVALID: (
        "The source contract payload failed structural validation."
    ),
    REASON_COMPARISON_COHORT_UNAVAILABLE: (
        "A comparative claim requires governed comparison cohorts that are not materialized."
    ),
    REASON_UPSTREAM_TRUTH_INCOMPLETE: (
        "An upstream truth boundary required by the rule is incomplete."
    ),
    REASON_FEATURE_DEPENDENCY_DISABLED: (
        "A required feature-flagged upstream capability is disabled."
    ),
    REASON_IMPLEMENTATION_ERROR: (
        "An implementation defect was detected during blocked-path evaluation."
    ),
}


def blocked_reason_description_v1(reason_code: str) -> str:
    return REASON_DESCRIPTIONS.get(
        str(reason_code or ""),
        "Blocked for a governed reason; see blocked_reason_code.",
    )


def classify_blocked_candidate_v1(
    *,
    reason_code: str,
    synthesis_rule_key: str,
    missing_source_domains: list[str] | None = None,
    evidence_exists_unmapped: bool = False,
) -> dict[str, Any]:
    """
    Classify a blocked candidate into exactly one closure category.

    Returns classification, owner_layer, expected/deferred/defect flags, temporary.
    """
    code = str(reason_code or "").strip()
    rule = str(synthesis_rule_key or "").strip()
    missing = list(missing_source_domains or [])

    if code == REASON_IMPLEMENTATION_ERROR or evidence_exists_unmapped:
        return {
            "blocked_classification": CLASS_MAPPING_DEFECT
            if evidence_exists_unmapped
            else CLASS_RUNTIME_MISCLASSIFIED,
            "owner_layer": OWNER_CISYN,
            "is_expected": False,
            "is_temporary": False,
            "is_deferred": False,
            "is_defect": True,
            "approval": "NOT_APPROVABLE_UNTIL_FIXED",
        }

    if code == REASON_TEMPORAL_ALIGNMENT_FAILED:
        return {
            "blocked_classification": CLASS_EXPECTED,
            "owner_layer": OWNER_CISYN,
            "is_expected": True,
            "is_temporary": True,
            "is_deferred": False,
            "is_defect": False,
            "approval": "APPROVABLE",
        }

    if code == REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE:
        # Shipping hesitation with empty mapping in demo window = expected.
        owner = OWNER_HESITATION if "product_hesitation" in missing else OWNER_CISYN
        if "commerce_signals" in missing:
            owner = OWNER_COMMERCE_SIGNALS
        if "product_purchase" in missing and owner == OWNER_CISYN:
            owner = OWNER_PURCHASE
        return {
            "blocked_classification": CLASS_EXPECTED,
            "owner_layer": owner,
            "is_expected": True,
            "is_temporary": True,
            "is_deferred": False,
            "is_defect": False,
            "approval": "APPROVABLE",
        }

    if code == REASON_COMPARISON_COHORT_UNAVAILABLE or rule == "vip_followup_outcome":
        if code in {
            REASON_COMPARISON_COHORT_UNAVAILABLE,
            REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE,
            REASON_TEMPORAL_ALIGNMENT_FAILED,
        }:
            # VIP comparison cohorts are a tracked upstream gap when not temporal-only.
            if code == REASON_TEMPORAL_ALIGNMENT_FAILED:
                return {
                    "blocked_classification": CLASS_EXPECTED,
                    "owner_layer": OWNER_CISYN,
                    "is_expected": True,
                    "is_temporary": True,
                    "is_deferred": False,
                    "is_defect": False,
                    "approval": "APPROVABLE",
                }
            return {
                "blocked_classification": CLASS_DEFERRED,
                "owner_layer": OWNER_VIP_COMPARISON,
                "is_expected": True,
                "is_temporary": True,
                "is_deferred": True,
                "is_defect": False,
                "approval": "APPROVABLE_WITH_TRACKED_DEFERRED_ITEM",
            }

    if rule == "discount_message_weakness" and (
        code
        in {
            REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE,
            REASON_REQUIRED_SOURCE_CONTRACT_MISSING,
            REASON_CANONICAL_FIELD_MISSING,
            REASON_UPSTREAM_TRUTH_INCOMPLETE,
        }
        or "message_strategy" in ",".join(missing)
    ):
        return {
            "blocked_classification": CLASS_DEFERRED,
            "owner_layer": OWNER_MESSAGE_STRATEGY,
            "is_expected": True,
            "is_temporary": True,
            "is_deferred": True,
            "is_defect": False,
            "approval": "APPROVABLE_WITH_TRACKED_DEFERRED_ITEM",
        }

    if code == REASON_UNSUPPORTED_SOURCE_CONTRACT_VERSION:
        return {
            "blocked_classification": CLASS_MAPPING_DEFECT,
            "owner_layer": OWNER_CISYN,
            "is_expected": False,
            "is_temporary": False,
            "is_deferred": False,
            "is_defect": True,
            "approval": "NOT_APPROVABLE_UNTIL_FIXED",
        }

    if code == REASON_SUBJECT_IDENTITY_UNRESOLVED:
        return {
            "blocked_classification": CLASS_MAPPING_DEFECT,
            "owner_layer": OWNER_CISYN,
            "is_expected": False,
            "is_temporary": False,
            "is_deferred": False,
            "is_defect": True,
            "approval": "NOT_APPROVABLE_UNTIL_FIXED",
        }

    if code == REASON_SOURCE_MAPPING_MISSING:
        return {
            "blocked_classification": CLASS_MAPPING_DEFECT,
            "owner_layer": OWNER_CISYN,
            "is_expected": False,
            "is_temporary": False,
            "is_deferred": False,
            "is_defect": True,
            "approval": "NOT_APPROVABLE_UNTIL_FIXED",
        }

    # Default: treat as expected data unavailability if reason is governed.
    if code in BLOCKED_REASON_CODES:
        return {
            "blocked_classification": CLASS_EXPECTED,
            "owner_layer": OWNER_CISYN,
            "is_expected": True,
            "is_temporary": True,
            "is_deferred": False,
            "is_defect": False,
            "approval": "APPROVABLE",
        }

    return {
        "blocked_classification": CLASS_RUNTIME_MISCLASSIFIED,
        "owner_layer": OWNER_CISYN,
        "is_expected": False,
        "is_temporary": False,
        "is_deferred": False,
        "is_defect": True,
        "approval": "NOT_APPROVABLE",
    }


def map_legacy_block_reason_v1(
    *,
    legacy_reason: str,
    missing: list[str] | None = None,
) -> str:
    """Map pre-addendum failure_reason strings to governed codes."""
    raw = str(legacy_reason or "").strip()
    miss = list(missing or [])
    if raw == "window_not_allowed_for_rule":
        return REASON_TEMPORAL_ALIGNMENT_FAILED
    if raw == "missing_required_source":
        if any(m.startswith("message_strategy") for m in miss):
            return REASON_UPSTREAM_TRUTH_INCOMPLETE
        if "comparable_vip_followup_cohorts" in miss:
            return REASON_COMPARISON_COHORT_UNAVAILABLE
        return REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE
    if raw in BLOCKED_REASON_CODES:
        return raw
    if raw.startswith("exception:"):
        return REASON_IMPLEMENTATION_ERROR
    return REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE


__all__ = [
    "BLOCKED_REASON_CODES",
    "BLOCKED_CLASSIFICATIONS",
    "REASON_REQUIRED_SOURCE_CONTRACT_MISSING",
    "REASON_REQUIRED_SOURCE_DATA_UNAVAILABLE",
    "REASON_UNSUPPORTED_SOURCE_CONTRACT_VERSION",
    "REASON_SUBJECT_IDENTITY_UNRESOLVED",
    "REASON_TIMESTAMP_AUTHORITY_UNAVAILABLE",
    "REASON_TEMPORAL_ALIGNMENT_FAILED",
    "REASON_SOURCE_MAPPING_MISSING",
    "REASON_CANONICAL_FIELD_MISSING",
    "REASON_SOURCE_CONTRACT_INVALID",
    "REASON_COMPARISON_COHORT_UNAVAILABLE",
    "REASON_UPSTREAM_TRUTH_INCOMPLETE",
    "REASON_FEATURE_DEPENDENCY_DISABLED",
    "REASON_IMPLEMENTATION_ERROR",
    "CLASS_EXPECTED",
    "CLASS_DEFERRED",
    "CLASS_MAPPING_DEFECT",
    "CLASS_RULE_DEFECT",
    "CLASS_RUNTIME_MISCLASSIFIED",
    "OWNER_CISYN",
    "OWNER_HESITATION",
    "OWNER_MESSAGE_STRATEGY",
    "OWNER_VIP_COMPARISON",
    "blocked_reason_description_v1",
    "classify_blocked_candidate_v1",
    "map_legacy_block_reason_v1",
]
