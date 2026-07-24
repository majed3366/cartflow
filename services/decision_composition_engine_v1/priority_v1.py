# -*- coding: utf-8 -*-
"""
Deterministic priority for Decision Composition Engine V1.

priority_score = scale(0-30) + impact(0-25) + urgency(0-20)
               + actionability(0-15) + evidence(0-10) − automation_discount(0-20)

Bands:
  >= 55 → needs_action_now
  30-54 → monitor
  < 30  → no_decision_supported (still may publish if contract valid & band override)
"""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.contract_v1 import (
    BAND_MONITOR,
    BAND_NEEDS_ACTION,
    BAND_NONE,
    DECISION_TYPE_RECOVERABILITY_GAP,
    DECISION_TYPE_VERIFIED_FINDING,
    DECISION_TYPE_WAITING_RECOVERY,
)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def scale_points(affected: int) -> int:
    n = _as_int(affected)
    if n <= 0:
        return 0
    if n >= 40:
        return 30
    if n >= 20:
        return 24
    if n >= 10:
        return 18
    if n >= 5:
        return 12
    if n >= 2:
        return 8
    return 4


def confidence_points(level: str) -> int:
    raw = _norm(level).lower()
    if raw in {"high", "مرتفع", "strong"}:
        return 10
    if raw in {"medium", "متوسط", "moderate"}:
        return 6
    if raw in {"low", "منخفض", "weak"}:
        return 3
    return 0


def impact_points(decision_type: str) -> int:
    t = _norm(decision_type)
    if t == DECISION_TYPE_RECOVERABILITY_GAP:
        return 25
    if t == DECISION_TYPE_VERIFIED_FINDING:
        return 20
    if t == DECISION_TYPE_WAITING_RECOVERY:
        return 12
    return 8


def urgency_points(*, decision_type: str, why_now: str) -> int:
    base = 8
    t = _norm(decision_type)
    if t == DECISION_TYPE_RECOVERABILITY_GAP:
        base = 18
    elif t == DECISION_TYPE_WAITING_RECOVERY:
        base = 10
    elif t == DECISION_TYPE_VERIFIED_FINDING:
        base = 14
    if "اليوم" in _norm(why_now) or "الآن" in _norm(why_now):
        base = min(20, base + 2)
    return base


def actionability_points(*, has_first_step: bool, automation_can_resolve: bool) -> int:
    if automation_can_resolve:
        return 2
    return 15 if has_first_step else 5


def automation_discount(*, automation_can_resolve: bool) -> int:
    return 20 if automation_can_resolve else 0


def calculate_priority_v1(
    candidate: Mapping[str, Any],
    *,
    affected_count: int = 0,
    automation_can_resolve: bool = False,
) -> tuple[int, str, dict[str, int]]:
    factors = {
        "scale": scale_points(affected_count or _as_int(candidate.get("affected_count"))),
        "impact": impact_points(_norm(candidate.get("decision_type"))),
        "urgency": urgency_points(
            decision_type=_norm(candidate.get("decision_type")),
            why_now=_norm(candidate.get("why_now")),
        ),
        "actionability": actionability_points(
            has_first_step=bool(_norm(candidate.get("first_step"))),
            automation_can_resolve=automation_can_resolve,
        ),
        "evidence": confidence_points(_norm(candidate.get("confidence"))),
        "automation_discount": automation_discount(
            automation_can_resolve=automation_can_resolve
        ),
    }
    score = (
        factors["scale"]
        + factors["impact"]
        + factors["urgency"]
        + factors["actionability"]
        + factors["evidence"]
        - factors["automation_discount"]
    )
    score = max(0, min(100, score))
    if automation_can_resolve and score < 55:
        band = BAND_MONITOR
    elif score >= 55:
        band = BAND_NEEDS_ACTION
    elif score >= 30:
        band = BAND_MONITOR
    else:
        band = BAND_NONE
    return score, band, factors


__all__ = ["calculate_priority_v1"]
