# -*- coding: utf-8 -*-
"""Shopify adapter scaffold — not connected in foundation v1."""
from __future__ import annotations

from typing import Any, Optional

from integrations.adapters.base import PlatformAdapter
from integrations.normalized_platform_event import NormalizedPlatformEvent


class ShopifyAdapter(PlatformAdapter):
    platform_id = "shopify"

    def normalize_event(self, raw_payload: dict[str, Any]) -> Optional[NormalizedPlatformEvent]:
        return None

    def verify_signature(self, headers: dict[str, Any], raw_body: bytes) -> bool:
        return False

    def map_store(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {"platform": self.platform_id, "external_store_id": str(raw_payload.get("shop_id") or "")}

    def extract_customer(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    def extract_cart(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    def extract_order(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}
