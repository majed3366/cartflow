# -*- coding: utf-8 -*-
"""Zid webhook → canonical purchase truth ingest (v2).

Authoritative platform paid truth requires either:

    event == order.payment_status.update AND payment_status == paid

or the authenticated Zid subscription's observed root-order delivery shape:

    no event/type wrapper, root store_id + order id, payment_status == paid

Event-name fragments (order.paid, "paid" in event) are not payment truth.
"""
from __future__ import annotations

from typing import Any, Optional

ZID_PLATFORM_PAID_EVENT = "order.payment_status.update"
ZID_PLATFORM_PAID_STATUS = "paid"
SOURCE_ZID_PLATFORM_PAID = "zid_webhook:platform_paid"
SOURCE_ZID_PLATFORM_PAID_BRIDGE = "zid_webhook:platform_paid_bridge"

_REJECTED_PAYMENT_STATUSES = frozenset(
    {
        "pending",
        "authorized",
        "failed",
        "cancelled",
        "canceled",
        "voided",
        "refunded",
        "partially_refunded",
        "unpaid",
    }
)


def _norm_token(raw: Any) -> str:
    return str(raw or "").strip().lower().replace(" ", "_")


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def zid_order_body(payload: dict[str, Any]) -> dict[str, Any]:
    """Documented Order schema may be the payload, ``data``, or ``order``."""
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if isinstance(data, dict):
        nested = data.get("order")
        if isinstance(nested, dict):
            return nested
        return data
    order = payload.get("order")
    if isinstance(order, dict):
        return order
    return payload


def extract_zid_platform_event(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    data = _as_dict(payload.get("data"))
    for src in (payload, data):
        ev = _norm_token(src.get("event") or src.get("type") or "")
        if ev:
            return ev
    return ""


def extract_zid_payment_status(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    order = zid_order_body(payload)
    for src in (order, payload, _as_dict(payload.get("data"))):
        raw = src.get("payment_status")
        if raw is None or isinstance(raw, (dict, list)):
            continue
        token = _norm_token(raw)
        if token:
            return token
    return ""


def extract_zid_order_id(payload: dict[str, Any]) -> str:
    """Canonical Zid order id: documented ``id``, then ``code``, then CartFlow aliases."""
    if not isinstance(payload, dict):
        return ""
    order = zid_order_body(payload)
    for src in (order, payload, _as_dict(payload.get("data"))):
        for key in ("id", "code", "order_id", "zid_order_id"):
            raw = src.get(key)
            if raw is None or isinstance(raw, (dict, list, bool)):
                continue
            s = str(raw).strip()
            if s:
                return s
    return ""


def extract_zid_store_slug_claim(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    order = zid_order_body(payload)
    for src in (payload, order, _as_dict(payload.get("data"))):
        for key in ("store_slug", "store"):
            raw = src.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        merchant = src.get("merchant_id")
        if merchant is not None and not isinstance(merchant, (dict, list)):
            s = str(merchant).strip()
            if s:
                return s
    return ""


def _canonical_store_slug_from_identifier(identifier: Any) -> str:
    sid = str(identifier or "").strip()
    if not sid:
        return ""
    try:
        from services.store_identity_v1 import (  # noqa: PLC0415
            canonical_store_slug_on_row,
            resolve_store_row_by_identifier,
        )

        row, _via = resolve_store_row_by_identifier(sid)
        return str(canonical_store_slug_on_row(row) or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _store_slug_from_zid_store_id(store_id: Any) -> str:
    """Resolve Zid numeric/UUID/alias identity to CartFlow's canonical store key."""
    return _canonical_store_slug_from_identifier(store_id)


def resolve_zid_store_slug(payload: dict[str, Any]) -> str:
    claimed = extract_zid_store_slug_claim(payload)
    if claimed:
        canonical = _canonical_store_slug_from_identifier(claimed)
        if canonical:
            return canonical
        # Preserve the established contract for explicit CartFlow store claims.
        return claimed

    order = zid_order_body(payload)
    store_id = order.get("store_id")
    if store_id is None:
        store_id = payload.get("store_id")
    if store_id is None:
        store_id = _as_dict(payload.get("data")).get("store_id")
    return _store_slug_from_zid_store_id(store_id)


def _is_observed_zid_root_order_delivery(payload: dict[str, Any]) -> bool:
    """Narrow fallback for Zid's observed eventless root Order webhook body."""
    if not isinstance(payload, dict):
        return False
    if extract_zid_platform_event(payload):
        return False
    if isinstance(payload.get("data"), dict) or isinstance(payload.get("order"), dict):
        return False
    store_id = payload.get("store_id")
    if store_id is None or isinstance(store_id, (dict, list, bool)):
        return False
    if not str(store_id).strip():
        return False
    return bool(extract_zid_order_id(payload))


def zid_payload_indicates_platform_paid(payload: dict[str, Any]) -> bool:
    """Authoritative Zid paid transition, including observed root-order delivery."""
    if not isinstance(payload, dict):
        return False
    event = extract_zid_platform_event(payload)
    if event:
        if event != ZID_PLATFORM_PAID_EVENT:
            return False
    elif not _is_observed_zid_root_order_delivery(payload):
        return False
    status = extract_zid_payment_status(payload)
    if not status or status in _REJECTED_PAYMENT_STATUSES:
        return False
    return status == ZID_PLATFORM_PAID_STATUS


def zid_payload_indicates_purchase(payload: dict[str, Any]) -> bool:
    """Zid webhook purchase path = authoritative platform paid only."""
    return zid_payload_indicates_platform_paid(payload)


def build_zid_purchase_truth_payload(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Map a documented Zid paid webhook to ingest shape.

    Fail closed without payment_status=paid, supported delivery shape, order id,
    or store slug.
    """
    if not zid_payload_indicates_platform_paid(payload):
        return None

    order_id = extract_zid_order_id(payload)
    if not order_id:
        return None

    store = resolve_zid_store_slug(payload)
    if not store:
        return None

    pl = dict(payload)
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
    if not session:
        nested_cart = zid_order_body(pl).get("cart")
        if isinstance(nested_cart, dict):
            session = str(nested_cart.get("id") or nested_cart.get("cart_id") or "").strip()
    if not session:
        session = f"zid-order:{order_id}"

    out: dict[str, Any] = {
        **pl,
        "store_slug": store,
        "store": store,
        "session_id": session,
        "purchase_source": SOURCE_ZID_PLATFORM_PAID,
        "order_id": order_id,
        "zid_order_id": order_id,
        "event": ZID_PLATFORM_PAID_EVENT,
        "payment_status": ZID_PLATFORM_PAID_STATUS,
        "_zid_purchase_truth_v2": True,
        "_zid_platform_paid": True,
    }
    try:
        from services.journey_identity_resolver_v1 import (  # noqa: PLC0415
            maybe_log_journey_identity_shadow,
        )

        maybe_log_journey_identity_shadow(out, source="zid_purchase_truth_payload")
    except Exception:  # noqa: BLE001
        pass
    return out


__all__ = [
    "SOURCE_ZID_PLATFORM_PAID",
    "SOURCE_ZID_PLATFORM_PAID_BRIDGE",
    "ZID_PLATFORM_PAID_EVENT",
    "ZID_PLATFORM_PAID_STATUS",
    "build_zid_purchase_truth_payload",
    "extract_zid_order_id",
    "extract_zid_payment_status",
    "extract_zid_platform_event",
    "resolve_zid_store_slug",
    "zid_order_body",
    "zid_payload_indicates_platform_paid",
    "zid_payload_indicates_purchase",
]
