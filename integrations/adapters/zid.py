# -*- coding: utf-8 -*-
"""Zid adapter — webhook scaffold plus verified connection (Manager probe)."""
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

    def map_order_economic_fact(self, raw_payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        from integrations.zid_order_economic_v1 import map_zid_order_view_to_economic_candidate

        return map_zid_order_view_to_economic_candidate(raw_payload)

    def verify_connection(self, store: Any) -> Any:
        """Zid verified connection — Manager probe + identity bind. Not a dashboard path."""
        from services.zid_connection_verification_v1 import (  # noqa: PLC0415
            verify_and_persist_zid_connection,
        )

        return verify_and_persist_zid_connection(store, trigger="adapter")
