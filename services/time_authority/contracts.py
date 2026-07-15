# -*- coding: utf-8 -*-
"""
Time Authority contracts — stable types and protocols (WP-1).

Consumers depend on these interfaces, not on provider internals.
Filtering recipes / emptiness enums are reserved for WP-3; placeholders listed for stability.
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
    """Kinds from Time Authority Architecture V2 §5."""

    CURRENT_PRODUCTION = "current_production"
    HISTORICAL_REPLAY = "historical_replay"
    SIMULATION = "simulation"
    TESTING = "testing"
    FUTURE_REPLAY = "future_replay"
    RECOVERY_REPLAY = "recovery_replay"


# Reserved for WP-3 — do not use for merchant windows until filtering lands.
class WindowRecipeId(str, Enum):
    LAST_N_DAYS = "last_n_days"
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_MONTH = "this_month"


class EmptinessType(str, Enum):
    """Reserved for WP-3 typed emptiness."""

    NO_STORE_HISTORY = "no_store_history"
    OUT_OF_WINDOW = "out_of_window"
    METRIC_UNSUPPORTED = "metric_unsupported"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    TRULY_CLEAR = "truly_clear"


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
) -> dict:
    """Minimal provenance bundle for future presentation (WP-11)."""
    return {
        "time_authority_version": 1,
        "clock_source_id": source_id,
        "query_time_context_kind": context_kind.value if context_kind else None,
        "authority_now": ensure_utc(authority_now).isoformat(),
    }
