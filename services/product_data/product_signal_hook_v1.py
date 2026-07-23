# -*- coding: utf-8 -*-
"""
Thin never-raise delegates for Product Signal Collection V1.

Attached to existing PDF / purchase / recovery / return paths. Never blocks
cart-event, Purchase Truth, widget, or recovery.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

log = logging.getLogger("cartflow")


def product_signal_try_from_cart_payload(
    payload: dict[str, Any],
    *,
    event_hint: str | None = None,
) -> None:
    try:
        from services.product_data.product_signal_collection_v1 import (
            collect_from_cart_payload,
        )

        collect_from_cart_payload(payload, event_hint=event_hint)
    except Exception as exc:  # noqa: BLE001
        log.debug("product signal cart hook skipped: %s", exc)


def product_signal_try_from_hesitation(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
) -> None:
    try:
        from services.product_data.product_signal_collection_v1 import (
            collect_from_hesitation,
        )

        collect_from_hesitation(
            store_slug,
            session_id,
            cart_id=cart_id,
            recovery_key=recovery_key,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("product signal hesitation hook skipped: %s", exc)


def product_signal_try_from_purchase(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    order_id: Optional[str] = None,
    purchased_at: Optional[datetime] = None,
) -> None:
    try:
        from services.product_data.product_signal_collection_v1 import (
            collect_from_purchase,
        )

        collect_from_purchase(
            store_slug,
            session_id,
            cart_id=cart_id,
            recovery_key=recovery_key,
            order_id=order_id,
            purchased_at=purchased_at,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("product signal purchase hook skipped: %s", exc)


def product_signal_try_from_recovery_timeline(
    *,
    store_slug: str,
    session_id: str,
    status: str,
    cart_id: str = "",
    recovery_key: Optional[str] = None,
    timeline_event_id: Optional[int] = None,
) -> None:
    try:
        from services.product_data.product_signal_collection_v1 import (
            collect_from_recovery_timeline,
        )

        collect_from_recovery_timeline(
            store_slug=store_slug,
            session_id=session_id,
            status=status,
            cart_id=cart_id,
            recovery_key=recovery_key,
            timeline_event_id=timeline_event_id,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("product signal recovery hook skipped: %s", exc)


def product_signal_try_from_customer_return(payload: dict[str, Any]) -> None:
    try:
        from services.product_data.product_signal_collection_v1 import (
            collect_from_customer_return,
        )

        collect_from_customer_return(payload)
    except Exception as exc:  # noqa: BLE001
        log.debug("product signal return hook skipped: %s", exc)


__all__ = [
    "product_signal_try_from_cart_payload",
    "product_signal_try_from_hesitation",
    "product_signal_try_from_purchase",
    "product_signal_try_from_recovery_timeline",
    "product_signal_try_from_customer_return",
]
