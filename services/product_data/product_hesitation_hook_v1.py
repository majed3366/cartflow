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
        from services.product_data.product_signal_hook_v1 import (  # noqa: PLC0415
            product_signal_try_from_hesitation,
        )

        product_signal_try_from_hesitation(
            store_slug,
            session_id,
            cart_id=cart_id,
            recovery_key=recovery_key,
        )
        try:
            from services.evidence_truth.observation_shadow_dual_write_v1 import (  # noqa: PLC0415
                maybe_shadow_behaviour_observation_v1,
            )
            from services.evidence_truth.evidence_dual_write_v1 import (  # noqa: PLC0415
                maybe_publish_behaviour_evidence_v1,
            )

            _beh_payload = {
                "store_slug": store_slug,
                "session_id": session_id,
                "cart_id": cart_id or "",
                "recovery_key": recovery_key or "",
                "reason": str(reason),
                "sub_reason": (str(sub_reason) if sub_reason else ""),
                "event": "hesitation_reason_selected",
            }
            obs_shadow = maybe_shadow_behaviour_observation_v1(
                _beh_payload, source="product_hesitation_hook"
            )
            oid = ""
            if isinstance(obs_shadow, dict):
                oid = str(obs_shadow.get("observation_id") or "")
            maybe_publish_behaviour_evidence_v1(
                _beh_payload,
                source="product_hesitation_hook",
                observation_id=oid,
            )
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        log.debug("hesitation mapping hook skipped: %s", exc)


__all__ = ["product_data_try_hesitation_mapping"]
