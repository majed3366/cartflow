# -*- coding: utf-8 -*-
"""
Merchant-safe diagnostic publication — no evidence tables / confidence math.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.diagnostic_reasoning_v1.contract_v1 import (
    DIAGNOSIS_STATUS_SUPPORTED,
    DIAGNOSTIC_VERSION_V1,
)


def publish_diagnostic_for_merchant_v1(
    contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Strip technical fields for Home / publication surfaces."""
    c = contract if isinstance(contract, Mapping) else {}
    status = str(c.get("diagnosis_status") or "")
    return {
        "ok": bool(c.get("contract_ok", True)),
        "schema": "diagnostic_publication_v1",
        "diagnostic_version": DIAGNOSTIC_VERSION_V1,
        "diagnostic_id": str(c.get("diagnostic_id") or ""),
        "diagnostic_family": str(c.get("diagnostic_family") or ""),
        "subject_type": str(c.get("subject_type") or ""),
        "subject_id": str(c.get("subject_id") or ""),
        "observation_ar": str(c.get("observation_ar") or ""),
        "diagnosis_ar": str(c.get("diagnosis_ar") or ""),
        "recommendation_ar": str(c.get("recommendation_ar") or ""),
        "diagnosis_status": status,
        # Confidence is not painted on Home; kept for Workspace later.
        "confidence_level": str(c.get("confidence_level") or ""),
        "selected_diagnosis": c.get("selected_diagnosis"),
        "generated_at": c.get("generated_at"),
        "expires_at": c.get("expires_at"),
        "freshness": "ready",
        "is_causal": status == DIAGNOSIS_STATUS_SUPPORTED,
        "merchant_safe": True,
    }


def pick_primary_diagnostic_publication_v1(
    publications: list[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    """Prefer supported causal diagnosis; else first honest insufficiency."""
    pubs = [dict(p) for p in publications if isinstance(p, Mapping)]
    for p in pubs:
        if p.get("diagnosis_status") == DIAGNOSIS_STATUS_SUPPORTED:
            return p
    return pubs[0] if pubs else None


__all__ = [
    "pick_primary_diagnostic_publication_v1",
    "publish_diagnostic_for_merchant_v1",
]
