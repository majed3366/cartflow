# -*- coding: utf-8 -*-
"""Lifecycle state machine — no stage skips."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from services.business_findings_lifecycle_v1.types_v1 import (
    LIFECYCLE_ORDER_V1,
    LS_ARCHIVED,
    LS_DETECTED,
    LS_RESOLVED,
)


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def lifecycle_index(state: str) -> int:
    try:
        return LIFECYCLE_ORDER_V1.index(str(state or ""))
    except ValueError:
        return -1


def can_advance(current: str, target: str) -> bool:
    """Allow advance only to the next stage (or terminal resolve/archive)."""
    cur = str(current or "")
    tgt = str(target or "")
    if cur == tgt:
        return True
    if tgt in {LS_RESOLVED, LS_ARCHIVED}:
        # May resolve/archive from any non-terminal state after detected.
        return lifecycle_index(cur) >= lifecycle_index(LS_DETECTED) and cur not in {
            LS_RESOLVED,
            LS_ARCHIVED,
        }
    ci = lifecycle_index(cur)
    ti = lifecycle_index(tgt)
    if ci < 0 or ti < 0:
        return False
    return ti == ci + 1


def append_lifecycle_event(
    events: list[dict[str, Any]],
    *,
    from_state: str,
    to_state: str,
    reason: str,
    at: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    out = list(events or [])
    out.append(
        {
            "from": from_state,
            "to": to_state,
            "reason": reason,
            "at": (at or _utc_naive_now()).isoformat(sep=" "),
        }
    )
    return out


def advance_state(
    row: dict[str, Any],
    target: str,
    *,
    reason: str,
) -> tuple[bool, str]:
    """
    Mutate row lifecycle_state + events if legal.
    Returns (ok, error_code).
    """
    current = str(row.get("lifecycle_state") or LS_DETECTED)
    if not can_advance(current, target):
        return False, f"illegal_transition:{current}->{target}"
    if current == target:
        return True, "noop"
    events = list(row.get("lifecycle_events") or [])
    row["lifecycle_events"] = append_lifecycle_event(
        events, from_state=current, to_state=target, reason=reason
    )
    row["lifecycle_state"] = target
    row["lifecycle_updated_at"] = _utc_naive_now().isoformat(sep=" ")
    return True, "advanced"


__all__ = [
    "lifecycle_index",
    "can_advance",
    "append_lifecycle_event",
    "advance_state",
]
