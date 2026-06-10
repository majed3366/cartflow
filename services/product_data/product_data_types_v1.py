# -*- coding: utf-8 -*-
"""Product Data Foundation v1 — shared types and configurable readiness thresholds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

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
    foundation: Any = None
    identity_coverage: Any = None

    def to_dict(self) -> dict[str, Any]:
        payload_health = {
            "readiness": self.readiness,
            "coverage": round(self.coverage, 4),
            "product_name_coverage": round(self.product_name_coverage, 4),
            "product_id_coverage": round(self.product_id_coverage, 4),
            "variant_coverage": round(self.variant_coverage, 4),
            "catalog_available": self.catalog_available,
            "confidence": self.confidence,
            "cart_sample_size": self.cart_sample_size,
        }
        if self.foundation is not None and hasattr(self.foundation, "to_dict"):
            foundation_health = self.foundation.to_dict()
        else:
            foundation_health = {
                "readiness": READINESS_LIMITED,
                "snapshot_coverage": 0.0,
                "catalog_coverage": 0.0,
                "hesitation_mapping_coverage": 0.0,
                "purchase_mapping_coverage": 0.0,
                "snapshot_rows": 0,
                "catalog_rows": 0,
                "hesitation_mapping_rows": 0,
                "purchase_mapping_rows": 0,
                "reason_events": 0,
                "purchase_events": 0,
                "session_sample_size": 0,
                "sessions_with_snapshots": 0,
            }
        if self.identity_coverage is not None and hasattr(self.identity_coverage, "to_dict"):
            identity = self.identity_coverage.to_dict()
        else:
            identity = {
                "cart_sample_size": self.cart_sample_size,
                "carts_with_lines": 0,
                "carts_without_lines": 0,
                "lines_capture_rate": 0.0,
                "payload_lines_capture_rate": 0.0,
                "foundation_snapshot_capture_rate": 0.0,
                "identity_capture_status": "no_activity",
                "carts_with_payload_lines": 0,
                "carts_with_foundation_snapshots": 0,
            }
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
            "payload_health": payload_health,
            "foundation_health": foundation_health,
            "identity_coverage": identity,
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
