# -*- coding: utf-8 -*-
"""
Purchase Mapping v1 — shared types for the Product ↔ Purchase foundation.

This module owns only the durable link between a canonical product identity and a
confirmed purchase (Purchase Truth). It does NOT define a second purchase truth
source and it does NOT carry intelligence, attribution scoring, or ranking.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

PURCHASE_SOURCE_TRUTH = "purchase_truth"

PURCHASE_SOURCE_VALUES = frozenset({PURCHASE_SOURCE_TRUTH})


@dataclass(frozen=True, slots=True)
class PurchaseMappingPersistResult:
    """Outcome of a purchase mapping persist attempt. Counts only — no insight."""

    inserted: int = 0
    skipped_duplicate: int = 0
    skipped_empty: int = 0
    skipped_invalid: int = 0


def purchase_mapping_to_dict(row: Any) -> dict[str, Any]:
    """Read-model dict for read helpers and tests."""
    return {
        "id": getattr(row, "id", None),
        "store_slug": getattr(row, "store_slug", "") or "",
        "session_id": getattr(row, "session_id", "") or "",
        "cart_id": getattr(row, "cart_id", "") or "",
        "recovery_key": getattr(row, "recovery_key", None),
        "order_id": getattr(row, "order_id", None),
        "stable_identity_key": getattr(row, "stable_identity_key", "") or "",
        "product_id": getattr(row, "product_id", None),
        "name": getattr(row, "name", None),
        "quantity": getattr(row, "quantity", None),
        "unit_price": getattr(row, "unit_price", None),
        "purchase_confidence": getattr(row, "purchase_confidence", "") or "",
        "purchase_source": getattr(row, "purchase_source", "") or "",
        "purchased_at": getattr(row, "purchased_at", None),
    }


__all__ = [
    "PURCHASE_SOURCE_TRUTH",
    "PURCHASE_SOURCE_VALUES",
    "PurchaseMappingPersistResult",
    "purchase_mapping_to_dict",
]
