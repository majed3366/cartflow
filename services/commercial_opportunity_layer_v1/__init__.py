# -*- coding: utf-8 -*-
"""Commercial Opportunity Layer V1 — production Home commercial strip (flag-gated)."""
from __future__ import annotations

from services.commercial_opportunity_layer_v1.attach_v1 import (
    attach_commercial_opportunity_layer_to_summary_v1,
)
from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    HOME_QUESTION_COMMERCIAL_AR,
    HOME_QUESTION_OPERATIONAL_AR,
    LAYER_VERSION,
    TRUTH_INSUFFICIENT,
    TRUTH_PRODUCTION_PARTIAL,
    TRUTH_PRODUCTION_READY,
    TRUTH_SIMULATION_ONLY,
)
from services.commercial_opportunity_layer_v1.flag_v1 import (
    ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1,
    commercial_opportunity_layer_v1_enabled,
)

__all__ = [
    "ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1",
    "HOME_QUESTION_COMMERCIAL_AR",
    "HOME_QUESTION_OPERATIONAL_AR",
    "LAYER_VERSION",
    "TRUTH_INSUFFICIENT",
    "TRUTH_PRODUCTION_PARTIAL",
    "TRUTH_PRODUCTION_READY",
    "TRUTH_SIMULATION_ONLY",
    "attach_commercial_opportunity_layer_to_summary_v1",
    "commercial_opportunity_layer_v1_enabled",
    "compose_commercial_opportunity_layer_v1",
]
