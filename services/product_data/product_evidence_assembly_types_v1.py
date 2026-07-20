# -*- coding: utf-8 -*-
"""
Product Evidence Assembly Foundation V1 — catalog constants.

Assembles Metrics + Trends into evidence bundles. No confidence or guidance.
"""
from __future__ import annotations

BUNDLE_VERSION_V1 = "pea_v1"
COMPUTATION_VERSION_V1 = "pea_v1_assemble"

SUBJECT_TYPE_PRODUCT = "product"
SUBJECT_TYPE_STORE = "store"
SUBJECT_TYPES = frozenset({SUBJECT_TYPE_PRODUCT, SUBJECT_TYPE_STORE})

SOURCE_LAYER_METRICS = "metrics"
SOURCE_LAYER_TRENDS = "trends"
SOURCE_LAYER_BOTH = "metrics+trends"

SOURCE_LAYERS = frozenset(
    {
        SOURCE_LAYER_METRICS,
        SOURCE_LAYER_TRENDS,
        SOURCE_LAYER_BOTH,
    }
)

__all__ = [
    "BUNDLE_VERSION_V1",
    "COMPUTATION_VERSION_V1",
    "SUBJECT_TYPE_PRODUCT",
    "SUBJECT_TYPE_STORE",
    "SUBJECT_TYPES",
    "SOURCE_LAYER_METRICS",
    "SOURCE_LAYER_TRENDS",
    "SOURCE_LAYER_BOTH",
    "SOURCE_LAYERS",
]
