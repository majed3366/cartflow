# -*- coding: utf-8 -*-
"""
Observation Foundation V1 — Observation Model (catalog).

Canonical continuous observation types for Product / Customer / Hesitation.
No UI. No intelligence. No decisions.
"""
from __future__ import annotations

from typing import Any, Literal

FOUNDATION_VERSION = "observation_foundation_v1"

# Evidence readiness for each observation type
EvidenceStatus = Literal["wired", "partial", "derived", "unavailable"]

# ---- Observation types (canonical) ----
OBS_PRODUCT_VIEW = "product_view_observed_v1"
OBS_PRODUCT_OPEN = "product_open_observed_v1"
OBS_CART_ADD = "cart_add_observed_v1"
OBS_CART_REMOVE = "cart_remove_observed_v1"
OBS_CHECKOUT_START = "checkout_start_observed_v1"
OBS_PURCHASE = "purchase_observed_v1"
OBS_RETURN_TO_PRODUCT = "return_to_product_observed_v1"
OBS_RETURN_TO_STORE = "return_to_store_observed_v1"
OBS_TIME_SPENT = "time_spent_observed_v1"
OBS_HESITATION_REASON = "hesitation_reason_observed_v1"
OBS_WHATSAPP_INTERACTION = "whatsapp_interaction_observed_v1"
OBS_REPEAT_VISIT = "repeat_visit_observed_v1"
OBS_REPEAT_PURCHASE = "repeat_purchase_observed_v1"

OBSERVATION_TYPES_V1: tuple[str, ...] = (
    OBS_PRODUCT_VIEW,
    OBS_PRODUCT_OPEN,
    OBS_CART_ADD,
    OBS_CART_REMOVE,
    OBS_CHECKOUT_START,
    OBS_PURCHASE,
    OBS_RETURN_TO_PRODUCT,
    OBS_RETURN_TO_STORE,
    OBS_TIME_SPENT,
    OBS_HESITATION_REASON,
    OBS_WHATSAPP_INTERACTION,
    OBS_REPEAT_VISIT,
    OBS_REPEAT_PURCHASE,
)

# Product Signal Collection → Observation Foundation (consumer mapping)
from services.product_data.product_signal_types_v1 import (  # noqa: E402
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CART_REMOVED,
    SIGNAL_PRODUCT_CHECKOUT_TOUCHED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
    SIGNAL_PRODUCT_PURCHASED,
    SIGNAL_PRODUCT_RECOVERY_PROGRESSED,
    SIGNAL_PRODUCT_RECOVERY_STARTED,
    SIGNAL_PRODUCT_VIEWED,
)

SIGNAL_TO_OBSERVATION_V1: dict[str, str] = {
    SIGNAL_PRODUCT_VIEWED: OBS_PRODUCT_VIEW,
    SIGNAL_PRODUCT_CART_ADDED: OBS_CART_ADD,
    SIGNAL_PRODUCT_CART_REMOVED: OBS_CART_REMOVE,
    SIGNAL_PRODUCT_CHECKOUT_TOUCHED: OBS_CHECKOUT_START,
    SIGNAL_PRODUCT_PURCHASED: OBS_PURCHASE,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED: OBS_RETURN_TO_STORE,
    SIGNAL_PRODUCT_INTEREST_HESITATION: OBS_HESITATION_REASON,
    SIGNAL_PRODUCT_RECOVERY_STARTED: OBS_WHATSAPP_INTERACTION,
    SIGNAL_PRODUCT_RECOVERY_PROGRESSED: OBS_WHATSAPP_INTERACTION,
}

