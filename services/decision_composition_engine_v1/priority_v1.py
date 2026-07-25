# -*- coding: utf-8 -*-
"""
Gate 2E — Decision priority by business impact (not counter size alone).

priority_score = business_impact(0-40) + meaning_urgency(0-20) + actionability(0-15)
               + evidence(0-10) + scale_cap(0-15) − automation_discount(0-20)

Scale is capped — volume informs, never dominates.
Bands: >= 55 needs_action_now · 30-54 monitor · < 30 none
"""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.business_impact_v1 import (
    domain_impact_weight_v1,
)
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
    """Capped volume signal — never the primary driver (Gate 2E)."""
    n = _as_int(affected)
    if n <= 0:
        return 0
    if n >= 40:
        return 15
    if n >= 20:
        return 12
    if n >= 10:
        return 9
    if n >= 5:
        return 6
    if n >= 2:
        return 4
    return 2


def confidence_points(level: str) -> int:
    raw = _norm(level).lower()
    if raw in {"high", "مرتفع", "strong"}:
        return 10
    if raw in {"medium", "متوسط", "moderate"}:
        return 6
    if raw in {"low", "منخفض", "weak"}:
        return 3
    return 0


def meaning_urgency_points(*, domain: str, decision_type: str, why_now: str) -> int:
    """Urgency from business meaning — recovery can be urgent when it threatens revenue."""
    d = _norm(domain)
    t = _norm(decision_type)
    base = 10
    if d in {"revenue", "products", "pricing", "shipping"}:
        base = 18
    elif d == "customer_behaviour":
        base = 16
    elif d == "recovery" or t == DECISION_TYPE_RECOVERABILITY_GAP:
        base = 16
    elif t == DECISION_TYPE_WAITING_RECOVERY or d == "operations":
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
    domain = _norm(
        candidate.get("business_domain")
        or candidate.get("decision_category")
        or ""
    )
    # Prefer stamped Gate 2E weight; else derive from domain / type.
    impact = _as_int(candidate.get("business_impact_weight"))
    if impact <= 0:
        impact = domain_impact_weight_v1(domain) if domain else 10
        # Type fallback when domain missing
        t = _norm(candidate.get("decision_type"))
        if t == DECISION_TYPE_RECOVERABILITY_GAP:
            impact = max(impact, 26)
        elif t == DECISION_TYPE_VERIFIED_FINDING:
            impact = max(impact, 30)
        elif t == DECISION_TYPE_WAITING_RECOVERY:
            impact = max(impact, 14)

    factors = {
        "business_impact": impact,
        "scale": scale_points(affected_count or _as_int(candidate.get("affected_count"))),
        "urgency": meaning_urgency_points(
            domain=domain,
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
        factors["business_impact"]
        + factors["scale"]
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
