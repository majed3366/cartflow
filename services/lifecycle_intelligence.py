# -*- coding: utf-8 -*-
"""
Lifecycle Intelligence v1 — behavior → decision → action (decision only).

Pure layer over existing behavioral signals. Does not generate messages,
schedule delays, or send WhatsApp. Callers log outcomes and keep legacy
reason → delay → message paths unchanged.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

log = logging.getLogger("cartflow")

# Decision outcomes (single value per evaluation)
DECISION_STOP = "STOP"
DECISION_CONTINUE = "CONTINUE"
DECISION_WAIT = "WAIT"
DECISION_HANDOFF = "HANDOFF"
DECISION_FALLBACK = "FALLBACK"

BEHAVIOR_PURCHASE_COMPLETED = "purchase_completed"
BEHAVIOR_RETURNED_TO_SITE = "returned_to_site"
BEHAVIOR_CUSTOMER_REPLIED = "customer_replied"
BEHAVIOR_IGNORED = "ignored"
BEHAVIOR_DELAY_WAITING = "delay_waiting"
BEHAVIOR_UNKNOWN = "unknown"


class LifecycleDecisionResult(TypedDict):
    behavior: str
    decision: str
    reason: str
    action: str
    next_step: Optional[str]


def resolve_lifecycle_behavior(
    *,
    returned: bool = False,
    purchased: bool = False,
    replied: bool = False,
    ignored: bool = False,
    delay_pending: bool = False,
    log_precedence: bool = True,
) -> str:
    """Map boolean evidence to a single behavioral label (strict precedence).

    Precedence: purchase > reply > return > waiting > send (delay/ignored tails).
    """
    candidates = {
        "purchase": bool(purchased),
        "reply": bool(replied),
        "return": bool(returned),
        "ignored": bool(ignored),
        "waiting": bool(delay_pending),
    }
    if purchased:
        winner = BEHAVIOR_PURCHASE_COMPLETED
    elif replied:
        winner = BEHAVIOR_CUSTOMER_REPLIED
    elif returned:
        winner = BEHAVIOR_RETURNED_TO_SITE
    elif ignored:
        winner = BEHAVIOR_IGNORED
    elif delay_pending:
        winner = BEHAVIOR_DELAY_WAITING
    else:
        winner = BEHAVIOR_UNKNOWN
    if log_precedence and winner != BEHAVIOR_UNKNOWN:
        log_lifecycle_precedence(winner=winner, candidates=candidates)
    return winner


def log_lifecycle_precedence(
    *,
    winner: str,
    candidates: dict[str, bool],
) -> None:
    """Audit log: ``[LIFECYCLE PRECEDENCE]`` for support and cross-module alignment."""
    parts = [
        "[LIFECYCLE PRECEDENCE]",
        f"winner={(winner or '-')[:64]}",
        "candidates="
        + ",".join(f"{k}:{'true' if v else 'false'}" for k, v in sorted(candidates.items())),
    ]
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def decide_lifecycle_recovery(
    *,
    returned: bool = False,
    purchased: bool = False,
    replied: bool = False,
    ignored: bool = False,
    reason_tag: Optional[str] = None,
    attempt_count: int = 0,
    delay_pending: bool = False,
) -> LifecycleDecisionResult:
    """
    Convert behavioral evidence into one lifecycle decision.

    Precedence: purchase → reply → return → ignored → delay wait → fallback.
    No message text; no persistence side effects.
    """
    behavior = resolve_lifecycle_behavior(
        returned=returned,
        purchased=purchased,
        replied=replied,
        ignored=ignored,
        delay_pending=delay_pending,
    )
    try:
        attempt_n = max(0, int(attempt_count or 0))
    except (TypeError, ValueError):
        attempt_n = 0
    rt = (reason_tag or "").strip() or None

    if behavior == BEHAVIOR_PURCHASE_COMPLETED:
        return {
            "behavior": behavior,
            "decision": DECISION_STOP,
            "reason": "purchase_completed",
            "action": "close_lifecycle",
            "next_step": None,
        }
    if behavior == BEHAVIOR_RETURNED_TO_SITE:
        return {
            "behavior": behavior,
            "decision": DECISION_STOP,
            "reason": "user_returned",
            "action": "no_send",
            "next_step": None,
        }
    if behavior == BEHAVIOR_CUSTOMER_REPLIED:
        return {
            "behavior": behavior,
            "decision": DECISION_HANDOFF,
            "reason": "customer_replied",
            "action": "handoff_continuation",
            "next_step": None,
        }
    if behavior == BEHAVIOR_IGNORED:
        next_idx = max(1, attempt_n + 1)
        return {
            "behavior": behavior,
            "decision": DECISION_CONTINUE,
            "reason": "customer_ignored",
            "action": "proceed_recovery",
            "next_step": f"attempt_{next_idx}",
        }
    if behavior == BEHAVIOR_DELAY_WAITING:
        return {
            "behavior": behavior,
            "decision": DECISION_WAIT,
            "reason": "delay_not_elapsed",
            "action": "wait_schedule",
            "next_step": None,
        }
    # unknown — reason/delay path unchanged; decision layer defers
    reason = "no_behavior_signal"
    if rt:
        reason = f"reason_tag:{rt}"
    return {
        "behavior": BEHAVIOR_UNKNOWN,
        "decision": DECISION_FALLBACK,
        "reason": reason,
        "action": "reason_then_delay",
        "next_step": None,
    }


def log_lifecycle_decision(
    result: LifecycleDecisionResult,
    *,
    session_id: str = "",
    recovery_key: str = "",
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Emit [LIFECYCLE DECISION] and [LIFECYCLE ACTION] lines for operational proof."""
    lines = [
        "[LIFECYCLE DECISION]",
        f"behavior={result.get('behavior', '')}",
        f"decision={result.get('decision', '')}",
        f"reason={result.get('reason', '')}",
    ]
    if result.get("next_step"):
        lines.append(f"next_step={result['next_step']}")
    sid = (session_id or "").strip()
    if sid:
        lines.append(f"session_id={sid[:80]}")
    rk = (recovery_key or "").strip()
    if rk:
        lines.append(f"recovery_key={rk[:120]}")
    if extra:
        for k, v in extra.items():
            if v is not None and str(v).strip() != "":
                lines.append(f"{k}={v}")
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass

    action_line = (
        f"[LIFECYCLE ACTION] action={result.get('action', '')} "
        f"decision={result.get('decision', '')} behavior={result.get('behavior', '')}"
    )
    try:
        print(action_line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", action_line)
    except Exception:  # noqa: BLE001
        pass
