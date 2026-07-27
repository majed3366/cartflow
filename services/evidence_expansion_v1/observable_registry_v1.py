# -*- coding: utf-8 -*-
"""
Governed future observables per diagnostic family.

Every observable must answer: which diagnosis becomes more accurate if collected?
No random data collection.
"""
from __future__ import annotations

from typing import Any

from services.diagnostic_reasoning_v1.contract_v1 import (
    FAMILY_CHECKOUT_AFTER_SHIPPING,
    FAMILY_CONTACT_FOLLOWUP_BLOCKED,
    FAMILY_INTEREST_WITHOUT_PURCHASE,
    FAMILY_PAYMENT_FRICTION,
)

# observable_key → {separates_causes, diagnosis_families_benefited, description}
OBSERVABLE_CATALOG_V1: dict[str, dict[str, Any]] = {
    "shipping_cost_first_shown": {
        "separates_causes": ["shipping_cost", "late_shipping_disclosure"],
        "diagnosis_families": [FAMILY_CHECKOUT_AFTER_SHIPPING],
        "description": "First time shipping cost is shown to the visitor",
    },
    "shipping_option_selected": {
        "separates_causes": ["shipping_option_availability", "shipping_cost"],
        "diagnosis_families": [FAMILY_CHECKOUT_AFTER_SHIPPING],
        "description": "Selected shipping option before leave",
    },
    "delivery_estimate_shown": {
        "separates_causes": ["delivery_time", "shipping_cost"],
        "diagnosis_families": [FAMILY_CHECKOUT_AFTER_SHIPPING],
        "description": "Delivery estimate visibility at shipping step",
    },
    "shipping_method_changed": {
        "separates_causes": ["shipping_option_availability", "shipping_cost"],
        "diagnosis_families": [FAMILY_CHECKOUT_AFTER_SHIPPING],
        "description": "Visitor changed shipping method before abandon",
    },
    "payment_attempt_after_shipping": {
        "separates_causes": ["payment_friction", "shipping_cost", "delivery_time"],
        "diagnosis_families": [
            FAMILY_CHECKOUT_AFTER_SHIPPING,
            FAMILY_PAYMENT_FRICTION,
        ],
        "description": "Payment attempt after shipping step",
    },
    "return_after_shipping_step": {
        "separates_causes": ["shipping_cost", "delivery_time", "late_shipping_disclosure"],
        "diagnosis_families": [FAMILY_CHECKOUT_AFTER_SHIPPING],
        "description": "Return / revisit after shipping appeared",
    },
    "shipping_step_dwell_ms": {
        "separates_causes": ["shipping_cost", "delivery_time", "shipping_option_availability"],
        "diagnosis_families": [FAMILY_CHECKOUT_AFTER_SHIPPING],
        "description": "Dwell time on shipping step",
    },
    "image_gallery_interaction": {
        "separates_causes": ["product_images", "insufficient_evidence"],
        "diagnosis_families": [FAMILY_INTEREST_WITHOUT_PURCHASE],
        "description": "Product image gallery interaction",
    },
    "spec_expansion": {
        "separates_causes": ["product_quality", "insufficient_evidence"],
        "diagnosis_families": [FAMILY_INTEREST_WITHOUT_PURCHASE],
        "description": "Specification section expanded",
    },
    "review_reading": {
        "separates_causes": ["product_quality", "insufficient_evidence"],
        "diagnosis_families": [FAMILY_INTEREST_WITHOUT_PURCHASE],
        "description": "Product reviews read",
    },
    "comparison_behaviour": {
        "separates_causes": ["price", "insufficient_evidence"],
        "diagnosis_families": [FAMILY_INTEREST_WITHOUT_PURCHASE],
        "description": "Comparison / alternate product behaviour",
    },
    "repeated_product_visits": {
        "separates_causes": ["interest_without_purchase"],
        "diagnosis_families": [FAMILY_INTEREST_WITHOUT_PURCHASE],
        "description": "Repeated visits to same product",
    },
    "payment_method_chosen": {
        "separates_causes": ["payment_friction"],
        "diagnosis_families": [FAMILY_PAYMENT_FRICTION],
        "description": "Payment method selected",
    },
    "payment_failure": {
        "separates_causes": ["payment_friction"],
        "diagnosis_families": [FAMILY_PAYMENT_FRICTION],
        "description": "Payment failure event",
    },
    "coupon_attempt": {
        "separates_causes": ["price", "payment_friction"],
        "diagnosis_families": [
            FAMILY_PAYMENT_FRICTION,
            FAMILY_INTEREST_WITHOUT_PURCHASE,
        ],
        "description": "Coupon / discount attempt",
    },
    "address_editing": {
        "separates_causes": ["shipping_option_availability", "delivery_time"],
        "diagnosis_families": [FAMILY_CHECKOUT_AFTER_SHIPPING],
        "description": "Address editing during checkout",
    },
    "message_opened": {
        "separates_causes": ["missing_contact", "insufficient_evidence"],
        "diagnosis_families": [FAMILY_CONTACT_FOLLOWUP_BLOCKED],
        "description": "Recovery / outreach message opened",
    },
    "reply_delay": {
        "separates_causes": ["missing_contact"],
        "diagnosis_families": [FAMILY_CONTACT_FOLLOWUP_BLOCKED],
        "description": "Customer reply delay after outreach",
    },
    "revisit_after_message": {
        "separates_causes": ["missing_contact"],
        "diagnosis_families": [FAMILY_CONTACT_FOLLOWUP_BLOCKED],
        "description": "Store revisit after message",
    },
    "usable_phone_captured": {
        "separates_causes": ["missing_contact"],
        "diagnosis_families": [FAMILY_CONTACT_FOLLOWUP_BLOCKED],
        "description": "Usable phone number captured before leave",
    },
}

