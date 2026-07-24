# -*- coding: utf-8 -*-
"""
Approved Observation Reality Validation mass (DEMO-PERFUME).

Temporary ORV surface only — same evidence shape as the reviewed Reality
Validation lab. Used when durable demo mass is incomplete so production Home
can paint the approved four cards (statement + action + confidence).
"""
from __future__ import annotations

from typing import Any

from services.product_data.product_signal_types_v1 import (
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
)

ORV_APPROVED_PRODUCT_KEY = "DEMO-PERFUME"


def approved_orv_validation_signals_v1() -> list[dict[str, Any]]:
    """Signal list that yields all four approved ORV statement capabilities."""
    pk = ORV_APPROVED_PRODUCT_KEY
    return [
        {
            "signal_type": SIGNAL_PRODUCT_CART_ADDED,
            "stable_identity_key": pk,
            "product_key": pk,
            "session_id": "orv-s1",
            "evidence_ref_id": "orv-add-1",
            "source": "orv_approved_mass_v1",
        },
        {
            "signal_type": SIGNAL_PRODUCT_CART_ADDED,
            "stable_identity_key": pk,
            "product_key": pk,
            "session_id": "orv-s2",
            "evidence_ref_id": "orv-add-2",
            "source": "orv_approved_mass_v1",
        },
        {
            "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
            "stable_identity_key": pk,
            "product_key": pk,
            "reason_code": "shipping",
            "evidence_ref_id": "orv-h-ship",
            "source": "orv_approved_mass_v1",
        },
        {
            "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
            "stable_identity_key": pk,
            "product_key": pk,
            "reason_code": "thinking",
            "evidence_ref_id": "orv-h-think",
            "source": "orv_approved_mass_v1",
        },
        {
            "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
            "stable_identity_key": pk,
            "product_key": pk,
            "customer_key": "orv-c1",
            "session_id": "orv-r1",
            "evidence_ref_id": "orv-ret-1",
            "source": "orv_approved_mass_v1",
        },
        {
            "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
            "stable_identity_key": pk,
            "product_key": pk,
            "customer_key": "orv-c1",
            "session_id": "orv-r2",
            "evidence_ref_id": "orv-ret-2",
            "source": "orv_approved_mass_v1",
        },
    ]


__all__ = [
    "ORV_APPROVED_PRODUCT_KEY",
    "approved_orv_validation_signals_v1",
]
