# -*- coding: utf-8 -*-
"""
Compatibility layer for dual-path migration (WP-1).

Existing call sites may later switch private `_utc_now` helpers to
`legacy_utc_now()` without behaviour change while SystemClock is ambient.

Consumer migration is later WPs. This module must not alter production paths
until those WPs opt in.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from services.time_authority.authority import authority_now, get_provider
from services.time_authority.contracts import ensure_utc


def legacy_utc_now() -> datetime:
    """
    Drop-in replacement target for module-local `_utc_now()`.

    Under ambient SystemClock this matches wall UTC. Under an active Time
    Authority provider (tests / future contexts) it follows authority_now().
    """
    return authority_now()


def coerce_optional_now(now: Optional[datetime]) -> datetime:
    """
    Compatibility helper for APIs that accept optional `now=`.

    If `now` is provided, return UTC-normalized value (fixed instant).
    If omitted, return authority_now().
    """
    if now is None:
        return authority_now()
    return ensure_utc(now)


def is_using_system_clock() -> bool:
    """True when ambient/default system provider is active."""
    from services.time_authority.contracts import ClockSourceKind

    return str(get_provider().source_id) == ClockSourceKind.SYSTEM.value
