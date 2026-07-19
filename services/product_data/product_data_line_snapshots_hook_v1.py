# -*- coding: utf-8 -*-
"""Thin delegate for cart line snapshot hooks from ``main.py`` (≤4 lines total impact)."""
from __future__ import annotations

from typing import Any


def product_data_try_line_snapshots(
    payload: dict[str, Any],
    *,
    event_hint: str | None = None,
) -> None:
    """Persist ``lines[]`` when event is cart_state_sync or cart_abandoned. Never raises."""
    try:
        from services.product_data.product_cart_snapshots_v1 import (
            CAPTURE_SOURCE_CART_ABANDONED,
            CAPTURE_SOURCE_CART_STATE_SYNC,
            try_persist_cart_line_snapshots_from_payload,
        )

        ev = str(event_hint or payload.get("event") or "").strip().lower()
        if ev == "cart_state_sync":
            try_persist_cart_line_snapshots_from_payload(
                payload, capture_source=CAPTURE_SOURCE_CART_STATE_SYNC
            )
        elif ev == "cart_abandoned":
            try_persist_cart_line_snapshots_from_payload(
                payload, capture_source=CAPTURE_SOURCE_CART_ABANDONED
            )
        from services.product_data.product_catalog_hook_v1 import (  # noqa: PLC0415
            product_data_try_catalog_normalize,
        )

        product_data_try_catalog_normalize(payload, event_hint=ev)
        from services.product_data.product_signal_hook_v1 import (  # noqa: PLC0415
            product_signal_try_from_cart_payload,
        )

        product_signal_try_from_cart_payload(payload, event_hint=ev)
    except Exception:  # noqa: BLE001
        pass


__all__ = ["product_data_try_line_snapshots"]
