# -*- coding: utf-8 -*-
"""Non-blocking catalog normalization hook — chained from cart event delegate."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("cartflow")


def product_data_try_catalog_normalize(
    payload: dict[str, Any],
    *,
    event_hint: str | None = None,
) -> None:
    """
    Normalize Product Identity ``lines[]`` into canonical catalog entries.
    Never raises; does not modify snapshots or cart/recovery behavior.
    """
    try:
        ev = str(event_hint or payload.get("event") or "").strip().lower()
        if ev not in ("cart_state_sync", "cart_abandoned"):
            return

        from services.product_data.product_catalog_v1 import (
            upsert_catalog_from_payload_lines,
        )

        upsert_catalog_from_payload_lines(payload)
    except Exception as exc:  # noqa: BLE001
        log.debug("catalog normalize skipped: %s", exc)


__all__ = ["product_data_try_catalog_normalize"]
