# -*- coding: utf-8 -*-
"""Business Findings Lifecycle V1 — constants and states."""
from __future__ import annotations

BFL_VERSION_V1 = "bfl_v1"
BFL_GENERATION_VERSION_V1 = "bfl_v1_gen"
BFL_TABLE = "business_findings"

# Explicit lifecycle — no skips.
LS_DETECTED = "detected"
LS_VALIDATED = "validated"
LS_PERSISTED = "persisted"
LS_KNOWLEDGE_ROUTED = "knowledge_routed"
LS_OT_ROUTED = "operational_truth_routed"
LS_SURFACE_ELIGIBLE = "surface_eligible"
LS_DISPLAYED = "displayed"
LS_RESOLVED = "resolved"
LS_ARCHIVED = "archived"

LIFECYCLE_ORDER_V1: tuple[str, ...] = (
    LS_DETECTED,
    LS_VALIDATED,
    LS_PERSISTED,
    LS_KNOWLEDGE_ROUTED,
    LS_OT_ROUTED,
    LS_SURFACE_ELIGIBLE,
    LS_DISPLAYED,
    LS_RESOLVED,
    LS_ARCHIVED,
)

# Visibility
VIS_HIDDEN = "hidden"
VIS_ELIGIBLE = "eligible"
VIS_DISPLAYED = "displayed"
VIS_SUPPRESSED = "suppressed"

# Severity (mapped from BFE recommendation / status)
SEV_CRITICAL = "critical"
SEV_HIGH = "high"
SEV_MEDIUM = "medium"
SEV_LOW = "low"
SEV_INFO = "informational"

SOURCE_TYPE_BFE = "business_finding"
KNOWLEDGE_TYPE_BFE = "business_finding_observation"

__all__ = [
    "BFL_VERSION_V1",
    "BFL_GENERATION_VERSION_V1",
    "BFL_TABLE",
    "LS_DETECTED",
    "LS_VALIDATED",
    "LS_PERSISTED",
    "LS_KNOWLEDGE_ROUTED",
    "LS_OT_ROUTED",
    "LS_SURFACE_ELIGIBLE",
    "LS_DISPLAYED",
    "LS_RESOLVED",
    "LS_ARCHIVED",
    "LIFECYCLE_ORDER_V1",
    "VIS_HIDDEN",
    "VIS_ELIGIBLE",
    "VIS_DISPLAYED",
    "VIS_SUPPRESSED",
    "SEV_CRITICAL",
    "SEV_HIGH",
    "SEV_MEDIUM",
    "SEV_LOW",
    "SEV_INFO",
    "SOURCE_TYPE_BFE",
    "KNOWLEDGE_TYPE_BFE",
]
