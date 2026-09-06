# -*- coding: utf-8 -*-
"""Mission Catalog + Prioritization V1 — contracts."""
from __future__ import annotations

from typing import FrozenSet

LAYER_VERSION = "mission_catalog_v1"
LAYER_SCHEMA = "mission_catalog_package_v1"

MAX_SECONDARIES = 2

# Catalog roles
ROLE_PRIMARY = "primary"
ROLE_SECONDARY = "secondary"
ROLE_SUPPRESSED = "suppressed"

# Lifecycle support levels for inventory
LIFECYCLE_MISSION_READY = "mission_ready"  # full Commercial Mission accept/measure/recheck
LIFECYCLE_COL_ONLY = "col_only"  # COL opportunity exists; mission profile not registered
LIFECYCLE_UNSUPPORTED = "unsupported"

# Suppression reason codes (machine-readable)
SUPPRESS_DUPLICATE_FAMILY = "duplicate_family"
SUPPRESS_CONFLICT_GROUP = "conflict_group"
SUPPRESS_ACTIVE_COMMITMENT_REISSUE = "active_commitment_reissue"
SUPPRESS_WEAKER_THAN_PRIMARY = "weaker_than_primary"
SUPPRESS_INSUFFICIENT = "insufficient_evidence"
SUPPRESS_NOT_MISSION_READY_FOR_PRIMARY = "not_mission_ready_for_primary"
SUPPRESS_STALE_OR_MISSING = "stale_or_missing_opportunity"
SUPPRESS_FAMILY_CONFIG_MISSING = "family_config_missing"
SUPPRESS_OVERFLOW_SECONDARY = "overflow_secondary_cap"

# Continuity boosts (explainable integers — not opaque AI)
BOOST_RECHECK_DUE = 400
BOOST_UNDER_MEASUREMENT = 350
BOOST_ACTION_CHOSEN = 300
BOOST_OPEN_COMMITMENT = 250

# Conflict groups: at most one family from a group in primary+secondary surface
CONFLICT_GROUPS: dict[str, FrozenSet[str]] = {
    # Value/price intervention themes — do not stack competing "don't discount / fix confidence" as both visible
    "pricing_value_theme": frozenset({"price_hesitation", "product_confidence"}),
    # Merchandising trust — confidence vs focus concentration (same commercial intent class)
    "merchandising_trust_theme": frozenset(
        {"product_confidence", "product_opportunity_focus"}
    ),
}

__all__ = [
    "BOOST_ACTION_CHOSEN",
    "BOOST_OPEN_COMMITMENT",
    "BOOST_RECHECK_DUE",
    "BOOST_UNDER_MEASUREMENT",
    "CONFLICT_GROUPS",
    "LAYER_SCHEMA",
    "LAYER_VERSION",
    "LIFECYCLE_COL_ONLY",
    "LIFECYCLE_MISSION_READY",
    "LIFECYCLE_UNSUPPORTED",
    "MAX_SECONDARIES",
    "ROLE_PRIMARY",
    "ROLE_SECONDARY",
    "ROLE_SUPPRESSED",
    "SUPPRESS_ACTIVE_COMMITMENT_REISSUE",
    "SUPPRESS_CONFLICT_GROUP",
    "SUPPRESS_DUPLICATE_FAMILY",
    "SUPPRESS_FAMILY_CONFIG_MISSING",
    "SUPPRESS_INSUFFICIENT",
    "SUPPRESS_NOT_MISSION_READY_FOR_PRIMARY",
    "SUPPRESS_OVERFLOW_SECONDARY",
    "SUPPRESS_STALE_OR_MISSING",
    "SUPPRESS_WEAKER_THAN_PRIMARY",
]
