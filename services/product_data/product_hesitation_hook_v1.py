# -*- coding: utf-8 -*-
"""
Thin non-blocking delegate for Hesitation Mapping v1.

Called from the reason-capture write path once a ``CartRecoveryReason`` has been
persisted. Maps the captured reason to the canonical products present in the
session. Never raises — widget, recovery, WhatsApp, VIP and Purchase Truth all
continue regardless of mapping outcome.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger("cartflow")


def product_data_try_hesitation_mapping(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    reason: Any = None,
    sub_reason: Any = None,
) -> None:
    """Persist Product ↔ Reason mappings for a captured hesitation. Never raises."""
    try:
        if not store_slug or not session_id or not reason:
            return
        from services.product_data.product_hesitation_mapping_v1 import (
            try_persist_hesitation_mappings,
        )

        try_persist_hesitation_mappings(
            store_slug,
            session_id,
            cart_id=cart_id,
            recovery_key=recovery_key,
            reason=str(reason),
            sub_reason=(str(sub_reason) if sub_reason else None),
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("hesitation mapping hook skipped: %s", exc)


__all__ = ["product_data_try_hesitation_mapping"]