# Observation Model — one row per observation type
OBSERVATION_MODEL_V1: tuple[dict[str, Any], ...] = (
    {
        "observation_type": OBS_PRODUCT_VIEW,
        "subject": "product",
        "meaning": "Customer viewed the product (PDP / product detail).",
        "evidence_status": "unavailable",
        "source_layer": "product_signal_collection_v1",
        "source_signal_types": [SIGNAL_PRODUCT_VIEWED],
        "gap": "product_viewed signal deferred — no durable PDP view persist.",
    },
    {
        "observation_type": OBS_PRODUCT_OPEN,
        "subject": "product",
        "meaning": "Customer opened the product surface (distinct open event).",
        "evidence_status": "unavailable",
        "source_layer": "none",
        "source_signal_types": [],
        "gap": "No durable product_open event; not distinct from view today.",
    },
    {
        "observation_type": OBS_CART_ADD,
        "subject": "product",
        "meaning": "Product added to cart.",
        "evidence_status": "wired",
        "source_layer": "product_signal_collection_v1",
        "source_signal_types": [SIGNAL_PRODUCT_CART_ADDED],
        "gap": "",
    },
    {
        "observation_type": OBS_CART_REMOVE,
        "subject": "product",
        "meaning": "Product removed from cart.",
        "evidence_status": "wired",
        "source_layer": "product_signal_collection_v1",
        "source_signal_types": [SIGNAL_PRODUCT_CART_REMOVED],
        "gap": "",
    },
    {
        "observation_type": OBS_CHECKOUT_START,
        "subject": "product",
        "meaning": "Checkout started while product present.",
        "evidence_status": "partial",
        "source_layer": "product_signal_collection_v1",
        "source_signal_types": [SIGNAL_PRODUCT_CHECKOUT_TOUCHED],
        "gap": "Checkout touch proxy — not a dedicated checkout_started observation.",
    },
    {
        "observation_type": OBS_PURCHASE,
        "subject": "product",
        "meaning": "Purchase confirmed for product.",
        "evidence_status": "wired",
        "source_layer": "product_signal_collection_v1 + purchase_truth",
        "source_signal_types": [SIGNAL_PRODUCT_PURCHASED],
        "gap": "",
    },
    {
        "observation_type": OBS_RETURN_TO_PRODUCT,
        "subject": "product",
        "meaning": "Customer returned specifically to this product.",
        "evidence_status": "unavailable",
        "source_layer": "none",
        "source_signal_types": [],
        "gap": "Return signals are store/session scoped, not product-page scoped.",
    },
    {
        "observation_type": OBS_RETURN_TO_STORE,
        "subject": "customer",
        "meaning": "Customer returned to the store (commercial return).",
        "evidence_status": "wired",
        "source_layer": "product_signal_collection_v1 + behavioral_return",
        "source_signal_types": [SIGNAL_PRODUCT_CUSTOMER_RETURNED],
        "gap": "",
    },
    {
        "observation_type": OBS_TIME_SPENT,
        "subject": "product",
        "meaning": "Time spent on product / session dwell.",
        "evidence_status": "unavailable",
        "source_layer": "none",
        "source_signal_types": [],
        "gap": "No durable dwell / time-spent persist path.",
    },
    {
        "observation_type": OBS_HESITATION_REASON,
        "subject": "reason",
        "meaning": "Hesitation reason captured with product context.",
        "evidence_status": "wired",
        "source_layer": "product_signal_collection_v1 + hesitation_mapping",
        "source_signal_types": [SIGNAL_PRODUCT_INTEREST_HESITATION],
        "gap": "",
    },
    {
        "observation_type": OBS_WHATSAPP_INTERACTION,
        "subject": "customer",
        "meaning": "WhatsApp / recovery interaction involving the customer and product context.",
        "evidence_status": "partial",
        "source_layer": "recovery_timeline + product_recovery_interaction signals",
        "source_signal_types": [
            SIGNAL_PRODUCT_RECOVERY_STARTED,
            SIGNAL_PRODUCT_RECOVERY_PROGRESSED,
        ],
        "gap": "Recovery timeline proxy — not full inbound WA product-scoped observation.",
    },
    {
        "observation_type": OBS_REPEAT_VISIT,
        "subject": "customer",
        "meaning": "Same customer visited / returned more than once.",
        "evidence_status": "derived",
        "source_layer": "observation_foundation_v1 (from return observations)",
        "source_signal_types": [SIGNAL_PRODUCT_CUSTOMER_RETURNED],
        "gap": "Derived when ≥2 return observations share a customer/session key.",
    },
    {
        "observation_type": OBS_REPEAT_PURCHASE,
        "subject": "customer",
        "meaning": "Same customer purchased more than once.",
        "evidence_status": "derived",
        "source_layer": "observation_foundation_v1 (from purchase observations)",
        "source_signal_types": [SIGNAL_PRODUCT_PURCHASED],
        "gap": "Derived when ≥2 purchase observations share a customer key.",
    },
)


def observation_catalog_dict_v1() -> dict[str, Any]:
    wired = [r for r in OBSERVATION_MODEL_V1 if r["evidence_status"] == "wired"]
    partial = [r for r in OBSERVATION_MODEL_V1 if r["evidence_status"] == "partial"]
    derived = [r for r in OBSERVATION_MODEL_V1 if r["evidence_status"] == "derived"]
    unavailable = [
        r for r in OBSERVATION_MODEL_V1 if r["evidence_status"] == "unavailable"
    ]
    return {
        "schema": FOUNDATION_VERSION,
        "layer": "observation_model",
        "observation_types": list(OBSERVATION_TYPES_V1),
        "entries": list(OBSERVATION_MODEL_V1),
        "counts": {
            "total": len(OBSERVATION_MODEL_V1),
            "wired": len(wired),
            "partial": len(partial),
            "derived": len(derived),
            "unavailable": len(unavailable),
        },
        "ui": False,
        "intelligence": False,
    }


__all__ = [
    "FOUNDATION_VERSION",
    "OBSERVATION_MODEL_V1",
    "OBSERVATION_TYPES_V1",
    "OBS_CART_ADD",
    "OBS_CART_REMOVE",
    "OBS_CHECKOUT_START",
    "OBS_HESITATION_REASON",
    "OBS_PRODUCT_OPEN",
    "OBS_PRODUCT_VIEW",
    "OBS_PURCHASE",
    "OBS_REPEAT_PURCHASE",
    "OBS_REPEAT_VISIT",
    "OBS_RETURN_TO_PRODUCT",
    "OBS_RETURN_TO_STORE",
    "OBS_TIME_SPENT",
    "OBS_WHATSAPP_INTERACTION",
    "SIGNAL_TO_OBSERVATION_V1",
    "observation_catalog_dict_v1",
]
