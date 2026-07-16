# -*- coding: utf-8 -*-
"""
Time Authority contracts — stable types and protocols (WP-1 / WP-2 / WP-3).

Consumers depend on these interfaces, not on provider internals.
Window recipes and emptiness enums are owned here; derivation lives in filtering.py.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional, Protocol, runtime_checkable
from datetime import datetime


@runtime_checkable
class ClockProvider(Protocol):
    """Supplies authoritative UTC 'now' for a bound Time Authority source."""

    @property
    def source_id(self) -> str:
        """Stable identifier for provenance (e.g. system, fixed, frozen, simulation)."""
        ...

    def now(self) -> datetime:
        """Return timezone-aware UTC datetime."""
        ...


class ClockSourceKind(str, Enum):
    """Identity of the active clock source."""

    SYSTEM = "system"
    FIXED_AS_OF = "fixed_as_of"
    FROZEN_TEST = "frozen_test"
    SIMULATION = "simulation"


class QueryTimeContextKind(str, Enum):
    """Kinds from Time Authority Architecture V2 §5 (canonical vocabulary)."""

    CURRENT_PRODUCTION = "current_production"
    HISTORICAL_REPLAY = "historical_replay"
    SIMULATION = "simulation"
    TESTING = "testing"
    FUTURE_REPLAY = "future_replay"
    RECOVERY_REPLAY = "recovery_replay"


# Aliases accepted at boundaries (map to QueryTimeContextKind). No duplicate modes.
_KIND_ALIASES: dict[str, QueryTimeContextKind] = {
    "production": QueryTimeContextKind.CURRENT_PRODUCTION,
    "current_production": QueryTimeContextKind.CURRENT_PRODUCTION,
    "simulation": QueryTimeContextKind.SIMULATION,
    "historical_replay": QueryTimeContextKind.HISTORICAL_REPLAY,
    "recovery_replay": QueryTimeContextKind.RECOVERY_REPLAY,
    "test": QueryTimeContextKind.TESTING,
    "testing": QueryTimeContextKind.TESTING,
    "future_replay": QueryTimeContextKind.FUTURE_REPLAY,
}


def resolve_context_kind(value: object) -> QueryTimeContextKind:
    """Resolve canonical kind or approved alias; reject unknown modes."""
    if isinstance(value, QueryTimeContextKind):
        return value
    key = str(value or "").strip().lower()
    if key in _KIND_ALIASES:
        return _KIND_ALIASES[key]
    raise ValueError(f"invalid_context_kind:{value}")


class TimeProvenance(str, Enum):
    """Internal provenance labels (not merchant-facing)."""

    SYSTEM_CLOCK = "system_clock"
    SIMULATION_CLOCK = "simulation_clock"
    HISTORICAL_REPLAY = "historical_replay"
    RECOVERY_REPLAY = "recovery_replay"
    FUTURE_REPLAY = "future_replay"
    TEST_CLOCK = "test_clock"


def provenance_for_kind(kind: QueryTimeContextKind) -> TimeProvenance:
    return {
        QueryTimeContextKind.CURRENT_PRODUCTION: TimeProvenance.SYSTEM_CLOCK,
        QueryTimeContextKind.SIMULATION: TimeProvenance.SIMULATION_CLOCK,
        QueryTimeContextKind.HISTORICAL_REPLAY: TimeProvenance.HISTORICAL_REPLAY,
        QueryTimeContextKind.RECOVERY_REPLAY: TimeProvenance.RECOVERY_REPLAY,
        QueryTimeContextKind.FUTURE_REPLAY: TimeProvenance.FUTURE_REPLAY,
        QueryTimeContextKind.TESTING: TimeProvenance.TEST_CLOCK,
    }[kind]


class TimezonePolicy(str, Enum):
    """
    Timezone policy for window recipes (WP-3).

    Approved V2 policy: UTC-only for persisted/query boundaries.
    Store-local behaviour remains parked (Architecture Q1) — reserved member
    is rejected by filtering with ``unsupported_timezone_policy``.
    """

    UTC = "utc"
    # Hook only — not implemented. Do not invent store-TZ math.
    STORE_LOCAL_RESERVED = "store_local_reserved"


class WindowRecipeId(str, Enum):
    """
    Canonical window recipes (WP-3).

    Interval shape for all recipes: half-open ``[start_at, end_at)`` in UTC
    (start inclusive, end exclusive). Adjacent windows share a boundary without overlap.
    """

    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_N_DAYS = "last_n_days"
    CURRENT_WEEK = "current_week"
    PREVIOUS_WEEK = "previous_week"
    CURRENT_MONTH = "current_month"
    PREVIOUS_MONTH = "previous_month"
    # Alias retained for WP-1 placeholder vocabulary
    THIS_MONTH = "this_month"
    EXPLICIT_RANGE = "explicit_range"
    COMPARISON_PERIOD = "comparison_period"
    SIMULATION_RANGE = "simulation_range"
    HISTORICAL_REPLAY_RANGE = "historical_replay_range"
    RECOVERY_REPLAY_RANGE = "recovery_replay_range"


# THIS_MONTH is an alias of CURRENT_MONTH (same derivation).
_RECIPE_ALIASES: dict[str, WindowRecipeId] = {
    "this_month": WindowRecipeId.CURRENT_MONTH,
    "current_month": WindowRecipeId.CURRENT_MONTH,
}


def resolve_window_recipe(value: object) -> WindowRecipeId:
    if isinstance(value, WindowRecipeId):
        if value == WindowRecipeId.THIS_MONTH:
            return WindowRecipeId.CURRENT_MONTH
        return value
    key = str(value or "").strip().lower()
    if key in _RECIPE_ALIASES:
        return _RECIPE_ALIASES[key]
    try:
        rid = WindowRecipeId(key)
    except ValueError as exc:
        raise ValueError(f"invalid_window_recipe:{value}") from exc
    if rid == WindowRecipeId.THIS_MONTH:
        return WindowRecipeId.CURRENT_MONTH
    return rid


class WindowResultStatus(str, Enum):
    """Typed outcome of window construction or event classification (WP-3)."""

    VALID_WINDOW = "valid_window"
    OUT_OF_WINDOW = "out_of_window"
    INVALID_RANGE = "invalid_range"
    INSUFFICIENT_HISTORY = "insufficient_history"
    UNSUPPORTED_TIMEZONE_POLICY = "unsupported_timezone_policy"
    MISSING_QUERY_TIME_CONTEXT = "missing_query_time_context"
    INVALID_ARGUMENT = "invalid_argument"


class EmptinessType(str, Enum):
    """Typed emptiness / sample outcomes (WP-3). Merchant wording is later WPs."""

    NO_STORE_HISTORY = "no_store_history"
    OUT_OF_WINDOW = "out_of_window"
    METRIC_UNSUPPORTED = "metric_unsupported"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    INSUFFICIENT_HISTORY = "insufficient_history"
    TRULY_CLEAR = "truly_clear"
    VALID = "valid"


def ensure_utc(dt: datetime) -> datetime:
    """Normalize to timezone-aware UTC."""
    from datetime import timezone

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def provenance_dict(
    *,
    source_id: str,
    context_kind: Optional[QueryTimeContextKind],
    authority_now: datetime,
    time_provenance: Optional[TimeProvenance] = None,
    correlation_id: str = "",
    timezone_policy: TimezonePolicy = TimezonePolicy.UTC,
) -> dict:
    """Internal provenance bundle (WP-11 may project a merchant-safe subset later)."""
    kind = context_kind
    tp = time_provenance
    if tp is None and kind is not None:
        tp = provenance_for_kind(kind)
    return {
        "time_authority_version": 2,
        "clock_source_id": source_id,
        "query_time_context_kind": kind.value if kind else None,
        "time_provenance": tp.value if tp else None,
        "timezone_policy": timezone_policy.value,
        "correlation_id": (correlation_id or "")[:128] or None,
        "authority_now": ensure_utc(authority_now).isoformat(),
        "merchant_visible": False,
    }
