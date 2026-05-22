# -*- coding: utf-8 -*-
"""
Purchase Completion + Closed Lifecycle v1 — terminal closure after purchase.

Additive: logs, in-memory/session flags, optional cf_behavioral persistence.
Does not change WhatsApp send, RecoverySchedule rows, delays, or intent rules.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from services.reply_intent_handling import INTENT_PURCHASE

log = logging.getLogger("cartflow")

TERMINAL_STATE_CLOSED_PURCHASE = "closed_purchase"
DEFAULT_CLOSE_REASON = "purchase_detected"

_lock = threading.RLock()
_closed_keys: set[str] = set()


def reset_purchase_lifecycle_closure_for_tests() -> None:
    with _lock:
        _closed_keys.clear()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _emit_lines(lines: list[str]) -> None:
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def log_purchase_lifecycle_closed(
    *,
    recovery_key: str,
    session_id: str = "",
    cart_id: str = "",
    reason: str = DEFAULT_CLOSE_REASON,
    source: str = "",
) -> None:
    lines = [
        "[PURCHASE LIFECYCLE CLOSED]",
        f"session_id={(session_id or '-')[:80]}",
        f"cart_id={(cart_id or '-')[:64]}",
        f"recovery_key={(recovery_key or '-')[:120]}",
        f"reason={(reason or DEFAULT_CLOSE_REASON)[:64]}",
        f"terminal_state={TERMINAL_STATE_CLOSED_PURCHASE}",
        "future_recovery_allowed=false",
        "future_continuation_allowed=false",
    ]
    if source:
        lines.append(f"source={source[:64]}")
    _emit_lines(lines)


def log_purchase_lifecycle_already_closed(
    *,
    recovery_key: str,
    session_id: str = "",
    cart_id: str = "",
    source: str = "",
) -> None:
    lines = [
        "[PURCHASE LIFECYCLE ALREADY CLOSED]",
        f"session_id={(session_id or '-')[:80]}",
        f"cart_id={(cart_id or '-')[:64]}",
        f"recovery_key={(recovery_key or '-')[:120]}",
        f"terminal_state={TERMINAL_STATE_CLOSED_PURCHASE}",
        "future_recovery_allowed=false",
        "future_continuation_allowed=false",
    ]
    if source:
        lines.append(f"source={source[:64]}")
    _emit_lines(lines)


def log_purchase_lifecycle_closure_skipped(*, reason: str, session_id: str = "", cart_id: str = "") -> None:
    _emit_lines(
        [
            "[PURCHASE LIFECYCLE CLOSURE SKIPPED]",
            f"reason={(reason or 'unknown')[:64]}",
            f"session_id={(session_id or '-')[:80]}",
            f"cart_id={(cart_id or '-')[:64]}",
        ]
    )


def _lifecycle_already_closed_in_memory(recovery_key: str) -> bool:
    rk = (recovery_key or "").strip()
    if not rk:
        return False
    with _lock:
        if rk in _closed_keys:
            return True
    try:
        from main import _is_user_converted  # noqa: PLC0415

        return bool(_is_user_converted(rk))
    except Exception:  # noqa: BLE001
        return False


def log_recovery_blocked_lifecycle_closed(
    *,
    recovery_key: str,
    session_id: str = "",
    cart_id: str = "",
) -> None:
    _emit_lines(
        [
            "[RECOVERY BLOCKED]",
            f"reason=lifecycle_closed_purchase",
            f"session_id={(session_id or '-')[:80]}",
            f"cart_id={(cart_id or '-')[:64]}",
            f"recovery_key={(recovery_key or '-')[:120]}",
            f"terminal_state={TERMINAL_STATE_CLOSED_PURCHASE}",
        ]
    )


def _sync_main_session_terminal_flags(recovery_key: str) -> None:
    """Align with existing conversion / sent guards in main (no schedule mutation)."""
    rk = (recovery_key or "").strip()
    if not rk:
        return
    try:
        from main import (  # noqa: PLC0415
            _recovery_session_lock,
            _session_recovery_converted,
            _session_recovery_sent,
        )

        with _recovery_session_lock:
            _session_recovery_converted[rk] = True
            _session_recovery_sent[rk] = True
    except Exception:  # noqa: BLE001
        pass


def behavioral_patch_for_closed_purchase(
    *,
    reason: str = DEFAULT_CLOSE_REASON,
    source: str = "",
) -> dict[str, Any]:
    patch: dict[str, Any] = {
        "lifecycle_terminal_state": TERMINAL_STATE_CLOSED_PURCHASE,
        "lifecycle_closed_at": utc_now_iso(),
        "lifecycle_closed_reason": (reason or DEFAULT_CLOSE_REASON)[:64],
        "continuation_automation_stopped": True,
        "future_recovery_allowed": False,
        "future_continuation_allowed": False,
    }
    if source:
        patch["lifecycle_closed_source"] = source[:64]
    return patch


def is_purchase_lifecycle_closed(recovery_key: str) -> bool:
    return _lifecycle_already_closed_in_memory(recovery_key)


def is_continuation_allowed_after_purchase_close(recovery_key: str) -> bool:
    return not is_purchase_lifecycle_closed(recovery_key)


def _merge_closed_purchase_behavioral(ac: Any, *, reason: str, source: str) -> None:
    if ac is None:
        return
    try:
        from services.behavioral_recovery.state_store import merge_behavioral_state

        merge_behavioral_state(
            ac,
            **behavioral_patch_for_closed_purchase(reason=reason, source=source),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "purchase lifecycle behavioral merge skipped: %s",
            exc,
            exc_info=True,
        )


def record_purchase_lifecycle_closure(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: str = "",
    reason: str = DEFAULT_CLOSE_REASON,
    source: str = "purchase_detected",
    ac: Any = None,
    mark_converted: bool = True,
) -> None:
    """
    Close lifecycle terminally for purchase — idempotent with explicit stdout proof.
    """
    rk = (recovery_key or "").strip()
    if not rk:
        log_purchase_lifecycle_closure_skipped(
            reason="empty_recovery_key",
            session_id=session_id,
            cart_id=cart_id,
        )
        return

    with _lock:
        already = rk in _closed_keys
        _closed_keys.add(rk)

    if already:
        log_purchase_lifecycle_already_closed(
            recovery_key=rk,
            session_id=session_id,
            cart_id=cart_id,
            source=source,
        )
    else:
        log_purchase_lifecycle_closed(
            recovery_key=rk,
            session_id=session_id,
            cart_id=cart_id,
            reason=reason,
            source=source,
        )

    if mark_converted:
        _sync_main_session_terminal_flags(rk)
    _merge_closed_purchase_behavioral(ac, reason=reason, source=source)


def record_purchase_lifecycle_closure_from_reply_intent(
    result: dict[str, Any],
    *,
    recovery_key: str,
    session_id: str = "",
    cart_id: str = "",
    ac: Any = None,
) -> None:
    """After ``[REPLY INTENT]`` when intent=PURCHASE and action=close_lifecycle."""
    intent = (result.get("intent") or "").strip().upper()
    action = (result.get("action") or "").strip().lower()
    if intent != INTENT_PURCHASE or action != "close_lifecycle":
        return

    rk = (recovery_key or "").strip()
    if not rk and session_id:
        try:
            from main import _recovery_key_from_payload

            rk = _recovery_key_from_payload(
                {
                    "session_id": session_id,
                    "cart_id": cart_id,
                }
            )
        except Exception:  # noqa: BLE001
            rk = ""

    record_purchase_lifecycle_closure(
        rk,
        session_id=session_id,
        cart_id=cart_id,
        reason="purchase_detected",
        source="customer_reply_purchase",
        ac=ac,
    )


def block_recovery_if_purchase_lifecycle_closed(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: str = "",
) -> bool:
    """
    Returns True when recovery execution must not proceed (caller should return).
    """
    if not is_purchase_lifecycle_closed(recovery_key):
        return False
    log_recovery_blocked_lifecycle_closed(
        recovery_key=recovery_key,
        session_id=session_id,
        cart_id=cart_id,
    )
    return True


def record_purchase_lifecycle_closure_from_conversion(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: str = "",
    source: str = "conversion_event",
) -> None:
    record_purchase_lifecycle_closure(
        recovery_key,
        session_id=session_id,
        cart_id=cart_id,
        reason="purchase_detected",
        source=source,
        mark_converted=True,
    )
