# -*- coding: utf-8 -*-
"""
Purchase Truth v1 — close lifecycle from purchase evidence (not customer reply text).

Additive layer on ``purchase_lifecycle_closure``; does not change WhatsApp, delays,
schedules, reply intent, or continuation rules.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger("cartflow")

# Strong purchase-evidence signals (verified=true).
_TRUTH_FLAG_KEYS: tuple[tuple[str, str], ...] = (
    ("purchase_completed", "purchase_completed"),
    ("order_paid", "order_paid"),
    ("checkout_completed", "checkout_completed"),
    ("order_created", "order_created"),
)

_TRUTH_EVENT_NAMES: frozenset[str] = frozenset(
    {
        "purchase_completed",
        "order_paid",
        "checkout_completed",
        "order_created",
        "purchase_event",
        "user_converted",
    }
)


def extract_purchase_truth_evidence(payload: dict[str, Any]) -> Optional[tuple[str, str]]:
    """
    Return ``(source, evidence_detail)`` when payload carries purchase truth.

    Supports platform-style events (future) and manual/dev flags for testing.
    """
    if not isinstance(payload, dict):
        return None

    for key, source in _TRUTH_FLAG_KEYS:
        if payload.get(key) is True:
            return source, f"{key}=true"

    ev_raw = payload.get("event") or payload.get("purchase_event")
    ev = str(ev_raw or "").strip().lower()
    if ev in _TRUTH_EVENT_NAMES:
        return ev, f"event={ev}"

    if payload.get("user_converted") is True:
        return "user_converted", "user_converted=true"

    return None


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
    Verify purchase evidence, mark session converted, close lifecycle.

    Returns ``recovery_key`` when evidence was applied; ``None`` if no evidence.
    """
    extracted = extract_purchase_truth_evidence(payload)
    if not extracted:
        return None

    source, evidence = extracted
    try:
        from main import (  # noqa: PLC0415
            _cart_id_str_from_payload,
            _recovery_key_from_payload,
            _recovery_session_lock,
            _session_part_from_payload,
            _session_recovery_converted,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("purchase truth: main import failed: %s", exc)
        return None

    key = _recovery_key_from_payload(payload)
    if not key:
        return None

    with _recovery_session_lock:
        _session_recovery_converted[key] = True

    apply_purchase_truth_lifecycle_closure(
        key,
        session_id=_session_part_from_payload(payload),
        cart_id=(_cart_id_str_from_payload(payload) or "") or "",
        source=source,
        evidence=evidence,
        context_payload=payload,
    )
    log.info("purchase truth ingested recovery_key=%s source=%s", key, source)
    return key
