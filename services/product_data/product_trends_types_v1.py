# -*- coding: utf-8 -*-
"""
Product Trends Foundation V1 — catalog (directions + windows only).

Describes how metrics change over time. No why, ranking, health, or guidance.
"""
from __future__ import annotations

from dataclasses import dataclass

from services.product_data.product_metrics_types_v1 import (
    WINDOW_D90,
    WINDOW_DAY,
    WINDOW_MONTH,
    WINDOW_WEEK,
)

COMPUTATION_VERSION_V1 = "ptf_v1_delta"

TREND_NEWLY_APPEARED = "newly_appeared"
TREND_DISAPPEARED = "disappeared"
TREND_STABLE = "stable"
TREND_INCREASING = "increasing"
TREND_DECREASING = "decreasing"

TREND_DIRECTIONS = frozenset(
    {
        TREND_NEWLY_APPEARED,
        TREND_DISAPPEARED,
        TREND_STABLE,
        TREND_INCREASING,
        TREND_DECREASING,
    }
)

TREND_WINDOW_TODAY = "today"
TREND_WINDOW_D7 = "d7"
TREND_WINDOW_D30 = "d30"
TREND_WINDOW_D90 = "d90"

SUPPORTED_TREND_WINDOWS = frozenset(
    {
        TREND_WINDOW_TODAY,
        TREND_WINDOW_D7,
        TREND_WINDOW_D30,
        TREND_WINDOW_D90,
    }
)


@dataclass(frozen=True, slots=True)
class TrendWindowSpec:
    trend_window: str
    metric_window_code: str
    length_days: int


TREND_WINDOW_SPECS: dict[str, TrendWindowSpec] = {
    TREND_WINDOW_TODAY: TrendWindowSpec(TREND_WINDOW_TODAY, WINDOW_DAY, 1),
    TREND_WINDOW_D7: TrendWindowSpec(TREND_WINDOW_D7, WINDOW_WEEK, 7),
    TREND_WINDOW_D30: TrendWindowSpec(TREND_WINDOW_D30, WINDOW_MONTH, 30),
    TREND_WINDOW_D90: TrendWindowSpec(TREND_WINDOW_D90, WINDOW_D90, 90),
}


def classify_trend_direction(previous: int, current: int) -> str:
    prev = int(previous or 0)
    curr = int(current or 0)
    if prev == 0 and curr > 0:
        return TREND_NEWLY_APPEARED
    if prev > 0 and curr == 0:
        return TREND_DISAPPEARED
    if curr == prev:
        return TREND_STABLE
    if curr > prev:
        return TREND_INCREASING
    return TREND_DECREASING


__all__ = [
    "COMPUTATION_VERSION_V1",
    "TREND_NEWLY_APPEARED",
    "TREND_DISAPPEARED",
    "TREND_STABLE",
    "TREND_INCREASING",
    "TREND_DECREASING",
    "TREND_DIRECTIONS",
    "TREND_WINDOW_TODAY",
    "TREND_WINDOW_D7",
    "TREND_WINDOW_D30",
    "TREND_WINDOW_D90",
    "SUPPORTED_TREND_WINDOWS",
    "TrendWindowSpec",
    "TREND_WINDOW_SPECS",
    "classify_trend_direction",
]
