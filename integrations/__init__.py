# -*- coding: utf-8 -*-
"""
CartFlow platform integrations — adapters normalize marketplace data; core stays independent.

Foundation v1: event contract + adapter scaffolds + gateway (no live Zid/Salla/Shopify wiring).
"""
from integrations.normalized_platform_event import (
    EVENT_CART_ABANDONED,
    EVENT_ORDER_PAID,
    NORMALIZED_EVENT_TYPES,
    NormalizedPlatformEvent,
)
from integrations.adapters import PlatformAdapter, SallaAdapter, ShopifyAdapter, ZidAdapter

__all__ = [
    "NormalizedPlatformEvent",
    "NORMALIZED_EVENT_TYPES",
    "EVENT_CART_ABANDONED",
    "EVENT_ORDER_PAID",
    "PlatformAdapter",
    "ZidAdapter",
    "SallaAdapter",
    "ShopifyAdapter",
]
