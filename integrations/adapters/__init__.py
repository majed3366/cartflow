# -*- coding: utf-8 -*-
"""Platform adapters (scaffold only — no live API wiring in v1)."""
from integrations.adapters.base import PlatformAdapter
from integrations.adapters.salla import SallaAdapter
from integrations.adapters.shopify import ShopifyAdapter
from integrations.adapters.zid import ZidAdapter

__all__ = [
    "PlatformAdapter",
    "ZidAdapter",
    "SallaAdapter",
    "ShopifyAdapter",
]
