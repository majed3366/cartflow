# -*- coding: utf-8 -*-
"""Zid adapter scaffold — no OAuth, no live API, no webhook wiring in foundation v1."""
from __future__ import annotations

from typing import Any, Optional

from integrations.adapters.base import PlatformAdapter
from integrations.normalized_platform_event import NormalizedPlatformEvent


class ZidAdapter(PlatformAdapter):
    platform_id = "zid"

    def normalize_event(self, raw_payload: dict[str, Any]) -> Optional[NormalizedPlatformEvent]:
        # Future: map Zid webhook schema → NormalizedPlatformEvent
        return None

    def verify_signature(self, headers: dict[str, Any], raw_body: bytes) -> bool:
        # Future: delegate to integrations.zid_client.verify_webhook_signature
        return False

    def map_store(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {"platform": self.platform_id, "external_store_id": str(raw_payload.get("store_id") or "")}

    def extract_customer(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    def extract_cart(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    def extract_order(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}
