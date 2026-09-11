# -*- coding: utf-8 -*-
"""Platform adapter interface — normalize marketplace payloads into CartFlow Core events."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from integrations.normalized_platform_event import NormalizedPlatformEvent


class PlatformAdapter(ABC):
    """Each marketplace implements this interface; core never imports platform SDKs."""

    platform_id: str = ""

    @abstractmethod
    def normalize_event(self, raw_payload: dict[str, Any]) -> Optional[NormalizedPlatformEvent]:
        """Map platform webhook/API body to ``NormalizedPlatformEvent`` (or None if unsupported)."""

    def verify_signature(self, headers: dict[str, Any], raw_body: bytes) -> bool:
        """Verify webhook authenticity. Scaffold: always False until platform wiring."""
        return False

    def map_store(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        """Return ``store_slug`` / ``external_store_id`` hints (no DB writes)."""
        return {}

    def extract_customer(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    def extract_cart(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    def extract_order(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    def map_order_economic_fact(self, raw_payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Platform-neutral paid-order money candidate, or None if fail-closed."""
        return None

    def verify_connection(self, store: Any) -> Any:
        """Platform-specific connection verification. Core consumes a normalized capability."""
        return None
