# -*- coding: utf-8 -*-
"""Canonical CartFlow SaaS plans — single source of truth."""
from __future__ import annotations

from typing import FrozenSet, Literal, Mapping

PlanId = Literal["starter", "growth", "pro"]

PLAN_STARTER: PlanId = "starter"
PLAN_GROWTH: PlanId = "growth"
PLAN_PRO: PlanId = "pro"

CANONICAL_PLAN_IDS: tuple[PlanId, ...] = (PLAN_STARTER, PLAN_GROWTH, PLAN_PRO)

DEFAULT_PLAN_ID: PlanId = PLAN_STARTER

PLAN_LABEL_AR: Mapping[PlanId, str] = {
    PLAN_STARTER: "Starter",
    PLAN_GROWTH: "Growth",
    PLAN_PRO: "Pro",
}

PLAN_RANK: Mapping[PlanId, int] = {
    PLAN_STARTER: 1,
    PLAN_GROWTH: 2,
    PLAN_PRO: 3,
}

# Starter entitlements
_STARTER_FEATURES: FrozenSet[str] = frozenset(
    {
        "widget",
        "reason_capture",
        "whatsapp_recovery",
        "dashboard",
        "basic_analytics",
    }
)

# Growth adds (cumulative on top of Starter)
_GROWTH_FEATURES: FrozenSet[str] = frozenset(
    {
        "vip_detection",
        "vip_alerts",
        "multi_message",
        "per_reason_templates",
        "per_reason_timing",
        "advanced_analytics",
        "recovery_insights",
        "merchant_controls",
    }
)

# Pro adds (cumulative on top of Growth)
_PRO_FEATURES: FrozenSet[str] = frozenset(
    {
        "advanced_message_logic",
        "advanced_recovery_controls",
        "operational_insights",
        "future_product_intelligence",
        "future_offer_intelligence",
        "future_operational_intelligence",
    }
)

PLAN_ENTITLEMENTS: Mapping[PlanId, FrozenSet[str]] = {
    PLAN_STARTER: _STARTER_FEATURES,
    PLAN_GROWTH: _STARTER_FEATURES | _GROWTH_FEATURES,
    PLAN_PRO: _STARTER_FEATURES | _GROWTH_FEATURES | _PRO_FEATURES,
}

ALL_KNOWN_FEATURES: FrozenSet[str] = PLAN_ENTITLEMENTS[PLAN_PRO]


def normalize_plan_id(raw: str | None) -> PlanId:
    key = (raw or "").strip().lower()
    if key in CANONICAL_PLAN_IDS:
        return key  # type: ignore[return-value]
    return DEFAULT_PLAN_ID


def plan_includes_plan(*, current: PlanId, required: PlanId) -> bool:
    return PLAN_RANK[current] >= PLAN_RANK[required]


def features_for_plan(plan_id: PlanId) -> FrozenSet[str]:
    return PLAN_ENTITLEMENTS[normalize_plan_id(plan_id)]
