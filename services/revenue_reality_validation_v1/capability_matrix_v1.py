# -*- coding: utf-8 -*-
"""Data capability matrix for Revenue Reality Validation V1."""
from __future__ import annotations

from typing import Any

from services.revenue_reality_validation_v1.contracts_v1 import (
    CAPABILITY_DATA_GAP,
    CAPABILITY_MISSING_DATA,
    CAPABILITY_MISSING_INSTRUMENTATION,
    CAPABILITY_NEEDS_EXTERNAL,
    CAPABILITY_PARTIAL,
    CAPABILITY_SUPPORTED,
    CAPABILITY_UNSAFE,
)


def build_capability_matrix_v1() -> dict[str, Any]:
    """
    Classify CartFlow capability families against production truth architecture.
    Simulation can exercise detectors; production support may still be PARTIAL/MISSING.
    """
    families = {
        "Product Intelligence": {
            "status": CAPABILITY_PARTIAL,
            "absent": [
                "unified product revenue contribution score in merchant Home",
                "governed product opportunity objects in production (sim-only here)",
            ],
            "supported_now": [
                "product signal events / metrics / trends foundations exist in codebase",
                "hesitation and recovery signals partially available",
            ],
        },
        "Acquisition Intelligence": {
            "status": CAPABILITY_MISSING_INSTRUMENTATION,
            "absent": [
                "trusted per-session acquisition channel attribution in production truth",
                "channel-level ATC/purchase/AOV governed pipeline",
            ],
            "note": "Simulation encodes channel truth for validation only.",
        },
        "Merchandising Intelligence": {
            "status": CAPABILITY_MISSING_DATA,
            "absent": [
                "homepage/category placement experiments linked to product discovery metrics",
                "merchandising change events as first-class evidence",
            ],
        },
        "Conversion Intelligence": {
            "status": CAPABILITY_PARTIAL,
            "absent": [
                "full funnel product-level conversion diagnosis wired to Revenue Missions in production UI",
            ],
            "supported_now": [
                "cart abandonment, recovery attempts, hesitation reasons (bounded)",
                "Operational Guidance Layer families for shipping/price/wait",
            ],
        },
        "Pricing Intelligence": {
            "status": CAPABILITY_PARTIAL,
            "absent": [
                "bounded price experiment measurement loop as production mission object",
                "comparative market price (external)",
            ],
            "supported_now": [
                "price hesitation signals when instrumented",
                "sale price / discount on orders when present",
            ],
        },
        "Retention Intelligence": {
            "status": CAPABILITY_MISSING_DATA,
            "absent": [
                "customer-level purchase sequences as governed production truth for missions",
                "propensity baselines for cross-sell retention",
            ],
            "note": "Simulation proves the mission shape; production needs identity+order history linkage.",
        },
        "Recovery Intelligence": {
            "status": CAPABILITY_PARTIAL,
            "absent": [
                "recovery outcomes folded into Revenue Mission measurement plans by default",
            ],
            "supported_now": [
                "recovery attempts, templates, timing, operational guidance",
            ],
        },
    }

    comparative = {
        "family": "Comparative Market Pricing",
        "status": CAPABILITY_NEEDS_EXTERNAL,
        "classification": CAPABILITY_UNSAFE,
        "required": [
            "trusted comparable-product source",
            "product matching",
            "freshness",
            "geography",
            "variant normalization",
            "shipping/tax normalization",
        ],
        "production_recommendation_allowed": False,
    }

    margin = {
        "family": "Margin Intelligence",
        "status": CAPABILITY_DATA_GAP,
        "note": (
            "Do not fake profit in production. Simulation-only unit cost may be labeled "
            "SIMULATION-ONLY for Scenario D lab validation."
        ),
        "production_recommendation_allowed": False,
    }

    return {
        "ok": True,
        "schema": "revenue_reality_capability_matrix_v1",
        "families": families,
        "comparative_market_pricing": comparative,
        "margin_intelligence": margin,
        "summary_scores": {
            "Product Intelligence": "PARTIAL",
            "Acquisition Intelligence": "DATA GAP",
            "Merchandising Intelligence": "DATA GAP",
            "Conversion Intelligence": "PARTIAL",
            "Pricing Intelligence": "PARTIAL",
            "Retention Intelligence": "DATA GAP",
            "Recovery Intelligence": "PARTIAL",
            "Comparative Market Pricing": "NEEDS_EXTERNAL_DATA / UNSAFE",
            "Margin Intelligence": "DATA GAP",
        },
    }


__all__ = ["build_capability_matrix_v1"]
