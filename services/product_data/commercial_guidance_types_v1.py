# -*- coding: utf-8 -*-
"""Commercial Guidance Foundation V1 — catalog constants."""
from __future__ import annotations

GUIDANCE_VERSION_V1 = "cgf_v1"
GENERATION_VERSION_V1 = "cgf_v1_gen"
REGISTRY_VERSION_V1 = "cgf_reg_v1"
SOURCE_CONTRACT_VERSION_V1 = "gef_v1_guidance_context"
GUIDANCE_SCOPE_V1 = "commercial_v1"

STATUS_ACTIVE = "active"
STATUS_DEFERRED = "deferred"
STATUS_ABSTAINED = "abstained"
STATUS_EXPIRED = "expired"
STATUS_SUPERSEDED = "superseded"

GUIDANCE_STATUSES = frozenset(
    {
        STATUS_ACTIVE,
        STATUS_DEFERRED,
        STATUS_ABSTAINED,
        STATUS_EXPIRED,
        STATUS_SUPERSEDED,
    }
)

KEY_CONTINUE_OBSERVING = "continue_observing"
KEY_INVESTIGATE_CONVERSION = "investigate_conversion_path"
KEY_REVIEW_PRODUCT = "review_product_experience"
KEY_REVIEW_CART = "review_cart_progression"
KEY_VERIFY_GAP = "verify_evidence_gap"
KEY_MONITOR_NEW = "monitor_new_pattern"
KEY_DEFER = "defer_until_more_evidence"
KEY_NO_GUIDANCE = "no_guidance"

GUIDANCE_KEYS = frozenset(
    {
        KEY_CONTINUE_OBSERVING,
        KEY_INVESTIGATE_CONVERSION,
        KEY_REVIEW_PRODUCT,
        KEY_REVIEW_CART,
        KEY_VERIFY_GAP,
        KEY_MONITOR_NEW,
        KEY_DEFER,
        KEY_NO_GUIDANCE,
    }
)

DEFAULT_UNKNOWN_FACTS = (
    "The current evidence does not establish a commercial root cause "
    "(shipping, pricing, checkout friction, or product suitability)."
)

DEFAULT_PROHIBITED_CLAIMS = (
    "Do not claim a specific root cause.",
    "Do not recommend price, discount, campaign, or inventory changes.",
    "Do not assert that checkout is broken or that advertising should increase.",
)

INTENT_METRIC_KEYS = frozenset(
    {
        "cart_added_count",
        "cart_abandoned_count",
        "checkout_touched_count",
        "cart_synced_count",
    }
)

CART_PROGRESSION_METRIC_KEYS = frozenset(
    {
        "cart_abandoned_count",
        "cart_removed_count",
        "checkout_touched_count",
    }
)

__all__ = [
    "GUIDANCE_VERSION_V1",
    "GENERATION_VERSION_V1",
    "REGISTRY_VERSION_V1",
    "SOURCE_CONTRACT_VERSION_V1",
    "GUIDANCE_SCOPE_V1",
    "STATUS_ACTIVE",
    "STATUS_DEFERRED",
    "STATUS_ABSTAINED",
    "STATUS_EXPIRED",
    "STATUS_SUPERSEDED",
    "GUIDANCE_STATUSES",
    "KEY_CONTINUE_OBSERVING",
    "KEY_INVESTIGATE_CONVERSION",
    "KEY_REVIEW_PRODUCT",
    "KEY_REVIEW_CART",
    "KEY_VERIFY_GAP",
    "KEY_MONITOR_NEW",
    "KEY_DEFER",
    "KEY_NO_GUIDANCE",
    "GUIDANCE_KEYS",
    "DEFAULT_UNKNOWN_FACTS",
    "DEFAULT_PROHIBITED_CLAIMS",
    "INTENT_METRIC_KEYS",
    "CART_PROGRESSION_METRIC_KEYS",
]
