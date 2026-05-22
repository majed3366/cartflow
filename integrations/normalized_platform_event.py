# -*- coding: utf-8 -*-
"""Normalized platform events — CartFlow Core input contract (integration foundation v1)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# Supported normalized event types (platform-agnostic).
EVENT_CART_CREATED = "cart_created"
EVENT_CART_UPDATED = "cart_updated"
EVENT_CART_ABANDONED = "cart_abandoned"
EVENT_CHECKOUT_STARTED = "checkout_started"
EVENT_ORDER_CREATED = "order_created"
EVENT_ORDER_PAID = "order_paid"
EVENT_ORDER_CANCELLED = "order_cancelled"
EVENT_CUSTOMER_UPDATED = "customer_updated"

NORMALIZED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EVENT_CART_CREATED,
        EVENT_CART_UPDATED,
        EVENT_CART_ABANDONED,
        EVENT_CHECKOUT_STARTED,
        EVENT_ORDER_CREATED,
        EVENT_ORDER_PAID,
        EVENT_ORDER_CANCELLED,
        EVENT_CUSTOMER_UPDATED,
    }
)

PURCHASE_TRUTH_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EVENT_ORDER_PAID,
        EVENT_ORDER_CREATED,
    }
)


@dataclass
class NormalizedPlatformEvent:
    """
    Platform-agnostic event fed into ``platform_integration_gateway``.

    Adapters produce this shape; core logic never reads raw marketplace payloads directly.
    """

    platform: str
    store_slug: str
    event_type: str
    external_store_id: str = ""
    external_customer_id: str = ""
    external_cart_id: str = ""
    external_order_id: str = ""
    event_time: str = ""
    customer_phone: str = ""
    customer_email: str = ""
    cart_total: Optional[float] = None
    currency: str = ""
    items: list[Any] = field(default_factory=list)
    checkout_url: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "platform_adapter"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NormalizedPlatformEvent:
        d = dict(data or {})
        items = d.get("items")
        if not isinstance(items, list):
            items = []
        raw = d.get("raw_payload")
        if not isinstance(raw, dict):
            raw = {}
        ct = d.get("cart_total")
        cart_total: Optional[float]
        if ct is None or ct == "":
            cart_total = None
        else:
            try:
                cart_total = float(ct)
            except (TypeError, ValueError):
                cart_total = None
        conf = d.get("confidence", 1.0)
        try:
            confidence = float(conf)
        except (TypeError, ValueError):
            confidence = 1.0
        return cls(
            platform=str(d.get("platform") or "").strip(),
            store_slug=str(d.get("store_slug") or "").strip(),
            event_type=str(d.get("event_type") or "").strip().lower(),
            external_store_id=str(d.get("external_store_id") or "").strip(),
            external_customer_id=str(d.get("external_customer_id") or "").strip(),
            external_cart_id=str(d.get("external_cart_id") or "").strip(),
            external_order_id=str(d.get("external_order_id") or "").strip(),
            event_time=str(d.get("event_time") or "").strip(),
            customer_phone=str(d.get("customer_phone") or "").strip(),
            customer_email=str(d.get("customer_email") or "").strip(),
            cart_total=cart_total,
            currency=str(d.get("currency") or "").strip(),
            items=items,
            checkout_url=str(d.get("checkout_url") or "").strip(),
            raw_payload=raw,
            confidence=max(0.0, min(1.0, confidence)),
            source=str(d.get("source") or "platform_adapter").strip(),
        )
