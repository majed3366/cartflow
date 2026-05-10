# -*- coding: utf-8 -*-
"""
Centralized merchant lifecycle precedence (behavior over scheduling).

Single source of truth for which *behavioral* tier wins when logs, phase,
blockers, and dashboard signals disagree. Scheduling tails (queued, duplicate,
automation) must never outrank stronger customer truth.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower()


def recovery_log_statuses_lower(statuses: Optional[Iterable[str]]) -> frozenset[str]:
    out: set[str] = set()
    for raw in statuses or ():
        t = _norm(raw)
        if t:
            out.add(t)
    return frozenset(out)


def lifecycle_purchased_evidence(
    *,
    ls: str,
    bk: str,
    pk: str,
    cr: str,
    log_ss: frozenset[str],
) -> bool:
    return bool(
        ls == "stopped_converted"
        or bk == "purchase_completed"
        or pk in ("stopped_purchase", "recovery_complete")
        or cr == "converted"
        or "stopped_converted" in log_ss
    )


def lifecycle_replied_evidence(
    *,
    bh: dict[str, Any],
    ls: str,
    bk: str,
    pk: str,
    log_ss: frozenset[str],
) -> bool:
    return bool(
        bh.get("customer_replied") is True
        or pk == "behavioral_replied"
        or bk == "customer_replied"
        or ls in ("skipped_followup_customer_replied", "skipped_user_rejected_help")
        or "skipped_followup_customer_replied" in log_ss
        or "skipped_user_rejected_help" in log_ss
    )


def lifecycle_returned_evidence(
    *,
    bh: dict[str, Any],
    ls: str,
    bk: str,
    pk: str,
    cr: str,
    log_ss: frozenset[str],
    dashboard_return_track: bool,
    dashboard_return_intel_panel: bool,
) -> bool:
    return bool(
        bh.get("user_returned_to_site") is True
        or bh.get("customer_returned_to_site") is True
        or pk == "customer_returned"
        or cr == "returned"
        or ls == "skipped_anti_spam"
        or bk == "user_returned"
        or "skipped_anti_spam" in log_ss
        or dashboard_return_track
        or dashboard_return_intel_panel
    )


def lifecycle_delay_scheduling_only(
    *,
    ls: str,
    pk: str,
    purchased: bool,
    replied: bool,
    returned: bool,
) -> bool:
    """True only when delay/schedule story is allowed (no stronger behavioral tier)."""
    if purchased or replied or returned:
        return False
    return bool(ls in ("queued", "skipped_delay_gate") or pk == "pending_second_attempt")
