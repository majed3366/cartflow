# -*- coding: utf-8 -*-
"""Progressive execution scale profiles — Phase 3."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ScaleProfile:
    profile_id: str
    duration_days: int
    journeys_per_day: float
    max_events_per_run: int
    batch_size: int
    pause_ms_between_batches: int
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PROFILES: dict[str, ScaleProfile] = {
    "small": ScaleProfile(
        profile_id="small",
        duration_days=3,
        journeys_per_day=2.0,
        max_events_per_run=120,
        batch_size=20,
        pause_ms_between_batches=50,
        description="3-day controlled validation",
    ),
    "medium": ScaleProfile(
        profile_id="medium",
        duration_days=14,
        journeys_per_day=3.0,
        max_events_per_run=800,
        batch_size=40,
        pause_ms_between_batches=100,
        description="14-day medium historical run",
    ),
    "large": ScaleProfile(
        profile_id="large",
        duration_days=30,
        journeys_per_day=4.0,
        max_events_per_run=2500,
        batch_size=50,
        pause_ms_between_batches=150,
        description="30-day large historical run",
    ),
    "full": ScaleProfile(
        profile_id="full",
        duration_days=60,
        journeys_per_day=5.0,
        max_events_per_run=6000,
        batch_size=50,
        pause_ms_between_batches=200,
        description="60-day full historical run",
    ),
    "stress": ScaleProfile(
        profile_id="stress",
        duration_days=90,
        journeys_per_day=6.0,
        max_events_per_run=12000,
        batch_size=50,
        pause_ms_between_batches=250,
        description="90+ day stress — never first",
    ),
}


def get_scale_profile(profile_id: str) -> ScaleProfile:
    key = str(profile_id or "small").strip().lower()
    if key not in _PROFILES:
        raise KeyError(f"unknown_scale_profile:{profile_id}")
    return _PROFILES[key]


def resolve_scale_profile(
    *,
    profile_id: Optional[str] = None,
    duration_days: Optional[int] = None,
) -> ScaleProfile:
    """Prefer explicit profile; otherwise map duration to nearest progressive tier."""
    if profile_id:
        return get_scale_profile(profile_id)
    days = int(duration_days or 3)
    if days <= 3:
        return get_scale_profile("small")
    if days <= 14:
        return get_scale_profile("medium")
    if days <= 30:
        return get_scale_profile("large")
    if days <= 60:
        return get_scale_profile("full")
    return get_scale_profile("stress")


def list_scale_profiles() -> list[ScaleProfile]:
    order = ("small", "medium", "large", "full", "stress")
    return [_PROFILES[k] for k in order]
