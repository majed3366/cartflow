# -*- coding: utf-8 -*-
"""
Product Metrics Foundation V1 — canonical metric catalog (definitions only).

Metrics answer "how much happened" from Product Signals. No trends, scores, or decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.product_data.product_signal_types_v1 import (
    SIGNAL_PRODUCT_CART_ABANDONED,
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CART_REMOVED,
    SIGNAL_PRODUCT_CART_SYNCED,
    SIGNAL_PRODUCT_CHECKOUT_TOUCHED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_EVIDENCE_LINKED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
    SIGNAL_PRODUCT_PURCHASED,
    SIGNAL_PRODUCT_RECOVERY_PROGRESSED,
    SIGNAL_PRODUCT_RECOVERY_STARTED,
)

COMPUTATION_VERSION_V1 = "pmf_v1_count"

FAMILY_INTEREST_METRICS = "interest_metrics"
FAMILY_CART_METRICS = "cart_metrics"
FAMILY_CHECKOUT_METRICS = "checkout_metrics"
FAMILY_PURCHASE_METRICS = "purchase_metrics"
FAMILY_RECOVERY_METRICS = "recovery_metrics"
FAMILY_RETURN_METRICS = "return_metrics"
FAMILY_EVIDENCE_METRICS = "evidence_metrics"

METRIC_FAMILIES = frozenset(
    {
        FAMILY_INTEREST_METRICS,
        FAMILY_CART_METRICS,
        FAMILY_CHECKOUT_METRICS,
        FAMILY_PURCHASE_METRICS,
        FAMILY_RECOVERY_METRICS,
        FAMILY_RETURN_METRICS,
        FAMILY_EVIDENCE_METRICS,
    }
)

METRIC_INTEREST_HESITATION_COUNT = "interest_hesitation_count"
METRIC_CART_ADDED_COUNT = "cart_added_count"
METRIC_CART_REMOVED_COUNT = "cart_removed_count"
METRIC_CART_SYNCED_COUNT = "cart_synced_count"
METRIC_CART_ABANDONED_COUNT = "cart_abandoned_count"
METRIC_CHECKOUT_TOUCHED_COUNT = "checkout_touched_count"
METRIC_PURCHASE_COUNT = "purchase_count"
METRIC_RECOVERY_STARTED_COUNT = "recovery_started_count"
METRIC_RECOVERY_PROGRESSED_COUNT = "recovery_progressed_count"
METRIC_CUSTOMER_RETURN_COUNT = "customer_return_count"
METRIC_EVIDENCE_LINKED_COUNT = "evidence_linked_count"

WINDOW_ALL = "all"
WINDOW_DAY = "day"
WINDOW_WEEK = "week"
WINDOW_MONTH = "month"

SUPPORTED_WINDOWS = frozenset({WINDOW_ALL, WINDOW_DAY, WINDOW_WEEK, WINDOW_MONTH})

STORE_GRAIN_IDENTITY = ""


@dataclass(frozen=True, slots=True)
class ProductMetricDefinition:
    metric_key: str
    metric_family: str
    source_signal_type: str
    definition: str


METRIC_DEFINITIONS: tuple[ProductMetricDefinition, ...] = (
    ProductMetricDefinition(
        METRIC_INTEREST_HESITATION_COUNT,
        FAMILY_INTEREST_METRICS,
        SIGNAL_PRODUCT_INTEREST_HESITATION,
        "Count of product_interest_hesitation signals",
    ),
    ProductMetricDefinition(
        METRIC_CART_ADDED_COUNT,
        FAMILY_CART_METRICS,
        SIGNAL_PRODUCT_CART_ADDED,
        "Count of product_cart_added signals",
    ),
    ProductMetricDefinition(
        METRIC_CART_REMOVED_COUNT,
        FAMILY_CART_METRICS,
        SIGNAL_PRODUCT_CART_REMOVED,
        "Count of product_cart_removed signals",
    ),
    ProductMetricDefinition(
        METRIC_CART_SYNCED_COUNT,
        FAMILY_CART_METRICS,
        SIGNAL_PRODUCT_CART_SYNCED,
        "Count of product_cart_synced signals",
    ),
    ProductMetricDefinition(
        METRIC_CART_ABANDONED_COUNT,
        FAMILY_CART_METRICS,
        SIGNAL_PRODUCT_CART_ABANDONED,
        "Count of product_cart_abandoned signals",
    ),
    ProductMetricDefinition(
        METRIC_CHECKOUT_TOUCHED_COUNT,
        FAMILY_CHECKOUT_METRICS,
        SIGNAL_PRODUCT_CHECKOUT_TOUCHED,
        "Count of product_checkout_touched signals",
    ),
    ProductMetricDefinition(
        METRIC_PURCHASE_COUNT,
        FAMILY_PURCHASE_METRICS,
        SIGNAL_PRODUCT_PURCHASED,
        "Count of product_purchased signals",
    ),
    ProductMetricDefinition(
        METRIC_RECOVERY_STARTED_COUNT,
        FAMILY_RECOVERY_METRICS,
        SIGNAL_PRODUCT_RECOVERY_STARTED,
        "Count of product_recovery_started signals",
    ),
    ProductMetricDefinition(
        METRIC_RECOVERY_PROGRESSED_COUNT,
        FAMILY_RECOVERY_METRICS,
        SIGNAL_PRODUCT_RECOVERY_PROGRESSED,
        "Count of product_recovery_progressed signals",
    ),
    ProductMetricDefinition(
        METRIC_CUSTOMER_RETURN_COUNT,
        FAMILY_RETURN_METRICS,
        SIGNAL_PRODUCT_CUSTOMER_RETURNED,
        "Count of product_customer_returned signals",
    ),
    ProductMetricDefinition(
        METRIC_EVIDENCE_LINKED_COUNT,
        FAMILY_EVIDENCE_METRICS,
        SIGNAL_PRODUCT_EVIDENCE_LINKED,
        "Count of product_evidence_linked signals",
    ),
)

METRIC_KEY_TO_DEFINITION: dict[str, ProductMetricDefinition] = {
    d.metric_key: d for d in METRIC_DEFINITIONS
}

SIGNAL_TYPE_TO_METRIC_KEY: dict[str, str] = {
    d.source_signal_type: d.metric_key for d in METRIC_DEFINITIONS
}

METRIC_KEYS = frozenset(METRIC_KEY_TO_DEFINITION.keys())


def metric_family_for_key(metric_key: str) -> Optional[str]:
    d = METRIC_KEY_TO_DEFINITION.get(str(metric_key or "").strip())
    return d.metric_family if d else None


def metric_key_for_signal_type(signal_type: str) -> Optional[str]:
    return SIGNAL_TYPE_TO_METRIC_KEY.get(str(signal_type or "").strip())


__all__ = [
    "COMPUTATION_VERSION_V1",
    "FAMILY_INTEREST_METRICS",
    "FAMILY_CART_METRICS",
    "FAMILY_CHECKOUT_METRICS",
    "FAMILY_PURCHASE_METRICS",
    "FAMILY_RECOVERY_METRICS",
    "FAMILY_RETURN_METRICS",
    "FAMILY_EVIDENCE_METRICS",
    "METRIC_FAMILIES",
    "METRIC_INTEREST_HESITATION_COUNT",
    "METRIC_CART_ADDED_COUNT",
    "METRIC_CART_REMOVED_COUNT",
    "METRIC_CART_SYNCED_COUNT",
    "METRIC_CART_ABANDONED_COUNT",
    "METRIC_CHECKOUT_TOUCHED_COUNT",
    "METRIC_PURCHASE_COUNT",
    "METRIC_RECOVERY_STARTED_COUNT",
    "METRIC_RECOVERY_PROGRESSED_COUNT",
    "METRIC_CUSTOMER_RETURN_COUNT",
    "METRIC_EVIDENCE_LINKED_COUNT",
    "WINDOW_ALL",
    "WINDOW_DAY",
    "WINDOW_WEEK",
    "WINDOW_MONTH",
    "SUPPORTED_WINDOWS",
    "STORE_GRAIN_IDENTITY",
    "ProductMetricDefinition",
    "METRIC_DEFINITIONS",
    "METRIC_KEY_TO_DEFINITION",
    "SIGNAL_TYPE_TO_METRIC_KEY",
    "METRIC_KEYS",
    "metric_family_for_key",
    "metric_key_for_signal_type",
]
