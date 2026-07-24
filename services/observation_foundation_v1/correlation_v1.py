# -*- coding: utf-8 -*-
"""
Observation Foundation V1 — Correlation Model.

Canonical chain:
  Product → Customer behavior → Reason → Return → Purchase

No UI. No recommendations. Correlations only — with statement capability markers.
"""
from __future__ import annotations

from typing import Any

from services.observation_foundation_v1.catalog_v1 import (
    FOUNDATION_VERSION,
    OBS_CART_ADD,
    OBS_CHECKOUT_START,
    OBS_HESITATION_REASON,
    OBS_PURCHASE,
    OBS_REPEAT_VISIT,
    OBS_RETURN_TO_STORE,
)

# Correlation kinds (structural links — not findings)
CORR_PRODUCT_CUSTOMER_BEHAVIOR = "product_customer_behavior_v1"
CORR_BEHAVIOR_REASON = "behavior_reason_v1"
CORR_REASON_RETURN = "reason_return_v1"
CORR_RETURN_PURCHASE = "return_purchase_v1"
CORR_PRODUCT_INTEREST_CONVERSION = "product_interest_conversion_v1"
CORR_REASON_STRENGTH = "reason_strength_compare_v1"
CORR_REPEAT_RETURN_NO_PURCHASE = "repeat_return_without_purchase_v1"
CORR_ABSENT_REASON = "absent_reason_evidence_v1"

CORRELATION_KINDS_V1: tuple[str, ...] = (
    CORR_PRODUCT_CUSTOMER_BEHAVIOR,
    CORR_BEHAVIOR_REASON,
    CORR_REASON_RETURN,
    CORR_RETURN_PURCHASE,
    CORR_PRODUCT_INTEREST_CONVERSION,
    CORR_REASON_STRENGTH,
    CORR_REPEAT_RETURN_NO_PURCHASE,
    CORR_ABSENT_REASON,
)

# Chain stages (ordered)
CHAIN_STAGES_V1: tuple[str, ...] = (
    "product",
    "customer_behavior",
    "reason",
    "return",
    "purchase",
)

# Stage → observation types that feed it
STAGE_OBSERVATIONS_V1: dict[str, tuple[str, ...]] = {
    "product": (OBS_CART_ADD, OBS_CHECKOUT_START, OBS_PURCHASE),
    "customer_behavior": (OBS_CART_ADD, OBS_CHECKOUT_START, OBS_RETURN_TO_STORE),
    "reason": (OBS_HESITATION_REASON,),
    "return": (OBS_RETURN_TO_STORE, OBS_REPEAT_VISIT),
    "purchase": (OBS_PURCHASE,),
}

# Statement capabilities (what Product Intelligence may later say — not emitted as UI)
STATEMENT_CAPABILITIES_V1: tuple[dict[str, Any], ...] = (
    {
        "capability_id": "high_interest_low_conversion",
        "example_statement": "The product has high interest but low conversion.",
        "required_correlation": CORR_PRODUCT_INTEREST_CONVERSION,
        "required_observations": [OBS_CART_ADD, OBS_PURCHASE],
        "requires_absent": False,
    },
    {
        "capability_id": "shipping_stronger_than_price",
        "example_statement": "Shipping evidence is stronger than price evidence.",
        "required_correlation": CORR_REASON_STRENGTH,
        "required_observations": [OBS_HESITATION_REASON],
        "requires_absent": False,
    },
    {
        "capability_id": "repeated_return_without_purchase",
        "example_statement": "Customers repeatedly return without purchasing.",
        "required_correlation": CORR_REPEAT_RETURN_NO_PURCHASE,
        "required_observations": [OBS_RETURN_TO_STORE, OBS_PURCHASE],
        "requires_absent": False,
    },
    {
        "capability_id": "no_quality_issue_evidence",
        "example_statement": "No evidence currently supports a quality issue.",
        "required_correlation": CORR_ABSENT_REASON,
        "required_observations": [OBS_HESITATION_REASON],
        "requires_absent": True,
        "absent_reason_tokens": ("quality", "جودة", "defect", "broken"),
    },
)

CORRELATION_MODEL_V1: dict[str, Any] = {
    "schema": FOUNDATION_VERSION,
    "layer": "correlation_model",
    "chain": list(CHAIN_STAGES_V1),
    "chain_diagram": "Product → Customer behavior → Reason → Return → Purchase",
    "kinds": list(CORRELATION_KINDS_V1),
    "stage_observations": {k: list(v) for k, v in STAGE_OBSERVATIONS_V1.items()},
    "statement_capabilities": list(STATEMENT_CAPABILITIES_V1),
    "ui": False,
    "intelligence": False,
    "rules": [
        "A correlation exists only when linked observations share product_key and/or session/customer key.",
        "Absence correlations require observation coverage for the reason family — silence is not proof without a reason-capture base.",
        "Correlations never invent recommendations or UI copy.",
    ],
}


def correlation_model_dict_v1() -> dict[str, Any]:
    return dict(CORRELATION_MODEL_V1)


__all__ = [
    "CHAIN_STAGES_V1",
    "CORR_ABSENT_REASON",
    "CORR_BEHAVIOR_REASON",
    "CORR_PRODUCT_CUSTOMER_BEHAVIOR",
    "CORR_PRODUCT_INTEREST_CONVERSION",
    "CORR_REASON_RETURN",
    "CORR_REASON_STRENGTH",
    "CORR_REPEAT_RETURN_NO_PURCHASE",
    "CORR_RETURN_PURCHASE",
    "CORRELATION_KINDS_V1",
    "CORRELATION_MODEL_V1",
    "STAGE_OBSERVATIONS_V1",
    "STATEMENT_CAPABILITIES_V1",
    "correlation_model_dict_v1",
]
