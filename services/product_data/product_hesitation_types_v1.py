# -*- coding: utf-8 -*-
"""
Hesitation Mapping v1 — shared types for the Product ↔ Reason foundation.

This module owns only the durable link between a canonical product identity and a
captured hesitation reason. It does NOT define a second reason truth source and it
does NOT carry any intelligence, scoring, ranking, or blame attribution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

# Mapping provenance — how the Product↔Reason fact entered this layer.
MAPPING_SOURCE_REASON_CAPTURE = "reason_capture"

MAPPING_SOURCE_VALUES = frozenset({MAPPING_SOURCE_REASON_CAPTURE})

MAX_REASON_LEN = 64
MAX_SUB_REASON_LEN = 64


@dataclass(frozen=True, slots=True)
class HesitationMappingPersistResult:
    """Outcome of a mapping persist attempt. Counts only — no insight."""

    inserted: int = 0
    skipped_duplicate: int = 0
    skipped_empty: int = 0
    skipped_invalid: int = 0

    def merge(self, other: "HesitationMappingPersistResult") -> "HesitationMappingPersistResult":
        return HesitationMappingPersistResult(
            inserted=self.inserted + other.inserted,
            skipped_duplicate=self.skipped_duplicate + other.skipped_duplicate,
            skipped_empty=self.skipped_empty + other.skipped_empty,
            skipped_invalid=self.skipped_invalid + other.skipped_invalid,
        )


def normalize_reason(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip().lower()
    return s[:MAX_REASON_LEN]


def normalize_sub_reason(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().lower()
    if not s:
        return None
    return s[:MAX_SUB_REASON_LEN]


def hesitation_mapping_to_dict(row: Any) -> dict[str, Any]:
    """Read-model dict for read helpers and tests."""
    return {
        "id": getattr(row, "id", None),
        "store_slug": getattr(row, "store_slug", "") or "",
        "session_id": getattr(row, "session_id", "") or "",
        "cart_id": getattr(row, "cart_id", "") or "",
        "recovery_key": getattr(row, "recovery_key", None),
        "stable_identity_key": getattr(row, "stable_identity_key", "") or "",
        "identity_tier": getattr(row, "identity_tier", "") or "",
        "product_id": getattr(row, "product_id", None),
        "name": getattr(row, "name", None),
        "reason": getattr(row, "reason", "") or "",
        "sub_reason": getattr(row, "sub_reason", None),
        "mapping_confidence": getattr(row, "mapping_confidence", "") or "",
        "mapping_source": getattr(row, "mapping_source", "") or "",
        "captured_at": getattr(row, "captured_at", None),
    }


__all__ = [
    "HesitationMappingPersistResult",
    "MAPPING_SOURCE_REASON_CAPTURE",
    "MAPPING_SOURCE_VALUES",
    "MAX_REASON_LEN",
    "MAX_SUB_REASON_LEN",
    "hesitation_mapping_to_dict",
    "normalize_reason",
    "normalize_sub_reason",
]
