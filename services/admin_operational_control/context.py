# -*- coding: utf-8 -*-
"""Shared read-only context for admin operational control modules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperationalIssue:
    code: str
    active: bool
    problem_ar: str
    impact_ar: str
    if_ignored_ar: str
    affected_stores: int
    urgency: str  # low | medium | high
    action_ar: str
    detail_href: str
    detail_anchor: str = ""
    tier: str = "potential"  # potential | actual
    why_ar: str = ""


@dataclass
class OperationalControlContext:
    generated_at_utc: str
    admin_rt: dict[str, Any]
    admin_summary: dict[str, Any]
    cart: dict[str, Any]
    pool: dict[str, Any]
    bg: dict[str, Any]
    wa: dict[str, Any]
    warnings: list[dict[str, str]]
    issues: list[OperationalIssue] = field(default_factory=list)
    affected_stores_estimate: int = 0
    slow_cart_event_count: int = 0
    pool_timeout_count: int = 0
    whatsapp_failed_24h: int | None = None
    background_failure_count: int = 0
    provider_unstable: bool = False