# Family → ordered missing observables that separate competing causes.
FAMILY_MISSING_OBSERVABLES_V1: dict[str, list[str]] = {
    FAMILY_CHECKOUT_AFTER_SHIPPING: [
        "shipping_cost_first_shown",
        "shipping_option_selected",
        "delivery_estimate_shown",
        "shipping_method_changed",
        "payment_attempt_after_shipping",
        "return_after_shipping_step",
        "shipping_step_dwell_ms",
        "address_editing",
    ],
    FAMILY_INTEREST_WITHOUT_PURCHASE: [
        "image_gallery_interaction",
        "spec_expansion",
        "review_reading",
        "comparison_behaviour",
        "repeated_product_visits",
        "coupon_attempt",
    ],
    FAMILY_PAYMENT_FRICTION: [
        "payment_method_chosen",
        "payment_failure",
        "payment_attempt_after_shipping",
        "coupon_attempt",
    ],
    FAMILY_CONTACT_FOLLOWUP_BLOCKED: [
        "usable_phone_captured",
        "message_opened",
        "reply_delay",
        "revisit_after_message",
    ],
}


def observables_for_family_v1(family: str) -> list[dict[str, Any]]:
    keys = list(FAMILY_MISSING_OBSERVABLES_V1.get(family) or [])
    out: list[dict[str, Any]] = []
    for key in keys:
        meta = OBSERVABLE_CATALOG_V1.get(key) or {}
        # Gate: must benefit at least one diagnosis family.
        benefited = list(meta.get("diagnosis_families") or [])
        if family not in benefited and benefited:
            continue
        if not benefited:
            continue
        out.append(
            {
                "observable_key": key,
                "description": meta.get("description") or key,
                "separates_causes": list(meta.get("separates_causes") or []),
                "diagnosis_families_benefited": benefited,
            }
        )
    return out


def assert_observable_benefits_diagnosis_v1(observable_key: str) -> bool:
    meta = OBSERVABLE_CATALOG_V1.get(observable_key) or {}
    return bool(meta.get("diagnosis_families")) and bool(meta.get("separates_causes"))


__all__ = [
    "FAMILY_MISSING_OBSERVABLES_V1",
    "OBSERVABLE_CATALOG_V1",
    "assert_observable_benefits_diagnosis_v1",
    "observables_for_family_v1",
]
