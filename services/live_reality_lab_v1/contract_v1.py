# -*- coding: utf-8 -*-
"""
Live Reality Laboratory V1 — identity + dataset vocabulary.

Canonical production validation tenant (not demo, not cf_fe_v1_*, not founder eval).
"""
from __future__ import annotations

from typing import FrozenSet

LAYER_VERSION = "live_reality_lab_v1"
DATASET_VERSION = "live_reality_dataset_v1"

LAB_STORE_SLUG = "cf_live_reality_lab"
LAB_EMAIL = "reality.lab@cartflow.local"
LAB_DISPLAY_NAME = "CartFlow Live Reality Lab"
LAB_INTEGRATION_SOURCE = "live_reality_lab_v1"
LAB_REASON_SOURCE = "live_reality_lab_v1"
LAB_CART_ID_PREFIX = "lrl_v1_"

# Exact allowlist — no wildcards.
LAB_PRODUCTION_ALLOWLIST: FrozenSet[str] = frozenset({LAB_STORE_SLUG})

SCENARIO_R1 = "R1_communication_obligation"
SCENARIO_R2 = "R2_shipping_hesitation"
SCENARIO_R3 = "R3_price_hesitation"
SCENARIO_R4 = "R4_product_confidence"
SCENARIO_R5 = "R5_product_opportunity_focus"
SCENARIO_R6 = "R6_insufficient_evidence"
SCENARIO_R7 = "R7_commercial_operational_coexistence"
SCENARIO_R8 = "R8_action_chosen"
SCENARIO_R9 = "R9_under_measurement"
SCENARIO_R10 = "R10_recheck_due"
SCENARIO_R11 = "R11_portfolio_conflict"
SCENARIO_R12 = "R12_capacity_released"

SCENARIO_ALLOWLIST: FrozenSet[str] = frozenset(
    {
        SCENARIO_R1,
        SCENARIO_R2,
        SCENARIO_R3,
        SCENARIO_R4,
        SCENARIO_R5,
        SCENARIO_R6,
        SCENARIO_R7,
        SCENARIO_R8,
        SCENARIO_R9,
        SCENARIO_R10,
        SCENARIO_R11,
        SCENARIO_R12,
    }
)

# Bootstrap password — rotate in ops before production lab use.
LAB_BOOTSTRAP_PASSWORD = "LiveRealityLab-Prod-Tenant-V1!"

__all__ = [
    "DATASET_VERSION",
    "LAB_BOOTSTRAP_PASSWORD",
    "LAB_CART_ID_PREFIX",
    "LAB_DISPLAY_NAME",
    "LAB_EMAIL",
    "LAB_INTEGRATION_SOURCE",
    "LAB_PRODUCTION_ALLOWLIST",
    "LAB_REASON_SOURCE",
    "LAB_STORE_SLUG",
    "LAYER_VERSION",
    "SCENARIO_ALLOWLIST",
    "SCENARIO_R1",
    "SCENARIO_R10",
    "SCENARIO_R11",
    "SCENARIO_R12",
    "SCENARIO_R2",
    "SCENARIO_R3",
    "SCENARIO_R4",
    "SCENARIO_R5",
    "SCENARIO_R6",
    "SCENARIO_R7",
    "SCENARIO_R8",
    "SCENARIO_R9",
]
