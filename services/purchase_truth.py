# -*- coding: utf-8 -*-
"""
Purchase Truth v1 — evidence-based lifecycle closure (facade).

Durable foundation: ``services.cartflow_purchase_truth``.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from services.cartflow_purchase_truth import (
    extract_purchase_evidence as extract_purchase_truth_evidence,
    record_purchase_from_payload,
)

log = logging.getLogger("cartflow")


def log_purchase_truth(
    *,
    source: str,
    recovery_key: str,
    session_id: str = "",
    cart_id: str = "",
    evidence: str = "",
    verified: bool = True,
) -> None:
    lines = [
        "[PURCHASE TRUTH]",
        f"source={(source or 'unknown')[:64]}",
        f"verified={'true' if verified else 'false'}",
        f"session_id={(session_id or '-')[:80]}",
        f"cart_id={(cart_id or '-')[:64]}",
        f"recovery_key={(recovery_key or '-')[:120]}",
    ]
    if evidence:
        lines.append(f"evidence={evidence[:120]}")
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def apply_purchase_truth_lifecycle_closure(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: str = "",
    source: str,
    evidence: str = "",
    ac: Any = None,
    context_payload: Optional[dict[str, Any]] = None,
) -> None:
    """Emit ``[PURCHASE TRUTH]`` then terminal ``[PURCHASE LIFECYCLE CLOSED]``."""
    from services.purchase_lifecycle_closure import record_purchase_lifecycle_closure

    rk = (recovery_key or "").strip()
    if not rk:
        return

    log_purchase_truth(
        source=source,
        recovery_key=rk,
        session_id=session_id,
        cart_id=cart_id,
        evidence=evidence,
        verified=True,
    )
    record_purchase_lifecycle_closure(
        rk,
        session_id=session_id,
        cart_id=cart_id,
        reason="purchase_truth_verified",
        source=f"purchase_truth:{source}",
        ac=ac,
        mark_converted=True,
    )
    try:
        from services.purchase_attribution_v1 import run_purchase_attribution_after_truth_closure

        run_purchase_attribution_after_truth_closure(
            rk,
            session_id=session_id,
            cart_id=cart_id,
            ac=ac,
            context_payload=context_payload,
            purchase_truth_source=source,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "purchase attribution hook failed (closure complete): %s",
            exc,
            exc_info=True,
        )


def ingest_purchase_truth_payload(payload: dict[str, Any]) -> Optional[str]:
    """
    Verify purchase evidence, persist durable truth, stop recovery.

    Returns ``recovery_key`` when evidence was applied; ``None`` if no evidence.
    """
    key = record_purchase_from_payload(payload)
    if key:
        log.info("purchase truth ingested recovery_key=%s", key)
    return key
