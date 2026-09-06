# -*- coding: utf-8 -*-
"""Founder Production Evaluation Tenant V1 — identity + feature vocabulary."""
from __future__ import annotations

from typing import FrozenSet

LAYER_VERSION = "founder_production_evaluation_tenant_v1"

# Production runtime evaluation merchant (smartreplyai.net) — not cf_fe_v1_* fixtures.
FOUNDER_EVAL_STORE_SLUG = "cf_founder_evaluation"
FOUNDER_EVAL_EMAIL = "founder.evaluation@cartflow.local"
FOUNDER_EVAL_DISPLAY_NAME = "CartFlow Founder Evaluation"
FOUNDER_EVAL_INTEGRATION_SOURCE = "founder_production_evaluation_v1"

# Production evaluation allowlist — exact identities only (count = 1).
PRODUCTION_EVALUATION_ALLOWLIST: FrozenSet[str] = frozenset({FOUNDER_EVAL_STORE_SLUG})

# Fixture / local logic tenants (remain test-only; NOT production evaluation).
FIXTURE_EVAL_PREFIX = "cf_fe_v1_"
FIXTURE_EVAL_INTEGRATION_SOURCE = "founder_evaluation_v1"

# Candidate features enabled only for founder production evaluation tenant.
FEATURE_MERCHANDISING_MISSION_SLICE_V1 = "merchandising_mission_slice_v1"

EVALUATION_FEATURES: FrozenSet[str] = frozenset(
    {FEATURE_MERCHANDISING_MISSION_SLICE_V1}
)

# Merchandising families withheld from normal merchants until founder review + release.
MERCHANDISING_EVAL_FAMILIES: FrozenSet[str] = frozenset(
    {"product_confidence", "product_opportunity_focus"}
)

__all__ = [
    "EVALUATION_FEATURES",
    "FEATURE_MERCHANDISING_MISSION_SLICE_V1",
    "FIXTURE_EVAL_INTEGRATION_SOURCE",
    "FIXTURE_EVAL_PREFIX",
    "FOUNDER_EVAL_DISPLAY_NAME",
    "FOUNDER_EVAL_EMAIL",
    "FOUNDER_EVAL_INTEGRATION_SOURCE",
    "FOUNDER_EVAL_STORE_SLUG",
    "LAYER_VERSION",
    "MERCHANDISING_EVAL_FAMILIES",
    "PRODUCTION_EVALUATION_ALLOWLIST",
]
