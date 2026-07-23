# -*- coding: utf-8 -*-
"""
Visitor proxy detection — WP-ET-08 / Gate B / Architecture §2.1.

Hard rule: carts, abandoned carts, or recovery rows must never proxy Visitor Evidence.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.evidence_truth.families_v1 import FAMILY_VISITOR
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1
from services.evidence_truth.observation_types_v1 import RAW_KIND_TRAFFIC

# Payload / event markers that indicate cart-as-traffic (forbidden proxies)
_CART_PROXY_EVENTS = frozenset(
    {
        "cart_abandoned",
        "cart_state_sync",
        "cart_updated",
        "abandoned",
        "add_to_cart",
        "atc",
    }
)
_PROXY_COUNT_KEYS = frozenset(
    {
        "abandoned_cart_count",
        "cart_count",
        "active_carts",
        "recovery_count",
        "visitor_total_from_carts",
    }
)


def detect_visitor_proxy_v1(
    payload: Mapping[str, Any] | None,
    *,
    observation: CanonicalObservationV1 | None = None,
    raw_kind: str = "",
) -> Optional[str]:
    """
    Return a proxy reason code if Visitor Evidence must not be published,
    else None.
    """
    if observation is not None:
        if observation.canonical_family != FAMILY_VISITOR:
            return "proxy_wrong_family"
        if observation.raw_kind != RAW_KIND_TRAFFIC:
            return "proxy_non_traffic_raw"
    kind = (raw_kind or (observation.raw_kind if observation else "") or "").strip().lower()
    if kind and kind != RAW_KIND_TRAFFIC:
        return "proxy_non_traffic_raw"

    if not isinstance(payload, Mapping):
        payload = {}

    event = str(payload.get("event") or "").strip().lower()
    if event in _CART_PROXY_EVENTS:
        return "proxy_cart_event"

    for key in _PROXY_COUNT_KEYS:
        if key in payload and payload.get(key) is not None:
            return f"proxy_count_field:{key}"

    # Recovery-row-as-visitor without presence identity
    has_recovery = bool(str(payload.get("recovery_key") or "").strip())
    has_presence = bool(
        str(payload.get("visitor_id") or payload.get("anonymous_id") or "").strip()
        or str(payload.get("session_id") or "").strip()
    )
    if has_recovery and not has_presence and event in {"", "recovery", "abandoned_cart"}:
        return "proxy_recovery_without_presence"

    source = str(payload.get("source") or "").strip().lower()
    if "abandoned_cart" in source or source.startswith("cart_"):
        return "proxy_cart_source"

    return None


def visitor_channel_available_v1(
    payload: Mapping[str, Any] | None,
    *,
    source_channel: str = "",
) -> bool:
    """
    Honest channel availability for Visitor Evidence.

    Unavailable when no presence channel / identity markers exist.
    """
    if not isinstance(payload, Mapping):
        payload = {}
    channel = (source_channel or "").strip().lower()
    if channel in {"", "unknown", "none", "unavailable"}:
        # Still allow if explicit presence identity is present (SDK may omit channel label)
        has_presence = bool(
            str(payload.get("visitor_id") or payload.get("anonymous_id") or "").strip()
            or str(payload.get("session_id") or "").strip()
        )
        if not has_presence:
            return False
    explicit = payload.get("channel_available")
    if explicit is False:
        return False
    if str(payload.get("channel_status") or "").strip().lower() in {
        "unavailable",
        "absent",
        "none",
    }:
        return False
    return True
