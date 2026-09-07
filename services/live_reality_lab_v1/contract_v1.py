# -*- coding: utf-8 -*-
"""
Live Reality Laboratory V1 — identity + dataset vocabulary.

Canonical production validation tenant (not demo, not cf_fe_v1_*, not founder eval).
Dataset V2 extends the same tenant; it does not create a second ranker or CDC.
"""
from __future__ import annotations

from typing import FrozenSet

LAYER_VERSION = "live_reality_lab_v1"
DATASET_VERSION = "live_reality_dataset_v1"
DATASET_VERSION_V2 = "live_reality_dataset_v2"

LAB_STORE_SLUG = "cf_live_reality_lab"
LAB_EMAIL = "reality.lab@cartflow.local"
LAB_DISPLAY_NAME = "CartFlow Live Reality Lab"
LAB_STORE_DISPLAY_NAME_V2 = "نور العناية"
LAB_INTEGRATION_SOURCE = "live_reality_lab_v1"
LAB_REASON_SOURCE = "live_reality_lab_v1"
LAB_CART_ID_PREFIX = "lrl_v1_"
LAB_CART_ID_PREFIX_V2 = "lrl_v2_"
LAB_CART_ID_PREFIX_ANY = "lrl_"

# Lab-owned production-shaped visit rows. Not a storefront/pixel writer.
LAB_SYNTHETIC_VISIT_SOURCE = "live_reality_lab_v2_synthetic_visit"
LAB_VISIT_TRUTH_CLASS = "LAB-SYNTHETIC PRODUCTION-SHAPED VISIT TRUTH"
MISSING_NAME_PRODUCT_ID = "nf-missing-name"

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

SCENARIO_R13 = "R13_sent_recovery_no_completion"
SCENARIO_R14 = "R14_sent_recovery_later_purchased"
SCENARIO_R15 = "R15_zero_visits"
SCENARIO_R16 = "R16_visits_no_carts"
SCENARIO_R17 = "R17_shipping_hesitation"
SCENARIO_R18 = "R18_delivery_duration_hesitation"
SCENARIO_R19 = "R19_cart_interest_weak_purchase"
SCENARIO_R20 = "R20_product_confidence"
SCENARIO_R21 = "R21_price_hesitation"
SCENARIO_R22 = "R22_healthy_product"
SCENARIO_R23 = "R23_unresolved_recovery"
SCENARIO_R24 = "R24_resolved_recovery"

SCENARIO_ALLOWLIST_V1: FrozenSet[str] = frozenset(
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

SCENARIO_ALLOWLIST_V2: FrozenSet[str] = frozenset(
    {
        SCENARIO_R13,
        SCENARIO_R14,
        SCENARIO_R15,
        SCENARIO_R16,
        SCENARIO_R17,
        SCENARIO_R18,
        SCENARIO_R19,
        SCENARIO_R20,
        SCENARIO_R21,
        SCENARIO_R22,
        SCENARIO_R23,
        SCENARIO_R24,
    }
)

SCENARIO_ALLOWLIST: FrozenSet[str] = frozenset(SCENARIO_ALLOWLIST_V1 | SCENARIO_ALLOWLIST_V2)

# Bootstrap password — rotate in ops before production lab use.
LAB_BOOTSTRAP_PASSWORD = "LiveRealityLab-Prod-Tenant-V1!"

__all__ = [
    "DATASET_VERSION",
    "DATASET_VERSION_V2",
    "LAB_BOOTSTRAP_PASSWORD",
    "LAB_CART_ID_PREFIX",
    "LAB_CART_ID_PREFIX_ANY",
    "LAB_CART_ID_PREFIX_V2",
    "LAB_DISPLAY_NAME",
    "LAB_EMAIL",
    "LAB_INTEGRATION_SOURCE",
    "LAB_PRODUCTION_ALLOWLIST",
    "LAB_REASON_SOURCE",
    "LAB_STORE_DISPLAY_NAME_V2",
    "LAB_STORE_SLUG",
    "LAB_SYNTHETIC_VISIT_SOURCE",
    "LAB_VISIT_TRUTH_CLASS",
    "LAYER_VERSION",
    "MISSING_NAME_PRODUCT_ID",
    "SCENARIO_ALLOWLIST",
    "SCENARIO_ALLOWLIST_V1",
    "SCENARIO_ALLOWLIST_V2",
    "SCENARIO_R1",
    "SCENARIO_R10",
    "SCENARIO_R11",
    "SCENARIO_R12",
    "SCENARIO_R13",
    "SCENARIO_R14",
    "SCENARIO_R15",
    "SCENARIO_R16",
    "SCENARIO_R17",
    "SCENARIO_R18",
    "SCENARIO_R19",
    "SCENARIO_R2",
    "SCENARIO_R20",
    "SCENARIO_R21",
    "SCENARIO_R22",
    "SCENARIO_R23",
    "SCENARIO_R24",
    "SCENARIO_R3",
    "SCENARIO_R4",
    "SCENARIO_R5",
    "SCENARIO_R6",
    "SCENARIO_R7",
    "SCENARIO_R8",
    "SCENARIO_R9",
]
