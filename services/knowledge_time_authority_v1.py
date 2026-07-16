# -*- coding: utf-8 -*-
"""
Knowledge Layer ↔ Time Authority bridge (INV-001 WP-4).

Single path for Knowledge merchant temporal windows. No wall-clock window math
in Knowledge collectors. No DB/network I/O.

Interval: half-open ``[start, end)`` in UTC; DB predicates use naive UTC
(legacy column storage) derived from Time Authority aware bounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional

from services.time_authority import (
    EmptinessType,
    QueryTimeContextKind,
    WindowRecipeId,
    WindowResultStatus,
    ensure_utc,
    resolve_effective_context,
    window_for,
)
from services.time_authority.emptiness import EmptinessResult, classify_store_history
from services.time_authority.filtering import TimeWindow
from services.time_authority.query_context import (
    QueryTimeContext,
    build_query_time_context,
)


def _naive_utc(dt: datetime) -> datetime:
    """Strip tz for SQLAlchemy DateTime columns stored as naive UTC."""
    u = ensure_utc(dt)
    return u.replace(tzinfo=None)


def resolve_knowledge_query_context(
    *,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> QueryTimeContext:
    """
    Bind Knowledge reads to Query Time Context.

    - Explicit ``context`` wins.
    - Explicit ``now`` builds a TESTING context at that as-of (test/compat inject).
    - Otherwise ambient ``resolve_effective_context()`` (production middleware / SystemClock).
    """
    if context is not None:
        return context
    if now is not None:
        ctx, _prov = build_query_time_context(
            QueryTimeContextKind.TESTING,
            as_of=ensure_utc(now),
            label="knowledge_now_inject",
        )
        return ctx
    return resolve_effective_context()


@dataclass(frozen=True)
class KnowledgeTimeWindow:
    """Governed Knowledge primary + comparison windows (DB-ready naive bounds)."""

    window_days: int
    start: datetime
    end: datetime
    prev_start: datetime
    primary: TimeWindow
    comparison: TimeWindow
    context: QueryTimeContext
    temporal_status: WindowResultStatus
    detail: str = ""

    @property
    def ok(self) -> bool:
        return (
            self.temporal_status == WindowResultStatus.VALID_WINDOW
            and self.primary.ok
            and self.comparison.ok
        )

    @property
    def authoritative_now(self) -> datetime:
        return ensure_utc(self.context.authoritative_now)

    def internal_provenance(self) -> dict[str, Any]:
        """Internal platform evidence — not for merchant UI."""
        return {
            "merchant_visible": False,
            "window_days": self.window_days,
            "temporal_status": self.temporal_status.value,
            "detail": self.detail or None,
            "primary": self.primary.provenance(),
            "comparison": self.comparison.provenance(),
            "context_mode": self.context.mode.value,
            "authority_provenance": self.context.time_provenance.value,
            "authoritative_now": self.authoritative_now.isoformat(),
            "simulation_run_id": self.context.simulation_run_id or None,
            "replay_id": self.context.replay_id or None,
            "correlation_id": self.context.correlation_id or None,
            "db_bounds_naive_utc": {
                "start": self.start.isoformat(),
                "end": self.end.isoformat(),
                "prev_start": self.prev_start.isoformat(),
            },
        }


def resolve_knowledge_windows(
    *,
    window_days: int = 7,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> KnowledgeTimeWindow:
    """
    Derive Knowledge rolling window + comparison period via WP-3 recipes.

    Recipe: ``last_n_days`` + ``comparison_period``.
    ``window_days`` floored to ≥1 (preserves legacy ``max(1, int(...))``).
    """
    n = max(1, int(window_days))
    ctx = resolve_knowledge_query_context(now=now, context=context)
    primary = window_for(WindowRecipeId.LAST_N_DAYS, context=ctx, n_days=n)
    if not primary.ok:
        z = _naive_utc(ctx.authoritative_now)
        return KnowledgeTimeWindow(
            window_days=n,
            start=z,
            end=z,
            prev_start=z,
            primary=primary,
            comparison=primary,
            context=ctx,
            temporal_status=primary.status,
            detail=primary.detail,
        )
    comparison = window_for(
        WindowRecipeId.COMPARISON_PERIOD,
        context=ctx,
        primary=primary,
    )
    if not comparison.ok:
        return KnowledgeTimeWindow(
            window_days=n,
            start=_naive_utc(primary.start_at),
            end=_naive_utc(primary.end_at),
            prev_start=_naive_utc(primary.start_at),
            primary=primary,
            comparison=comparison,
            context=ctx,
            temporal_status=comparison.status,
            detail=comparison.detail,
        )
    return KnowledgeTimeWindow(
        window_days=n,
        start=_naive_utc(primary.start_at),
        end=_naive_utc(primary.end_at),
        prev_start=_naive_utc(comparison.start_at),
        primary=primary,
        comparison=comparison,
        context=ctx,
        temporal_status=WindowResultStatus.VALID_WINDOW,
    )


def knowledge_stamp_now(
    *,
    now: Optional[datetime] = None,
    context: Optional[QueryTimeContext] = None,
) -> datetime:
    """UTC stamp for generated_at — same authority as window construction."""
    return ensure_utc(
        resolve_knowledge_query_context(now=now, context=context).authoritative_now
    )


def classify_knowledge_temporal_emptiness(
    *,
    time_window: KnowledgeTimeWindow,
    has_any_history: bool,
    has_in_window: bool,
    sample_count: Optional[int] = None,
    min_sample: Optional[int] = None,
) -> EmptinessResult:
    """Typed temporal emptiness without extra I/O (uses caller-known flags)."""
    if not time_window.ok:
        mapping = {
            WindowResultStatus.INVALID_RANGE: EmptinessType.METRIC_UNSUPPORTED,
            WindowResultStatus.UNSUPPORTED_TIMEZONE_POLICY: EmptinessType.METRIC_UNSUPPORTED,
            WindowResultStatus.MISSING_QUERY_TIME_CONTEXT: EmptinessType.METRIC_UNSUPPORTED,
            WindowResultStatus.INVALID_ARGUMENT: EmptinessType.METRIC_UNSUPPORTED,
            WindowResultStatus.INSUFFICIENT_HISTORY: EmptinessType.INSUFFICIENT_HISTORY,
        }
        et = mapping.get(time_window.temporal_status, EmptinessType.METRIC_UNSUPPORTED)
        return EmptinessResult(
            emptiness_type=et,
            status=time_window.temporal_status,
            window=time_window.primary,
            detail=time_window.detail,
        )
    return classify_store_history(
        window=time_window.primary,
        has_any_history=has_any_history,
        has_in_window=has_in_window,
        sample_count=sample_count,
        min_sample=min_sample,
    )


def knowledge_time_contract_meta() -> Mapping[str, Any]:
    return {
        "consumer": "knowledge",
        "recipe_primary": WindowRecipeId.LAST_N_DAYS.value,
        "recipe_comparison": WindowRecipeId.COMPARISON_PERIOD.value,
        "interval_shape": "[start_at, end_at)",
        "timezone_policy": "utc",
        "db_bound_representation": "naive_utc",
        "io": "none",
    }


__all__ = [
    "KnowledgeTimeWindow",
    "classify_knowledge_temporal_emptiness",
    "knowledge_stamp_now",
    "knowledge_time_contract_meta",
    "resolve_knowledge_query_context",
    "resolve_knowledge_windows",
]
