# -*- coding: utf-8 -*-
"""
Governed Time Filtering Contract (WP-3).

Canonical temporal windows derived only from Query Time Context /
Platform Time Authority. Interval shape: half-open ``[start_at, end_at)`` UTC.

Performance contract:
- Pure / near-pure, constant-time
- No database or network I/O
- Deterministic for the same context + inputs
- Index-friendly bounds (``ts >= start_at AND ts < end_at``)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from services.time_authority.contracts import (
    QueryTimeContextKind,
    TimezonePolicy,
    WindowRecipeId,
    WindowResultStatus,
    ensure_utc,
    resolve_window_recipe,
)
from services.time_authority.exceptions import FilteringError
from services.time_authority.query_context import (
    QueryTimeContext,
    get_query_time_context,
    resolve_effective_context,
)

# Stable interval convention (documented contract).
INTERVAL_SHAPE = "[start_at, end_at)"
START_INCLUSIVE = True
END_EXCLUSIVE = True


@dataclass(frozen=True)
class TimeWindow:
    """Immutable temporal window with internal provenance."""

    recipe: WindowRecipeId
    start_at: datetime
    end_at: datetime
    status: WindowResultStatus
    authoritative_now: datetime
    timezone_policy: TimezonePolicy
    context_mode: QueryTimeContextKind
    authority_provenance: str
    correlation_id: str = ""
    simulation_run_id: str = ""
    replay_id: str = ""
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == WindowResultStatus.VALID_WINDOW

    def contains(self, event_at: datetime) -> bool:
        """True if ``start_at <= event_at < end_at`` (UTC-normalized)."""
        if not self.ok:
            return False
        t = ensure_utc(event_at)
        return self.start_at <= t < self.end_at

    def as_sql_bounds(self) -> tuple[datetime, datetime]:
        """Index-friendly ``(start_at, end_at)`` for ``>= start AND < end``."""
        if not self.ok:
            raise FilteringError(f"window_not_valid:{self.status.value}")
        return self.start_at, self.end_at

    def provenance(self) -> dict[str, Any]:
        return {
            "interval_shape": INTERVAL_SHAPE,
            "recipe": self.recipe.value,
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat(),
            "status": self.status.value,
            "authoritative_now": self.authoritative_now.isoformat(),
            "timezone_policy": self.timezone_policy.value,
            "context_mode": self.context_mode.value,
            "authority_provenance": self.authority_provenance,
            "correlation_id": self.correlation_id or None,
            "simulation_run_id": self.simulation_run_id or None,
            "replay_id": self.replay_id or None,
            "detail": self.detail or None,
            "merchant_visible": False,
        }


def _utc_midnight(dt: datetime) -> datetime:
    d = ensure_utc(dt)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def _month_start(dt: datetime) -> datetime:
    d = ensure_utc(dt)
    return datetime(d.year, d.month, 1, tzinfo=timezone.utc)


def _next_month_start(dt: datetime) -> datetime:
    y, m = _add_months(ensure_utc(dt).year, ensure_utc(dt).month, 1)
    return datetime(y, m, 1, tzinfo=timezone.utc)


def _iso_week_start(dt: datetime) -> datetime:
    """Monday 00:00 UTC of the ISO week containing dt."""
    d = _utc_midnight(dt)
    # Monday = 0
    return d - timedelta(days=d.weekday())


def _fail(
    recipe: WindowRecipeId,
    status: WindowResultStatus,
    ctx: QueryTimeContext,
    *,
    detail: str = "",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> TimeWindow:
    now = ensure_utc(ctx.authoritative_now)
    z = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return TimeWindow(
        recipe=recipe,
        start_at=start or z,
        end_at=end or z,
        status=status,
        authoritative_now=now,
        timezone_policy=ctx.timezone_policy,
        context_mode=ctx.mode,
        authority_provenance=ctx.time_provenance.value,
        correlation_id=ctx.correlation_id,
        simulation_run_id=ctx.simulation_run_id,
        replay_id=ctx.replay_id,
        detail=detail,
    )


def _ok(
    recipe: WindowRecipeId,
    start: datetime,
    end: datetime,
    ctx: QueryTimeContext,
) -> TimeWindow:
    start_u = ensure_utc(start)
    end_u = ensure_utc(end)
    if start_u >= end_u:
        return _fail(
            recipe,
            WindowResultStatus.INVALID_RANGE,
            ctx,
            detail="start_at_not_before_end_at",
            start=start_u,
            end=end_u,
        )
    return TimeWindow(
        recipe=recipe,
        start_at=start_u,
        end_at=end_u,
        status=WindowResultStatus.VALID_WINDOW,
        authoritative_now=ensure_utc(ctx.authoritative_now),
        timezone_policy=ctx.timezone_policy,
        context_mode=ctx.mode,
        authority_provenance=ctx.time_provenance.value,
        correlation_id=ctx.correlation_id,
        simulation_run_id=ctx.simulation_run_id,
        replay_id=ctx.replay_id,
    )


def _require_utc_policy(ctx: QueryTimeContext, recipe: WindowRecipeId) -> Optional[TimeWindow]:
    if ctx.timezone_policy != TimezonePolicy.UTC:
        return _fail(
            recipe,
            WindowResultStatus.UNSUPPORTED_TIMEZONE_POLICY,
            ctx,
            detail=f"policy={ctx.timezone_policy.value}",
        )
    return None


def window_for(
    recipe: object,
    *,
    context: Optional[QueryTimeContext] = None,
    n_days: Optional[int] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    primary: Optional[TimeWindow] = None,
    require_explicit_context: bool = False,
) -> TimeWindow:
    """
    Derive a governed temporal window.

    Relative recipes use ``context.authoritative_now`` (or ambient production
    via ``resolve_effective_context``). Never calls wall clock directly.
    """
    try:
        rid = resolve_window_recipe(recipe)
    except ValueError as exc:
        # Need a context shell for provenance — use effective if possible
        ctx = context or resolve_effective_context()
        return _fail(
            WindowRecipeId.EXPLICIT_RANGE,
            WindowResultStatus.INVALID_ARGUMENT,
            ctx,
            detail=str(exc),
        )

    if require_explicit_context and get_query_time_context() is None and context is None:
        # Synthetic minimal context for error provenance only
        from services.time_authority.query_context import build_default_production_context

        shell = build_default_production_context()
        return _fail(
            rid,
            WindowResultStatus.MISSING_QUERY_TIME_CONTEXT,
            shell,
            detail="explicit_query_time_context_required",
        )

    ctx = context or resolve_effective_context()
    policy_fail = _require_utc_policy(ctx, rid)
    if policy_fail is not None:
        return policy_fail

    now = ensure_utc(ctx.authoritative_now)

    if rid == WindowRecipeId.TODAY:
        start = _utc_midnight(now)
        return _ok(rid, start, start + timedelta(days=1), ctx)

    if rid == WindowRecipeId.YESTERDAY:
        start = _utc_midnight(now) - timedelta(days=1)
        return _ok(rid, start, start + timedelta(days=1), ctx)

    if rid == WindowRecipeId.LAST_N_DAYS:
        if n_days is None or int(n_days) < 1:
            return _fail(
                rid,
                WindowResultStatus.INVALID_ARGUMENT,
                ctx,
                detail="n_days_must_be_positive_int",
            )
        n = int(n_days)
        # Rolling window ending at authoritative_now (exclusive)
        return _ok(rid, now - timedelta(days=n), now, ctx)

    if rid == WindowRecipeId.CURRENT_WEEK:
        start = _iso_week_start(now)
        return _ok(rid, start, start + timedelta(days=7), ctx)

    if rid == WindowRecipeId.PREVIOUS_WEEK:
        start = _iso_week_start(now) - timedelta(days=7)
        return _ok(rid, start, start + timedelta(days=7), ctx)

    if rid == WindowRecipeId.CURRENT_MONTH:
        start = _month_start(now)
        return _ok(rid, start, _next_month_start(now), ctx)

    if rid == WindowRecipeId.PREVIOUS_MONTH:
        cur = _month_start(now)
        y, m = _add_months(cur.year, cur.month, -1)
        start = datetime(y, m, 1, tzinfo=timezone.utc)
        return _ok(rid, start, cur, ctx)

    if rid == WindowRecipeId.EXPLICIT_RANGE:
        if start_at is None or end_at is None:
            return _fail(
                rid,
                WindowResultStatus.INVALID_ARGUMENT,
                ctx,
                detail="explicit_range_requires_start_at_and_end_at",
            )
        return _ok(rid, ensure_utc(start_at), ensure_utc(end_at), ctx)

    if rid == WindowRecipeId.COMPARISON_PERIOD:
        if primary is None or not primary.ok:
            return _fail(
                rid,
                WindowResultStatus.INVALID_ARGUMENT,
                ctx,
                detail="comparison_period_requires_valid_primary_window",
            )
        duration = primary.end_at - primary.start_at
        end = primary.start_at
        start = end - duration
        return _ok(rid, start, end, ctx)

    if rid in (
        WindowRecipeId.SIMULATION_RANGE,
        WindowRecipeId.HISTORICAL_REPLAY_RANGE,
        WindowRecipeId.RECOVERY_REPLAY_RANGE,
    ):
        required = {
            WindowRecipeId.SIMULATION_RANGE: QueryTimeContextKind.SIMULATION,
            WindowRecipeId.HISTORICAL_REPLAY_RANGE: QueryTimeContextKind.HISTORICAL_REPLAY,
            WindowRecipeId.RECOVERY_REPLAY_RANGE: QueryTimeContextKind.RECOVERY_REPLAY,
        }[rid]
        if ctx.mode != required:
            return _fail(
                rid,
                WindowResultStatus.INVALID_ARGUMENT,
                ctx,
                detail=f"{rid.value}_requires_{required.value}_context",
            )
        if n_days is not None:
            if int(n_days) < 1:
                return _fail(
                    rid,
                    WindowResultStatus.INVALID_ARGUMENT,
                    ctx,
                    detail="n_days_must_be_positive_int",
                )
            n = int(n_days)
            return _ok(rid, now - timedelta(days=n), now, ctx)
        # Default: calendar day containing authoritative_now (UTC)
        start = _utc_midnight(now)
        return _ok(rid, start, start + timedelta(days=1), ctx)

    return _fail(
        rid,
        WindowResultStatus.INVALID_ARGUMENT,
        ctx,
        detail=f"unsupported_recipe:{rid.value}",
    )


def windows_adjacent_non_overlapping(left: TimeWindow, right: TimeWindow) -> bool:
    """True if left.end_at == right.start_at (touching, no overlap)."""
    if not (left.ok and right.ok):
        return False
    return left.end_at == right.start_at


def filter_contract_meta() -> Mapping[str, Any]:
    """Static contract description for docs / ops."""
    return {
        "interval_shape": INTERVAL_SHAPE,
        "start_inclusive": START_INCLUSIVE,
        "end_exclusive": END_EXCLUSIVE,
        "timezone_policy": TimezonePolicy.UTC.value,
        "io": "none",
        "hot_path_safe": True,
    }
