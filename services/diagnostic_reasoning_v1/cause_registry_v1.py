# -*- coding: utf-8 -*-
"""Candidate Cause Registry V1 — governed competing causes per family."""
from __future__ import annotations

from typing import Any

from services.diagnostic_reasoning_v1.contract_v1 import (
    AR_REC_CONTACT,
    AR_REC_CONTINUE,
    AR_REC_PAYMENT,
    AR_REC_SHIPPING_COST,
    FAMILY_CHECKOUT_AFTER_SHIPPING,
    FAMILY_CONTACT_FOLLOWUP_BLOCKED,
    FAMILY_INTEREST_WITHOUT_PURCHASE,
    FAMILY_PAYMENT_FRICTION,
)

# Signal tokens that may appear in bounded evidence bags.
SIGNAL_SHIPPING_COST = "shipping_cost"
SIGNAL_SHIPPING = "shipping"
SIGNAL_DELIVERY_TIME = "delivery_time"
SIGNAL_DELIVERY = "delivery"
SIGNAL_PAYMENT = "payment"
SIGNAL_PAYMENT_FRICTION = "payment_friction"
SIGNAL_PRICE = "price"
SIGNAL_NO_PHONE = "no_phone"
SIGNAL_SHIPPING_STAGE = "shipping_stage_observed"
SIGNAL_INTEREST = "interest_without_purchase"
SIGNAL_OPTIONS = "shipping_option_availability"
SIGNAL_LATE_DISCLOSURE = "late_shipping_disclosure"

