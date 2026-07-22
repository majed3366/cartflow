# -*- coding: utf-8 -*-
"""Surface Composition Foundation V1 — surface_registry_v1 + class maps."""
from __future__ import annotations

from typing import Any

from services.product_data.surface_composition_types_v1 import (
    CLASS_ACTION_QUEUE,
    CLASS_COMMERCIAL_GUIDANCE,
    CLASS_CONFIGURATION,
    CLASS_CRITICAL_ATTENTION,
    CLASS_EMPTY_STATE,
    CLASS_EVIDENCE_GAP,
    CLASS_EXECUTIVE_SUMMARY,
    CLASS_KNOWLEDGE,
    CLASS_OBSERVATION,
    CLASS_OPERATIONAL_HEALTH,
    CLASS_RECOVERY_HEALTH,
    CLASS_TIMELINE,
    CLASS_TREND,
    INTENT_CONFIGURATION,
    INTENT_EVIDENCE_NOTICE,
    INTENT_HEADLINE,
    INTENT_HERO,
    INTENT_INFORMATION,
    INTENT_INSIGHT_CARD,
    INTENT_OPERATIONAL_STATE,
    INTENT_PRIORITY_CARD,
    INTENT_SUMMARY_CARD,
    INTENT_WARNING,
    SURFACE_CARTS,
    SURFACE_COMMUNICATION,
    SURFACE_DECISION,
    SURFACE_HOME,
    SURFACE_REGISTRY_VERSION_V1,
    SURFACE_SETTINGS,
    SURFACES_V1,
)


def _surface(
    *,
    surface_id: str,
    purpose: str,
    merchant_question: str,
    owner: str,
    supported_classes: tuple[str, ...],
    cognitive_load: dict[str, int],
    refresh_policy: str,
    priority_policy: str,
    collapse_policy: str,
    stale_policy: str,
    routing_policy: str,
    ordering_policy: str,
) -> dict[str, Any]:
    return {
        "surface_id": surface_id,
        "purpose": purpose,
        "merchant_question_answered": merchant_question,
        "owner": owner,
        "supported_information_classes": list(supported_classes),
        "maximum_cognitive_load": dict(cognitive_load),
        "refresh_policy": refresh_policy,
        "priority_policy": priority_policy,
        "collapse_policy": collapse_policy,
        "stale_policy": stale_policy,
        "routing_policy": routing_policy,
        "ordering_policy": ordering_policy,
        "version": SURFACE_REGISTRY_VERSION_V1,
    }


