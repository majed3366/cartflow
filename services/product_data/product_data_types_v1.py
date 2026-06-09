# -*- coding: utf-8 -*-
"""Product Data Foundation v1 — shared types and configurable readiness thresholds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Readiness classification (store-level product coverage)
READINESS_READY = "ready"
READINESS_PARTIAL = "partial"
READINESS_LIMITED = "limited"

READINESS_VALUES = frozenset({READINESS_READY, READINESS_PARTIAL, READINESS_LIMITED})

# Overall data confidence (field quality, not insight confidence)
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

CONFIDENCE_VALUES = frozenset({CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW})


@dataclass(frozen=True, slots=True)
class ProductDataHealthThresholds:
    """Configurable gates for readiness + confidence classification."""

    ready_min_coverage: float = 0.80
    partial_min_coverage: float = 0.40
    confidence_high_min_coverage: float = 0.80
    confidence_high_min_product_id_coverage: float = 0.60
    confidence_medium_min_coverage: float = 0.40
    confidence_medium_min_product_id_coverage: float = 0.30

    def __post_init__(self) -> None:
        if not 0.0 <= self.partial_min_coverage <= self.ready_min_coverage <= 1.0:
            raise ValueError("invalid coverage threshold ordering")
        if not 0.0 <= self.confidence_medium_min_product_id_coverage <= 1.0:
            raise ValueError("invalid confidence thresholds")


DEFAULT_HEALTH_THRESHOLDS = ProductDataHealthThresholds()


@dataclass
class ProductDataHealthReport:
    """Read-only product data readiness for one store."""

    ok: bool = True
    store_slug: str = ""
    window_days: int = 7
    readiness: str = READINESS_LIMITED
    coverage: float = 0.0
    product_name_coverage: float = 0.0
    product_id_coverage: float = 0.0
    variant_coverage: float = 0.0
    catalog_available: bool = False
    confidence: str = CONFIDENCE_LOW
    cart_sample_size: int = 0
    store_resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "store_slug": self.store_slug,
            "window_days": self.window_days,
            "readiness": self.readiness,
            "coverage": round(self.coverage, 4),
            "product_name_coverage": round(self.product_name_coverage, 4),
            "product_id_coverage": round(self.product_id_coverage, 4),
            "variant_coverage": round(self.variant_coverage, 4),
            "catalog_available": self.catalog_available,
            "confidence": self.confidence,
            "cart_sample_size": self.cart_sample_size,
            "store_resolved": self.store_resolved,
        }


def classify_readiness(
    coverage: float,
    *,
    thresholds: ProductDataHealthThresholds = DEFAULT_HEALTH_THRESHOLDS,
) -> str:
    if coverage >= thresholds.ready_min_coverage:
        return READINESS_READY
    if coverage >= thresholds.partial_min_coverage:
        return READINESS_PARTIAL
    return READINESS_LIMITED


def classify_confidence(
    coverage: float,
    product_id_coverage: float,
    *,
    thresholds: ProductDataHealthThresholds = DEFAULT_HEALTH_THRESHOLDS,
) -> str:
    if (
        coverage >= thresholds.confidence_high_min_coverage
        and product_id_coverage >= thresholds.confidence_high_min_product_id_coverage
    ):
        return CONFIDENCE_HIGH
    if (
        coverage >= thresholds.confidence_medium_min_coverage
        or product_id_coverage >= thresholds.confidence_medium_min_product_id_coverage
    ):
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW
