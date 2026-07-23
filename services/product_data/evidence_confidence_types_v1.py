# -*- coding: utf-8 -*-
"""
Evidence Confidence Foundation V1 — catalog constants.

Confidence about assembled evidence quality only. No guidance or health.
"""
from __future__ import annotations

CONFIDENCE_VERSION_V1 = "ecf_v1"
EVALUATOR_VERSION_V1 = "ecf_v1_eval"

LEVEL_LOW = "low"
LEVEL_MEDIUM = "medium"
LEVEL_HIGH = "high"
LEVEL_VERY_HIGH = "very_high"

CONFIDENCE_LEVELS = frozenset(
    {LEVEL_LOW, LEVEL_MEDIUM, LEVEL_HIGH, LEVEL_VERY_HIGH}
)

# Evaluation catalog (not a Metrics read) — keys expected for completeness.
CORE_EVIDENCE_METRIC_KEYS: tuple[str, ...] = (
    "cart_added_count",
    "cart_abandoned_count",
    "purchase_count",
    "evidence_linked_count",
)


def confidence_level_for_score(score: int) -> str:
    s = max(0, min(100, int(score)))
    if s >= 80:
        return LEVEL_VERY_HIGH
    if s >= 60:
        return LEVEL_HIGH
    if s >= 40:
        return LEVEL_MEDIUM
    return LEVEL_LOW


__all__ = [
    "CONFIDENCE_VERSION_V1",
    "EVALUATOR_VERSION_V1",
    "LEVEL_LOW",
    "LEVEL_MEDIUM",
    "LEVEL_HIGH",
    "LEVEL_VERY_HIGH",
    "CONFIDENCE_LEVELS",
    "CORE_EVIDENCE_METRIC_KEYS",
    "confidence_level_for_score",
]
