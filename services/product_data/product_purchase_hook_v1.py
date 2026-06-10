# -*- coding: utf-8 -*-
"""
Thin non-blocking delegate for Purchase Mapping v1.

Called from Purchase Truth ``record_purchase`` after a purchase is confirmed.
Maps canonical products present in the session to the purchase event. Never
raises — Purchase Truth, recovery, widget, and Knowledge all continue regardless.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger("cartflow")


def product_data_try_purchase_mapping(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    order_id: Optional[str] = None,
    purchase_source: str = "",
    purchased_at: Optional[datetime] = None,
) -> None:
    """Persist Product ↔ Purchase mappings after Purchase Truth confirmation. Never raises."""
    try:
        if not store_slug or not session_id or not purchase_source:
            return
        from services.product_data.product_purchase_mapping_v1 import (
            try_persist_purchase_mappings,
        )

        try_persist_purchase_mappings(
            store_slug,
            session_id,
            cart_id=cart_id,
            recovery_key=recovery_key,
            order_id=order_id,
            purchase_source=purchase_source,
            purchased_at=purchased_at,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("purchase mapping hook skipped: %s", exc)


__all__ = ["product_data_try_purchase_mapping"]
