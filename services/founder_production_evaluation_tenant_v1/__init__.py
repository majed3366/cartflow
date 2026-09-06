# -*- coding: utf-8 -*-
"""Founder Production Evaluation Tenant V1 — production review isolation gate."""
from __future__ import annotations

from services.founder_production_evaluation_tenant_v1.contract_v1 import (
    FEATURE_MERCHANDISING_MISSION_SLICE_V1,
    FOUNDER_EVAL_EMAIL,
    FOUNDER_EVAL_INTEGRATION_SOURCE,
    FOUNDER_EVAL_STORE_SLUG,
    LAYER_VERSION,
    MERCHANDISING_EVAL_FAMILIES,
    PRODUCTION_EVALUATION_ALLOWLIST,
)
from services.founder_production_evaluation_tenant_v1.ensure_v1 import (
    ensure_founder_production_evaluation_tenant_v1,
)
from services.founder_production_evaluation_tenant_v1.gate_v1 import (
    ENV_TEST_ALLOW_MERCHANDISING_SLICE,
    filter_merchandising_opportunities,
    founder_evaluation_feature_enabled,
    is_fixture_evaluation_slug,
    is_founder_evaluation_tenant,
    is_founder_production_evaluation_tenant,
    merchandising_families_allowed_for_store,
    test_merchandising_slice_infrastructure_enabled,
)
from services.founder_production_evaluation_tenant_v1.side_effects_v1 import (
    evaluation_side_effect_block_reason,
    evaluation_tenant_blocks_external_side_effects,
)

__all__ = [
    "ENV_TEST_ALLOW_MERCHANDISING_SLICE",
    "FEATURE_MERCHANDISING_MISSION_SLICE_V1",
    "FOUNDER_EVAL_EMAIL",
    "FOUNDER_EVAL_INTEGRATION_SOURCE",
    "FOUNDER_EVAL_STORE_SLUG",
    "LAYER_VERSION",
    "MERCHANDISING_EVAL_FAMILIES",
    "PRODUCTION_EVALUATION_ALLOWLIST",
    "ensure_founder_production_evaluation_tenant_v1",
    "evaluation_side_effect_block_reason",
    "evaluation_tenant_blocks_external_side_effects",
    "filter_merchandising_opportunities",
    "founder_evaluation_feature_enabled",
    "is_fixture_evaluation_slug",
    "is_founder_evaluation_tenant",
    "is_founder_production_evaluation_tenant",
    "merchandising_families_allowed_for_store",
    "test_merchandising_slice_infrastructure_enabled",
]