SURFACE_REGISTRY_V1: dict[str, dict[str, Any]] = {
    SURFACE_HOME: _surface(
        surface_id=SURFACE_HOME,
        purpose="Compose what the merchant should know now.",
        merchant_question="What should I know about my store right now?",
        owner="surface_composition_foundation_v1",
        supported_classes=(
            CLASS_EXECUTIVE_SUMMARY,
            CLASS_CRITICAL_ATTENTION,
            CLASS_COMMERCIAL_GUIDANCE,
            CLASS_KNOWLEDGE,
            CLASS_EVIDENCE_GAP,
            CLASS_OBSERVATION,
            CLASS_EMPTY_STATE,
        ),
        cognitive_load={
            INTENT_HERO: 1,
            CLASS_EXECUTIVE_SUMMARY: 4,
            CLASS_CRITICAL_ATTENTION: 5,
            CLASS_KNOWLEDGE: 3,
            CLASS_COMMERCIAL_GUIDANCE: 3,
        },
        refresh_policy="consume_current_compositions_only",
        priority_policy="impact_urgency_freshness_confidence",
        collapse_policy="overflow_to_collapsed_never_expand",
        stale_policy="aging_then_stale_then_expire",
        routing_policy="consume_guidance_routing_destinations_only",
        ordering_policy="deterministic_priority_score_desc",
    ),
    SURFACE_DECISION: _surface(
        surface_id=SURFACE_DECISION,
        purpose="Compose decisions that require merchant reasoning or review.",
        merchant_question="What decision requires my reasoning or review?",
        owner="surface_composition_foundation_v1",
        supported_classes=(
            CLASS_CRITICAL_ATTENTION,
            CLASS_COMMERCIAL_GUIDANCE,
            CLASS_EVIDENCE_GAP,
            CLASS_ACTION_QUEUE,
            CLASS_EMPTY_STATE,
        ),
        cognitive_load={
            INTENT_HERO: 1,
            CLASS_CRITICAL_ATTENTION: 8,
            CLASS_COMMERCIAL_GUIDANCE: 5,
            CLASS_EVIDENCE_GAP: 3,
        },
        refresh_policy="consume_current_compositions_only",
        priority_policy="impact_urgency_evidence_completeness",
        collapse_policy="overflow_to_collapsed_never_expand",
        stale_policy="aging_then_stale_then_expire",
        routing_policy="consume_guidance_routing_destinations_only",
        ordering_policy="deterministic_priority_score_desc",
    ),
    SURFACE_CARTS: _surface(
        surface_id=SURFACE_CARTS,
        purpose="Compose cart operational attention.",
        merchant_question="What is happening in carts, and what needs attention?",
        owner="surface_composition_foundation_v1",
        supported_classes=(
            CLASS_OPERATIONAL_HEALTH,
            CLASS_RECOVERY_HEALTH,
            CLASS_COMMERCIAL_GUIDANCE,
            CLASS_CRITICAL_ATTENTION,
            CLASS_EMPTY_STATE,
        ),
        cognitive_load={
            CLASS_CRITICAL_ATTENTION: 6,
            CLASS_OPERATIONAL_HEALTH: 4,
            CLASS_RECOVERY_HEALTH: 4,
            CLASS_COMMERCIAL_GUIDANCE: 4,
        },
        refresh_policy="consume_current_compositions_only",
        priority_policy="operational_severity_urgency_freshness",
        collapse_policy="overflow_to_collapsed_never_expand",
        stale_policy="aging_then_stale_then_expire",
        routing_policy="consume_guidance_routing_destinations_only",
        ordering_policy="deterministic_priority_score_desc",
    ),
    SURFACE_COMMUNICATION: _surface(
        surface_id=SURFACE_COMMUNICATION,
        purpose="Compose communication follow-up attention.",
        merchant_question="What happened in communication, and what needs follow-up?",
        owner="surface_composition_foundation_v1",
        supported_classes=(
            CLASS_ACTION_QUEUE,
            CLASS_OBSERVATION,
            CLASS_TIMELINE,
            CLASS_EMPTY_STATE,
        ),
        cognitive_load={
            CLASS_ACTION_QUEUE: 5,
            CLASS_OBSERVATION: 3,
            CLASS_TIMELINE: 3,
        },
        refresh_policy="consume_current_compositions_only",
        priority_policy="urgency_freshness_confidence",
        collapse_policy="overflow_to_collapsed_never_expand",
        stale_policy="aging_then_stale_then_expire",
        routing_policy="consume_guidance_routing_destinations_only",
        ordering_policy="deterministic_priority_score_desc",
    ),
    SURFACE_SETTINGS: _surface(
        surface_id=SURFACE_SETTINGS,
        purpose="Compose configuration control context.",
        merchant_question="How do I control platform behavior and configuration?",
        owner="surface_composition_foundation_v1",
        supported_classes=(
            CLASS_CONFIGURATION,
            CLASS_EMPTY_STATE,
        ),
        cognitive_load={
            CLASS_CONFIGURATION: 6,
        },
        refresh_policy="consume_current_compositions_only",
        priority_policy="configuration_relevance_freshness",
        collapse_policy="overflow_to_collapsed_never_expand",
        stale_policy="aging_then_stale_then_expire",
        routing_policy="consume_guidance_routing_destinations_only",
        ordering_policy="deterministic_priority_score_desc",
    ),
}


