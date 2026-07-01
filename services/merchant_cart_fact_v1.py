# -*- coding: utf-8 -*-
"""Merchant cart fact v1 — single headline fact per normal-cart row (read-only)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

FACT_KIND_PURCHASED = "purchased"
FACT_KIND_CHECKOUT = "checkout"
FACT_KIND_RETURNED = "returned"

LABEL_PURCHASED_AR = "تم الشراء"
LABEL_CHECKOUT_AR = "وصل العميل إلى صفحة الدفع"
LABEL_RETURNED_AR = "عاد العميل للموقع"

_STATE_COMPLETED = "completed"
_VARIANT_PURCHASED = "purchased"


def _behavioral_mapping(behavioral: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not behavioral or not isinstance(behavioral, dict):
        return {}
    return behavioral


def _purchased_fact(
    *,
    purchase_truth: bool,
    customer_lifecycle_state: str,
    customer_lifecycle_completed_variant: str,
) -> bool:
    if purchase_truth:
        return True
    state = (customer_lifecycle_state or "").strip().lower()
    variant = (customer_lifecycle_completed_variant or "").strip().lower()
    return state == _STATE_COMPLETED and variant == _VARIANT_PURCHASED


def _checkout_fact(behavioral: Mapping[str, Any] | None) -> bool:
    bh = _behavioral_mapping(behavioral)
    if bh.get("recovery_returned_checkout_page"):
        return True
    ctx = str(bh.get("recovery_return_context") or "").strip().lower()
    return ctx == "checkout"


def _return_fact(behavioral: Mapping[str, Any] | None) -> bool:
    bh = _behavioral_mapping(behavioral)
    if str(bh.get("recovery_return_timestamp") or "").strip():
        return True
    if bh.get("user_returned_to_site"):
        return True
    if bh.get("customer_returned_to_site"):
        return True
    return False


def resolve_merchant_cart_fact_v1(
    *,
    purchase_truth: bool = False,
    customer_lifecycle_state: str = "",
    customer_lifecycle_completed_variant: str = "",
    behavioral: Mapping[str, Any] | None = None,
    is_vip_lane: bool = False,
) -> Optional[dict[str, str]]:
    """Return at most one merchant fact dict, or None."""
    if is_vip_lane:
        return None
    if _purchased_fact(
        purchase_truth=purchase_truth,
        customer_lifecycle_state=customer_lifecycle_state,
        customer_lifecycle_completed_variant=customer_lifecycle_completed_variant,
    ):
        return {"kind": FACT_KIND_PURCHASED, "label_ar": LABEL_PURCHASED_AR}
    if _checkout_fact(behavioral):
        return {"kind": FACT_KIND_CHECKOUT, "label_ar": LABEL_CHECKOUT_AR}
    if _return_fact(behavioral):
        return {"kind": FACT_KIND_RETURNED, "label_ar": LABEL_RETURNED_AR}
    return None


def attach_merchant_cart_fact_v1(
    target: dict[str, Any],
    *,
    purchase_truth: bool = False,
    customer_lifecycle_state: str = "",
    customer_lifecycle_completed_variant: str = "",
    behavioral: Mapping[str, Any] | None = None,
    is_vip_lane: bool = False,
) -> None:
    """Attach ``merchant_cart_fact_v1`` when a fact resolves."""
    fact = resolve_merchant_cart_fact_v1(
        purchase_truth=purchase_truth,
        customer_lifecycle_state=customer_lifecycle_state,
        customer_lifecycle_completed_variant=customer_lifecycle_completed_variant,
        behavioral=behavioral,
        is_vip_lane=is_vip_lane,
    )
    if fact:
        target["merchant_cart_fact_v1"] = fact


__all__ = [
    "FACT_KIND_CHECKOUT",
    "FACT_KIND_PURCHASED",
    "FACT_KIND_RETURNED",
    "LABEL_CHECKOUT_AR",
    "LABEL_PURCHASED_AR",
    "LABEL_RETURNED_AR",
    "attach_merchant_cart_fact_v1",
    "resolve_merchant_cart_fact_v1",
]
