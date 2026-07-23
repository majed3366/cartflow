# -*- coding: utf-8 -*-
"""
Product signal classification — WP-ET-07 / C-10.

Hard rule: ATC / cart-line presence is not a product view.
"""
from __future__ import annotations

from typing import Any, Mapping

# Signal classes (provider-neutral)
SIGNAL_VIEW = "view"
SIGNAL_ATC = "atc"
SIGNAL_CART_LINE = "cart_line"
SIGNAL_INTEREST = "interest"
SIGNAL_UNKNOWN = "unknown"

_VIEW_MARKERS = frozenset(
    {
        "product_view",
        "pdp_view",
        "view",
        "product_viewed",
        "page_view_product",
        "impression_product",
    }
)
_ATC_MARKERS = frozenset(
    {
        "atc",
        "add_to_cart",
        "added_to_cart",
        "cart_add",
        "add",
    }
)
_CART_LINE_MARKERS = frozenset(
    {
        "cart_state_sync",
        "cart_abandoned",
        "cart_line",
        "line_snapshot",
        "product_line_snapshots:cart_state_sync",
        "product_line_snapshots:cart_abandoned",
    }
)


def classify_product_signal_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "",
) -> str:
    """
    Classify a product Raw/observation payload.

    Returns SIGNAL_* class. Never treats ATC/cart-line as VIEW.
    """
    if not isinstance(payload, Mapping):
        payload = {}
    explicit = str(payload.get("signal_class") or "").strip().lower()
    if explicit in {SIGNAL_VIEW, SIGNAL_ATC, SIGNAL_CART_LINE, SIGNAL_INTEREST}:
        if explicit == SIGNAL_ATC:
            return SIGNAL_ATC
        return explicit

    candidates = [
        str(payload.get("event") or "").strip().lower(),
        str(payload.get("capture_source") or "").strip().lower(),
        str(source or "").strip().lower(),
    ]
    joined = " ".join(c for c in candidates if c)

    for m in _VIEW_MARKERS:
        if m == joined or m in candidates or joined.endswith(f":{m}"):
            # Guard: cart_state_sync with reason=add is ATC-like, not view
            if "cart_state_sync" in joined and str(payload.get("reason") or "").strip().lower() == "add":
                return SIGNAL_ATC
            return SIGNAL_VIEW
    for m in _ATC_MARKERS:
        if m in candidates or m == joined:
            return SIGNAL_ATC
    for m in _CART_LINE_MARKERS:
        if m in candidates or m in joined:
            return SIGNAL_CART_LINE
    if "product" in joined and "view" in joined:
        return SIGNAL_VIEW
    if candidates[0] or candidates[1]:
        return SIGNAL_INTEREST
    return SIGNAL_UNKNOWN


def view_claimed_from_signal_class_v1(signal_class: str) -> bool:
    return (signal_class or "").strip().lower() == SIGNAL_VIEW


def atc_is_not_view_v1(signal_class: str) -> bool:
    """Constitutional: ATC/cart_line must never imply view."""
    sc = (signal_class or "").strip().lower()
    if sc in {SIGNAL_ATC, SIGNAL_CART_LINE}:
        return True
    return sc != SIGNAL_VIEW
