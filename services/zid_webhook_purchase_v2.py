# -*- coding: utf-8 -*-
"""Zid webhook → canonical purchase truth ingest (v2)."""
from __future__ import annotations

from typing import Any, Optional


_ZID_PURCHASE_EVENT_FRAGMENTS = (
    "order.paid",
    "order_paid",
    "order.paid.success",
    "checkout.completed",
    "checkout_completed",
    "purchase.completed",
    "purchase_completed",
)

_ZID_ORDER_PAID_STATUS = frozenset(
    {
        "paid",
        "completed",
        "complete",
        "success",
        "successful",
    }
)


def _norm_event(raw: Any) -> str:
    return str(raw or "").strip().lower().replace(" ", "_")


def zid_payload_indicates_purchase(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("purchase_completed") is True or payload.get("order_paid") is True:
        return True
    ev = _norm_event(payload.get("event") or payload.get("type") or "")
    if not ev:
        return False
    if ev in _ZID_PURCHASE_EVENT_FRAGMENTS:
        return True
    if "order" in ev and "paid" in ev:
        return True
    status = _norm_event(
        payload.get("order_status")
        or payload.get("status")
        or (payload.get("order") or {}).get("status")
        if isinstance(payload.get("order"), dict)
        else ""
    )
    if status in _ZID_ORDER_PAID_STATUS and ("order" in ev or payload.get("order_id")):
        return True
    return False


def build_zid_purchase_truth_payload(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Map Zid webhook body to ingest shape when purchase/order-paid is detected.
    """
    if not zid_payload_indicates_purchase(payload):
        return None

    pl = dict(payload)
    ev = _norm_event(pl.get("event") or pl.get("type") or "zid.webhook")
    source = "order_paid" if "paid" in ev else "purchase_completed"
    if pl.get("order_paid") is True:
        source = "order_paid"
    elif pl.get("purchase_completed") is True:
        source = "purchase_completed"

    store = (
        str(pl.get("store_slug") or pl.get("store") or pl.get("merchant_id") or "")
        .strip()
    )
    session = str(pl.get("session_id") or pl.get("cart_id") or "").strip()
    if not session:
        cart = pl.get("cart") if isinstance(pl.get("cart"), dict) else {}
        session = str(
            pl.get("zid_cart_id")
            or pl.get("external_cart_id")
            or cart.get("id")
            or cart.get("cart_id")
            or ""
        ).strip()
    order_id = str(
        pl.get("order_id")
        or pl.get("zid_order_id")
        or (pl.get("order") or {}).get("id")
        if isinstance(pl.get("order"), dict)
        else ""
    ).strip()

    out: dict[str, Any] = {
        **pl,
        "store_slug": store or pl.get("store_slug"),
        "store": store or pl.get("store"),
        "session_id": session,
        "purchase_source": f"zid_webhook:{source}",
        "order_paid": source == "order_paid",
        "purchase_completed": source == "purchase_completed",
        "event": source,
        "_zid_purchase_truth_v2": True,
    }
    if order_id:
        out["order_id"] = order_id
        out["zid_order_id"] = order_id
    try:
        from services.journey_identity_resolver_v1 import (  # noqa: PLC0415
            maybe_log_journey_identity_shadow,
        )

        maybe_log_journey_identity_shadow(out, source="zid_purchase_truth_payload")
    except Exception:  # noqa: BLE001
        pass
    return out


__all__ = [
    "build_zid_purchase_truth_payload",
    "zid_payload_indicates_purchase",
]