CAUSE_REGISTRY_V1: dict[str, list[dict[str, Any]]] = {
    FAMILY_CHECKOUT_AFTER_SHIPPING: [
        {
            "cause_key": "shipping_cost",
            "supporting_signals": [SIGNAL_SHIPPING_COST],
            # Generic "shipping" alone is NOT enough to select cost.
            "weak_supporting_signals": [SIGNAL_SHIPPING],
            "contradicting_signals": [SIGNAL_DELIVERY_TIME, SIGNAL_DELIVERY, SIGNAL_PAYMENT],
            "minimum_evidence": 3,
            "identity_required": True,
            "safe_recommendation_ar": AR_REC_SHIPPING_COST,
            "suppression_conditions": ["sample_below_minimum", "tie_with_peer"],
        },
        {
            "cause_key": "delivery_time",
            "supporting_signals": [SIGNAL_DELIVERY_TIME],
            "weak_supporting_signals": [SIGNAL_DELIVERY],
            "contradicting_signals": [SIGNAL_SHIPPING_COST, SIGNAL_PAYMENT],
            "minimum_evidence": 3,
            "identity_required": True,
            "safe_recommendation_ar": "راجع مدة التوصيل المعروضة قبل إتمام الطلب.",
            "suppression_conditions": ["sample_below_minimum", "tie_with_peer"],
        },
        {
            "cause_key": "shipping_option_availability",
            "supporting_signals": [SIGNAL_OPTIONS],
            "weak_supporting_signals": [],
            "contradicting_signals": [SIGNAL_SHIPPING_COST, SIGNAL_DELIVERY_TIME],
            "minimum_evidence": 3,
            "identity_required": True,
            "safe_recommendation_ar": "راجع خيارات الشحن المتاحة عند نقطة المغادرة.",
            "suppression_conditions": ["sample_below_minimum", "missing_signal"],
        },
        {
            "cause_key": "late_shipping_disclosure",
            "supporting_signals": [SIGNAL_LATE_DISCLOSURE],
            "weak_supporting_signals": [],
            "contradicting_signals": [],
            "minimum_evidence": 3,
            "identity_required": True,
            "safe_recommendation_ar": "اعرض تقدير تكلفة الشحن قبل إتمام الطلب.",
            "suppression_conditions": ["sample_below_minimum", "missing_signal"],
        },
        {
            "cause_key": "payment_friction",
            "supporting_signals": [SIGNAL_PAYMENT_FRICTION, SIGNAL_PAYMENT],
            "weak_supporting_signals": [],
            "contradicting_signals": [SIGNAL_SHIPPING_COST, SIGNAL_DELIVERY_TIME],
            "minimum_evidence": 3,
            "identity_required": True,
            "safe_recommendation_ar": AR_REC_PAYMENT,
            "suppression_conditions": ["sample_below_minimum", "tie_with_peer"],
        },
        {
            "cause_key": "insufficient_evidence",
            "supporting_signals": [SIGNAL_SHIPPING_STAGE],
            "weak_supporting_signals": [SIGNAL_SHIPPING, SIGNAL_DELIVERY],
            "contradicting_signals": [],
            "minimum_evidence": 0,
            "identity_required": False,
            "safe_recommendation_ar": AR_REC_CONTINUE,
            "suppression_conditions": [],
        },
    ],
    FAMILY_INTEREST_WITHOUT_PURCHASE: [
        {
            "cause_key": "insufficient_evidence",
            "supporting_signals": [SIGNAL_INTEREST],
            "weak_supporting_signals": [],
            "contradicting_signals": [],
            "minimum_evidence": 0,
            "identity_required": False,
            "safe_recommendation_ar": AR_REC_CONTINUE,
            "suppression_conditions": [],
        },
        {
            "cause_key": "shipping_cost",
            "supporting_signals": [SIGNAL_SHIPPING_COST],
            "weak_supporting_signals": [],
            "contradicting_signals": [SIGNAL_PRICE, SIGNAL_PAYMENT],
            "minimum_evidence": 3,
            "identity_required": True,
            "safe_recommendation_ar": AR_REC_SHIPPING_COST,
            "suppression_conditions": ["sample_below_minimum"],
        },
        {
            "cause_key": "price",
            "supporting_signals": [SIGNAL_PRICE],
            "weak_supporting_signals": [],
            "contradicting_signals": [SIGNAL_SHIPPING_COST],
            "minimum_evidence": 3,
            "identity_required": True,
            "safe_recommendation_ar": "راجع السعر أو وضّح القيمة قبل إتمام الطلب.",
            "suppression_conditions": ["sample_below_minimum", "tie_with_peer"],
        },
    ],
    FAMILY_PAYMENT_FRICTION: [
        {
            "cause_key": "payment_friction",
            "supporting_signals": [SIGNAL_PAYMENT_FRICTION, SIGNAL_PAYMENT],
            "weak_supporting_signals": [],
            "contradicting_signals": [SIGNAL_SHIPPING_COST],
            "minimum_evidence": 3,
            "identity_required": True,
            "safe_recommendation_ar": AR_REC_PAYMENT,
            "suppression_conditions": ["sample_below_minimum"],
        },
        {
            "cause_key": "insufficient_evidence",
            "supporting_signals": [],
            "weak_supporting_signals": [],
            "contradicting_signals": [],
            "minimum_evidence": 0,
            "identity_required": False,
            "safe_recommendation_ar": AR_REC_CONTINUE,
            "suppression_conditions": [],
        },
    ],
    FAMILY_CONTACT_FOLLOWUP_BLOCKED: [
        {
            "cause_key": "missing_contact",
            "supporting_signals": [SIGNAL_NO_PHONE],
            "weak_supporting_signals": [],
            "contradicting_signals": [],
            "minimum_evidence": 1,
            "identity_required": False,
            "safe_recommendation_ar": AR_REC_CONTACT,
            "suppression_conditions": [],
        },
        {
            "cause_key": "insufficient_evidence",
            "supporting_signals": [],
            "weak_supporting_signals": [],
            "contradicting_signals": [],
            "minimum_evidence": 0,
            "identity_required": False,
            "safe_recommendation_ar": AR_REC_CONTINUE,
            "suppression_conditions": [],
        },
    ],
}


def causes_for_family_v1(family: str) -> list[dict[str, Any]]:
    return list(CAUSE_REGISTRY_V1.get(family) or [])


__all__ = [
    "CAUSE_REGISTRY_V1",
    "SIGNAL_DELIVERY",
    "SIGNAL_DELIVERY_TIME",
    "SIGNAL_INTEREST",
    "SIGNAL_LATE_DISCLOSURE",
    "SIGNAL_NO_PHONE",
    "SIGNAL_OPTIONS",
    "SIGNAL_PAYMENT",
    "SIGNAL_PAYMENT_FRICTION",
    "SIGNAL_PRICE",
    "SIGNAL_SHIPPING",
    "SIGNAL_SHIPPING_COST",
    "SIGNAL_SHIPPING_STAGE",
    "causes_for_family_v1",
]
