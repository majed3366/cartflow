# -*- coding: utf-8 -*-
"""
Typed emptiness / sample classification against a governed TimeWindow (WP-3).

No merchant wording. No I/O. Consumers map EmptinessType to UX later.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from services.time_authority.contracts import (
    EmptinessType,
    WindowResultStatus,
    ensure_utc,
)
from services.time_authority.filtering import TimeWindow


@dataclass(frozen=True)
class EmptinessResult:
    """Typed classification relative to a window (internal platform evidence)."""

    emptiness_type: EmptinessType
    status: WindowResultStatus
    window: TimeWindow
    event_at: Optional[datetime] = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.emptiness_type == EmptinessType.VALID


def classify_timestamp(
    event_at: datetime,
    window: TimeWindow,
) -> EmptinessResult:
    """Classify a single event timestamp against a window."""
    if not window.ok:
        return EmptinessResult(
            emptiness_type=EmptinessType.METRIC_UNSUPPORTED,
            status=window.status,
            window=window,
            event_at=ensure_utc(event_at),
            detail=f"window_not_valid:{window.status.value}",
        )
    t = ensure_utc(event_at)
    if window.contains(t):
        return EmptinessResult(
            emptiness_type=EmptinessType.VALID,
            status=WindowResultStatus.VALID_WINDOW,
            window=window,
            event_at=t,
        )
    return EmptinessResult(
        emptiness_type=EmptinessType.OUT_OF_WINDOW,
        status=WindowResultStatus.OUT_OF_WINDOW,
        window=window,
        event_at=t,
        detail="event_outside_half_open_interval",
    )


def classify_store_history(
    *,
    window: TimeWindow,
    has_any_history: bool,
    has_in_window: bool,
    sample_count: Optional[int] = None,
    min_sample: Optional[int] = None,
    earliest_at: Optional[datetime] = None,
) -> EmptinessResult:
    """
    Distinguish silent-empty failure modes for future consumers.

    - no history anywhere → ``no_store_history``
    - history exists but none in window → ``out_of_window``
    - in-window but sample below threshold → ``insufficient_sample``
    - comparison needs span before window start → ``insufficient_history``
    """
    if not window.ok:
        return EmptinessResult(
            emptiness_type=EmptinessType.METRIC_UNSUPPORTED,
            status=window.status,
            window=window,
            detail=f"window_not_valid:{window.status.value}",
        )
    if not has_any_history:
        return EmptinessResult(
            emptiness_type=EmptinessType.NO_STORE_HISTORY,
            status=WindowResultStatus.VALID_WINDOW,
            window=window,
            detail="no_events_for_store",
        )
    if earliest_at is not None:
        earliest = ensure_utc(earliest_at)
        if earliest >= window.end_at:
            return EmptinessResult(
                emptiness_type=EmptinessType.OUT_OF_WINDOW,
                status=WindowResultStatus.OUT_OF_WINDOW,
                window=window,
                event_at=earliest,
                detail="earliest_at_on_or_after_window_end",
            )
        if earliest > window.start_at and not has_in_window:
            return EmptinessResult(
                emptiness_type=EmptinessType.INSUFFICIENT_HISTORY,
                status=WindowResultStatus.INSUFFICIENT_HISTORY,
                window=window,
                event_at=earliest,
                detail="history_starts_after_window_start",
            )
    if not has_in_window:
        return EmptinessResult(
            emptiness_type=EmptinessType.OUT_OF_WINDOW,
            status=WindowResultStatus.OUT_OF_WINDOW,
            window=window,
            detail="history_exists_outside_window",
        )
    if (
        min_sample is not None
        and sample_count is not None
        and int(sample_count) < int(min_sample)
    ):
        return EmptinessResult(
            emptiness_type=EmptinessType.INSUFFICIENT_SAMPLE,
            status=WindowResultStatus.VALID_WINDOW,
            window=window,
            detail=f"sample_count={sample_count}<min_sample={min_sample}",
        )
    if has_in_window and (sample_count is None or int(sample_count) > 0):
        return EmptinessResult(
            emptiness_type=EmptinessType.VALID,
            status=WindowResultStatus.VALID_WINDOW,
            window=window,
        )
    return EmptinessResult(
        emptiness_type=EmptinessType.TRULY_CLEAR,
        status=WindowResultStatus.VALID_WINDOW,
        window=window,
        detail="in_window_zero_after_eligibility",
    )
