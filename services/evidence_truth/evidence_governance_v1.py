# -*- coding: utf-8 -*-
"""
Evidence Truth constitutional governance vocabulary — WP-ET-05.

Truth Before Consumption lifecycle (Architecture / task governance):
  Produced → Accounted → Observable → Verified → Eligible → Consumable

WP-ET-05 may reach Eligible. Consumable remains unauthorized (no consumers).
"""
from __future__ import annotations

from services.evidence_truth.observation_types_v1 import (
    TIMESTAMP_AUTHORITY_PLATFORM_QTC,
    TIMESTAMP_AUTHORITY_WALL_CLOCK_UTC,
)

# Lifecycle states (ordered)
LIFECYCLE_PRODUCED = "produced"
LIFECYCLE_ACCOUNTED = "accounted"
LIFECYCLE_OBSERVABLE = "observable"
LIFECYCLE_VERIFIED = "verified"
LIFECYCLE_ELIGIBLE = "eligible"
LIFECYCLE_CONSUMABLE = "consumable"

EVIDENCE_LIFECYCLE_STATES_V1: frozenset[str] = frozenset(
    {
        LIFECYCLE_PRODUCED,
        LIFECYCLE_ACCOUNTED,
        LIFECYCLE_OBSERVABLE,
        LIFECYCLE_VERIFIED,
        LIFECYCLE_ELIGIBLE,
        LIFECYCLE_CONSUMABLE,
    }
)

# Accounting / observability identities (status stamps on the record)
EVIDENCE_ACCOUNTING_PENDING = "pending"
EVIDENCE_ACCOUNTING_RECORDED = "recorded"
EVIDENCE_ACCOUNTING_REJECTED = "rejected"

EVIDENCE_ACCOUNTING_STATUS_V1: frozenset[str] = frozenset(
    {
        EVIDENCE_ACCOUNTING_PENDING,
        EVIDENCE_ACCOUNTING_RECORDED,
        EVIDENCE_ACCOUNTING_REJECTED,
    }
)

EVIDENCE_OBSERVABILITY_OPS_VISIBLE = "ops_visible"
EVIDENCE_OBSERVABILITY_HIDDEN = "hidden"

EVIDENCE_OBSERVABILITY_STATUS_V1: frozenset[str] = frozenset(
    {
        EVIDENCE_OBSERVABILITY_OPS_VISIBLE,
        EVIDENCE_OBSERVABILITY_HIDDEN,
    }
)

TIMESTAMP_AUTHORITIES_V1: frozenset[str] = frozenset(
    {
        TIMESTAMP_AUTHORITY_WALL_CLOCK_UTC,
        TIMESTAMP_AUTHORITY_PLATFORM_QTC,
    }
)

EVIDENCE_GOVERNANCE_VERSION = 1

# Eligibility for consumption (WP-ET-05: never consumable by Bundle/KL/Findings)
ELIGIBILITY_NOT_CONSUMABLE = "not_consumable"
ELIGIBILITY_SHADOW_ONLY = "shadow_dual_write_only"