# Presentation type → (information_class, default_presentation_intent)
PRESENTATION_CLASS_MAP_V1: dict[str, tuple[str, str]] = {
    "executive_summary": (CLASS_EXECUTIVE_SUMMARY, INTENT_SUMMARY_CARD),
    "decision_prompt": (CLASS_CRITICAL_ATTENTION, INTENT_PRIORITY_CARD),
    "operational_notice": (CLASS_OPERATIONAL_HEALTH, INTENT_OPERATIONAL_STATE),
    "monitoring_state": (CLASS_OBSERVATION, INTENT_INSIGHT_CARD),
    "evidence_gap_state": (CLASS_EVIDENCE_GAP, INTENT_EVIDENCE_NOTICE),
    "follow_up_context": (CLASS_ACTION_QUEUE, INTENT_INFORMATION),
    "configuration_context": (CLASS_CONFIGURATION, INTENT_CONFIGURATION),
    "abstention_state": (CLASS_EVIDENCE_GAP, INTENT_WARNING),
}


# Duplicate-group full-explanation owner (one surface owns full explanation).
DUPLICATE_OWNER_BY_CLASS_V1: dict[str, str] = {
    CLASS_EXECUTIVE_SUMMARY: SURFACE_HOME,
    CLASS_CRITICAL_ATTENTION: SURFACE_DECISION,
    CLASS_COMMERCIAL_GUIDANCE: SURFACE_DECISION,
    CLASS_KNOWLEDGE: SURFACE_HOME,
    CLASS_OPERATIONAL_HEALTH: SURFACE_CARTS,
    CLASS_RECOVERY_HEALTH: SURFACE_CARTS,
    CLASS_EVIDENCE_GAP: SURFACE_DECISION,
    CLASS_TREND: SURFACE_HOME,
    CLASS_OBSERVATION: SURFACE_HOME,
    CLASS_TIMELINE: SURFACE_COMMUNICATION,
    CLASS_ACTION_QUEUE: SURFACE_COMMUNICATION,
    CLASS_CONFIGURATION: SURFACE_SETTINGS,
    CLASS_EMPTY_STATE: SURFACE_HOME,
}


EMPTY_STATE_KEYS_V1 = (
    "evidence_still_growing",
    "no_operational_issues",
    "insufficient_evidence",
    "nothing_requiring_action",
)


def list_surfaces_v1() -> list[str]:
    return sorted(SURFACE_REGISTRY_V1.keys())


def get_surface_registry_entry_v1(surface_id: str) -> dict[str, Any] | None:
    entry = SURFACE_REGISTRY_V1.get(str(surface_id or ""))
    return dict(entry) if entry else None


def surface_registry_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    for key in SURFACES_V1:
        if key not in SURFACE_REGISTRY_V1:
            errors.append(f"missing_surface:{key}")
    for key, entry in SURFACE_REGISTRY_V1.items():
        if entry.get("surface_id") != key:
            errors.append(f"key_mismatch:{key}")
        if entry.get("owner") != "surface_composition_foundation_v1":
            errors.append(f"owner_mismatch:{key}")
        if not entry.get("supported_information_classes"):
            errors.append(f"no_classes:{key}")
        if not entry.get("maximum_cognitive_load"):
            errors.append(f"no_cognitive_load:{key}")
        for banned in ("css", "pixel", "component", "figma", "show_on_home"):
            blob = str(entry).lower()
            if banned in blob and banned == "show_on_home":
                errors.append(f"page_owned_field:{banned}")
    extra = set(SURFACE_REGISTRY_V1) - set(SURFACES_V1)
    for key in sorted(extra):
        errors.append(f"unsupported_surface:{key}")
    return (len(errors) == 0, errors)


__all__ = [
    "SURFACE_REGISTRY_V1",
    "PRESENTATION_CLASS_MAP_V1",
    "DUPLICATE_OWNER_BY_CLASS_V1",
    "EMPTY_STATE_KEYS_V1",
    "list_surfaces_v1",
    "get_surface_registry_entry_v1",
    "surface_registry_valid_v1",
]
