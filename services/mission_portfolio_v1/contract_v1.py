# -*- coding: utf-8 -*-
"""Mission Portfolio V1 — capacity, conflict vocabulary, reason codes."""
from __future__ import annotations

from typing import FrozenSet

LAYER_VERSION = "mission_portfolio_v1"
LAYER_SCHEMA = "mission_portfolio_package_v1"

# --- Capacity (conservative) ---
MAX_ACTIVE_MISSIONS = 1
MAX_SECONDARY_READY = 2

# Slot-owning CDC phases (READY does not own)
SLOT_PHASES: FrozenSet[str] = frozenset(
    {"ACTION_CHOSEN", "UNDER_MEASUREMENT", "RECHECK_DUE"}
)

# Portfolio conflict types (controlled vocabulary)
CONFLICT_MUTUALLY_EXCLUSIVE = "MUTUALLY_EXCLUSIVE"
CONFLICT_MEASUREMENT_CONTAMINATION = "MEASUREMENT_CONTAMINATION"
CONFLICT_DUPLICATE_INTENT = "DUPLICATE_INTENT"
CONFLICT_CAPACITY_ONLY = "CAPACITY_ONLY"
CONFLICT_SAFE_TO_COEXIST = "SAFE_TO_COEXIST"

CONFLICT_TYPES: FrozenSet[str] = frozenset(
    {
        CONFLICT_MUTUALLY_EXCLUSIVE,
        CONFLICT_MEASUREMENT_CONTAMINATION,
        CONFLICT_DUPLICATE_INTENT,
        CONFLICT_CAPACITY_ONLY,
        CONFLICT_SAFE_TO_COEXIST,
    }
)

# Machine-readable defer / suppress reasons
REASON_CAPACITY_OCCUPIED = "active_mission_occupies_capacity"
REASON_CONFLICTS_WITH_ACTIVE = "conflicts_with_active_mission"
REASON_MEASUREMENT_CONTAMINATION = "would_contaminate_measurement"
REASON_DUPLICATE_INTENT = "duplicate_intent"
REASON_LOWER_PRIORITY_RECHECK = "lower_priority_while_recheck_due"
REASON_INSUFFICIENT = "insufficient_evidence"
REASON_CATALOG_SUPPRESSED = "catalog_suppressed"
REASON_UNKNOWN_FAMILY = "unknown_family_fail_safe"
REASON_MISSING_CONFLICT_RULE = "conflict_rule_missing_fail_safe"
REASON_CLOSED_FREED = "active_closed_capacity_freed"
REASON_SAFE_SECONDARY = "safe_secondary_no_slot"

# Families known to portfolio conflict matrix
FAMILY_SHIPPING = "shipping_friction"
FAMILY_PRICE = "price_hesitation"
FAMILY_PRODUCT_CONFIDENCE = "product_confidence"
FAMILY_PRODUCT_FOCUS = "product_opportunity_focus"

# Measurement-sensitive pairs: (active_family, candidate_family)
MEASUREMENT_CONTAMINATION_PAIRS: FrozenSet[tuple[str, str]] = frozenset(
    {
        (FAMILY_SHIPPING, FAMILY_PRICE),
        (FAMILY_PRICE, FAMILY_SHIPPING),
        (FAMILY_PRICE, FAMILY_PRODUCT_FOCUS),
        (FAMILY_PRODUCT_FOCUS, FAMILY_PRICE),
        (FAMILY_PRODUCT_CONFIDENCE, FAMILY_PRODUCT_FOCUS),
        (FAMILY_PRODUCT_FOCUS, FAMILY_PRODUCT_CONFIDENCE),
    }
)

# Mutually exclusive pairs (symmetric)
MUTUALLY_EXCLUSIVE_PAIRS: FrozenSet[tuple[str, str]] = frozenset(
    {
        (FAMILY_PRICE, FAMILY_PRODUCT_CONFIDENCE),
        (FAMILY_PRODUCT_CONFIDENCE, FAMILY_PRICE),
        (FAMILY_PRODUCT_CONFIDENCE, FAMILY_PRODUCT_FOCUS),
        (FAMILY_PRODUCT_FOCUS, FAMILY_PRODUCT_CONFIDENCE),
    }
)

__all__ = [
    "CONFLICT_CAPACITY_ONLY",
    "CONFLICT_DUPLICATE_INTENT",
    "CONFLICT_MEASUREMENT_CONTAMINATION",
    "CONFLICT_MUTUALLY_EXCLUSIVE",
    "CONFLICT_SAFE_TO_COEXIST",
    "CONFLICT_TYPES",
    "FAMILY_PRICE",
    "FAMILY_PRODUCT_CONFIDENCE",
    "FAMILY_PRODUCT_FOCUS",
    "FAMILY_SHIPPING",
    "LAYER_SCHEMA",
    "LAYER_VERSION",
    "MAX_ACTIVE_MISSIONS",
    "MAX_SECONDARY_READY",
    "MEASUREMENT_CONTAMINATION_PAIRS",
    "MUTUALLY_EXCLUSIVE_PAIRS",
    "REASON_CAPACITY_OCCUPIED",
    "REASON_CATALOG_SUPPRESSED",
    "REASON_CLOSED_FREED",
    "REASON_CONFLICTS_WITH_ACTIVE",
    "REASON_DUPLICATE_INTENT",
    "REASON_INSUFFICIENT",
    "REASON_LOWER_PRIORITY_RECHECK",
    "REASON_MEASUREMENT_CONTAMINATION",
    "REASON_MISSING_CONFLICT_RULE",
    "REASON_SAFE_SECONDARY",
    "REASON_UNKNOWN_FAMILY",
    "SLOT_PHASES",
]
