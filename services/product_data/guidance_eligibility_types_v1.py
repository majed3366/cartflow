# -*- coding: utf-8 -*-
"""
Guidance Eligibility Foundation V1 — catalog constants.

Permission governance only. No guidance content.
"""
from __future__ import annotations

ELIGIBILITY_VERSION_V1 = "gef_v1"
EVALUATOR_VERSION_V1 = "gef_v1_eval"

STATUS_ELIGIBLE = "eligible"
STATUS_INSUFFICIENT_KNOWLEDGE = "insufficient_knowledge"
STATUS_INSUFFICIENT_CONFIDENCE = "insufficient_confidence"
STATUS_CONFLICTING_KNOWLEDGE = "conflicting_knowledge"
STATUS_EXPIRED_KNOWLEDGE = "expired_knowledge"
STATUS_PENDING_OBSERVATION = "pending_observation"

ELIGIBILITY_STATUSES = frozenset(
    {
        STATUS_ELIGIBLE,
        STATUS_INSUFFICIENT_KNOWLEDGE,
        STATUS_INSUFFICIENT_CONFIDENCE,
        STATUS_CONFLICTING_KNOWLEDGE,
        STATUS_EXPIRED_KNOWLEDGE,
        STATUS_PENDING_OBSERVATION,
    }
)

# Minimum: evidence_quality + metric_trend_observation
REQUIRED_KNOWLEDGE_COUNT_V1 = 2

HIGH_CONFIDENCE_LEVELS = frozenset({"high", "very_high"})

BLOCK_NO_KNOWLEDGE = "no_knowledge"
BLOCK_EXPIRED = "expired_knowledge"
BLOCK_CONFLICT = "conflict_flag_present"
BLOCK_CONFIDENCE = "confidence_below_high"
BLOCK_MISSING_QUALITY = "missing_evidence_quality"
BLOCK_MISSING_TREND = "missing_trend_observation"
BLOCK_BELOW_COUNT = "below_required_count"

__all__ = [
    "ELIGIBILITY_VERSION_V1",
    "EVALUATOR_VERSION_V1",
    "STATUS_ELIGIBLE",
    "STATUS_INSUFFICIENT_KNOWLEDGE",
    "STATUS_INSUFFICIENT_CONFIDENCE",
    "STATUS_CONFLICTING_KNOWLEDGE",
    "STATUS_EXPIRED_KNOWLEDGE",
    "STATUS_PENDING_OBSERVATION",
    "ELIGIBILITY_STATUSES",
    "REQUIRED_KNOWLEDGE_COUNT_V1",
    "HIGH_CONFIDENCE_LEVELS",
    "BLOCK_NO_KNOWLEDGE",
    "BLOCK_EXPIRED",
    "BLOCK_CONFLICT",
    "BLOCK_CONFIDENCE",
    "BLOCK_MISSING_QUALITY",
    "BLOCK_MISSING_TREND",
    "BLOCK_BELOW_COUNT",
]
