# -*- coding: utf-8 -*-
"""
Daily Brief ↔ Time Authority bridge (INV-001 WP-6).

Brief does not own window recipes. Rolling windows are identical to Knowledge
and Dashboard via ``resolve_knowledge_windows``. ``brief_date`` and stamps
derive from Query Time Context authoritative now (UTC calendar date).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from services.dashboard_kpi_time_v1 import resolve_dashboard_rolling_windows
from services.knowledge_time_authority_v1 import (
    KnowledgeTimeWindow,
    knowledge_stamp_now,
    resolve_knowledge_windows,
)
from services.time_authority.query_context import QueryTimeContext

BRIEF_DEFAULT_WINDOW_DAYS = 7


def resolve_brief_windows(
    *,
    window_days: int = BRIEF_DEFAULT_WINDOW_DAYS,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> KnowledgeTimeWindow:
    """Same rolling + comparison windows as Knowledge / Dashboard."""
    return resolve_knowledge_windows(
        window_days=window_days, now=now, context=context
    )


def brief_date_iso(
    *,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> str:
    """UTC calendar date of authoritative_now (YYYY-MM-DD)."""
    return knowledge_stamp_now(now=now, context=context).date().isoformat()


def brief_stamp_now(
    *,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> datetime:
    """Report generation timestamp from Time Authority."""
    return knowledge_stamp_now(now=now, context=context)


def brief_time_observability(
    tw: KnowledgeTimeWindow,
) -> dict[str, Any]:
    """Internal temporal provenance for brief observability (not merchant UI)."""
    return {
        "merchant_visible": False,
        "window_days": tw.window_days,
        "start": tw.start.isoformat(),
        "end": tw.end.isoformat(),
        "prev_start": tw.prev_start.isoformat(),
        "context_mode": tw.context.mode.value,
        "authoritative_now": tw.authoritative_now.isoformat(),
        "simulation_run_id": tw.context.simulation_run_id or None,
        "replay_id": tw.context.replay_id or None,
        "cross_surface": {
            "knowledge": "resolve_knowledge_windows",
            "dashboard": "resolve_dashboard_rolling_windows",
            "brief": "resolve_brief_windows",
        },
    }


def assert_brief_dashboard_knowledge_windows_equal(
    *,
    window_days: int = BRIEF_DEFAULT_WINDOW_DAYS,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> Mapping[str, Any]:
    """Cross-surface equality helper (tests / Gate checks)."""
    kl = resolve_knowledge_windows(
        window_days=window_days, now=now, context=context
    )
    dash = resolve_dashboard_rolling_windows(
        window_days=window_days, now=now, context=context
    )
    brief = resolve_brief_windows(
        window_days=window_days, now=now, context=context
    )
    equal = (kl.start, kl.end, kl.prev_start) == (
        dash.start,
        dash.end,
        dash.prev_start,
    ) and (kl.start, kl.end, kl.prev_start) == (
        brief.start,
        brief.end,
        brief.prev_start,
    )
    return {
        "equal": equal,
        "knowledge": (kl.start, kl.end, kl.prev_start),
        "dashboard": (dash.start, dash.end, dash.prev_start),
        "brief": (brief.start, brief.end, brief.prev_start),
    }


__all__ = [
    "BRIEF_DEFAULT_WINDOW_DAYS",
    "assert_brief_dashboard_knowledge_windows_equal",
    "brief_date_iso",
    "brief_stamp_now",
    "brief_time_observability",
    "resolve_brief_windows",
]
