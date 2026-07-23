# -*- coding: utf-8 -*-
"""
Commercial Guidance Foundation V1 — canonical guidance registry.

Single source of truth for supported guidance types. No scattered keys.
"""
from __future__ import annotations

from typing import Any

from services.product_data.commercial_guidance_types_v1 import (
    DEFAULT_PROHIBITED_CLAIMS,
    DEFAULT_UNKNOWN_FACTS,
    KEY_CONTINUE_OBSERVING,
    KEY_DEFER,
    KEY_INVESTIGATE_CONVERSION,
    KEY_MONITOR_NEW,
    KEY_NO_GUIDANCE,
    KEY_REVIEW_CART,
    KEY_REVIEW_PRODUCT,
    KEY_VERIFY_GAP,
    REGISTRY_VERSION_V1,
    STATUS_ABSTAINED,
    STATUS_ACTIVE,
    STATUS_DEFERRED,
)
from services.product_data.guidance_eligibility_types_v1 import (
    STATUS_ELIGIBLE,
    STATUS_CONFLICTING_KNOWLEDGE,
    STATUS_EXPIRED_KNOWLEDGE,
    STATUS_INSUFFICIENT_CONFIDENCE,
    STATUS_INSUFFICIENT_KNOWLEDGE,
    STATUS_PENDING_OBSERVATION,
)

_INELIGIBLE = frozenset(
    {
        STATUS_INSUFFICIENT_KNOWLEDGE,
        STATUS_INSUFFICIENT_CONFIDENCE,
        STATUS_CONFLICTING_KNOWLEDGE,
        STATUS_EXPIRED_KNOWLEDGE,
        STATUS_PENDING_OBSERVATION,
    }
)


def _entry(
    *,
    key: str,
    definition: str,
    permitted_statuses: frozenset[str],
    required_knowledge_types: tuple[str, ...],
    prohibited_blocks: tuple[str, ...],
    max_claim_strength: str,
    validity_days: int,
    default_unknowns: tuple[str, ...],
    default_prohibited: tuple[str, ...],
    rule_version: str,
    default_status: str,
    active: bool = True,
) -> dict[str, Any]:
    return {
        "guidance_key": key,
        "definition": definition,
        "permitted_eligibility_statuses": sorted(permitted_statuses),
        "required_knowledge_types": list(required_knowledge_types),
        "prohibited_blocking_conditions": list(prohibited_blocks),
        "max_claim_strength": max_claim_strength,
        "default_validity_days": validity_days,
        "default_unknowns": list(default_unknowns),
        "default_prohibited_claims": list(default_prohibited),
        "rule_version": rule_version,
        "default_guidance_status": default_status,
        "active": active,
        "registry_version": REGISTRY_VERSION_V1,
    }


GUIDANCE_REGISTRY_V1: dict[str, dict[str, Any]] = {
    KEY_NO_GUIDANCE: _entry(
        key=KEY_NO_GUIDANCE,
        definition=(
            "CartFlow does not currently have sufficient governed grounds "
            "to issue commercial guidance."
        ),
        permitted_statuses=_INELIGIBLE | frozenset({STATUS_ELIGIBLE}),
        required_knowledge_types=(),
        prohibited_blocks=(),
        max_claim_strength="none",
        validity_days=7,
        default_unknowns=(DEFAULT_UNKNOWN_FACTS,),
        default_prohibited=DEFAULT_PROHIBITED_CLAIMS,
        rule_version="cgf_rule_no_guidance_v1",
        default_status=STATUS_ABSTAINED,
    ),
    KEY_DEFER: _entry(
        key=KEY_DEFER,
        definition=(
            "Defer commercial action until additional evidence is available."
        ),
        permitted_statuses=frozenset({STATUS_ELIGIBLE}),
        required_knowledge_types=(),
        prohibited_blocks=(),
        max_claim_strength="deferral",
        validity_days=7,
        default_unknowns=(DEFAULT_UNKNOWN_FACTS,),
        default_prohibited=DEFAULT_PROHIBITED_CLAIMS,
        rule_version="cgf_rule_defer_v1",
        default_status=STATUS_DEFERRED,
    ),
    KEY_CONTINUE_OBSERVING: _entry(
        key=KEY_CONTINUE_OBSERVING,
        definition=(
            "Continue observing the pattern before making a commercial change."
        ),
        permitted_statuses=frozenset({STATUS_ELIGIBLE}),
        required_knowledge_types=("evidence_quality", "metric_trend_observation"),
        prohibited_blocks=(),
        max_claim_strength="observe",
        validity_days=7,
        default_unknowns=(DEFAULT_UNKNOWN_FACTS,),
        default_prohibited=DEFAULT_PROHIBITED_CLAIMS,
        rule_version="cgf_rule_continue_observing_v1",
        default_status=STATUS_ACTIVE,
    ),
    KEY_MONITOR_NEW: _entry(
        key=KEY_MONITOR_NEW,
        definition=(
            "Monitor whether the new pattern persists before acting."
        ),
        permitted_statuses=frozenset({STATUS_ELIGIBLE}),
        required_knowledge_types=("metric_trend_observation",),
        prohibited_blocks=(),
        max_claim_strength="monitor",
        validity_days=7,
        default_unknowns=(DEFAULT_UNKNOWN_FACTS,),
        default_prohibited=DEFAULT_PROHIBITED_CLAIMS,
        rule_version="cgf_rule_monitor_new_v1",
        default_status=STATUS_ACTIVE,
    ),
    KEY_INVESTIGATE_CONVERSION: _entry(
        key=KEY_INVESTIGATE_CONVERSION,
        definition=(
            "Investigate what happens between demonstrated intent and completion."
        ),
        permitted_statuses=frozenset({STATUS_ELIGIBLE}),
        required_knowledge_types=("metric_trend_observation", "evidence_gap"),
        prohibited_blocks=(),
        max_claim_strength="investigate",
        validity_days=7,
        default_unknowns=(DEFAULT_UNKNOWN_FACTS,),
        default_prohibited=DEFAULT_PROHIBITED_CLAIMS,
        rule_version="cgf_rule_investigate_conversion_v1",
        default_status=STATUS_ACTIVE,
    ),
    KEY_REVIEW_CART: _entry(
        key=KEY_REVIEW_CART,
        definition=(
            "Review how carts progress after customer intent is established."
        ),
        permitted_statuses=frozenset({STATUS_ELIGIBLE}),
        required_knowledge_types=("metric_trend_observation",),
        prohibited_blocks=(),
        max_claim_strength="review",
        validity_days=7,
        default_unknowns=(DEFAULT_UNKNOWN_FACTS,),
        default_prohibited=DEFAULT_PROHIBITED_CLAIMS,
        rule_version="cgf_rule_review_cart_v1",
        default_status=STATUS_ACTIVE,
    ),
    KEY_REVIEW_PRODUCT: _entry(
        key=KEY_REVIEW_PRODUCT,
        definition=(
            "Review the product experience and customer journey around this product."
        ),
        permitted_statuses=frozenset({STATUS_ELIGIBLE}),
        required_knowledge_types=("metric_trend_observation",),
        prohibited_blocks=(),
        max_claim_strength="review",
        validity_days=7,
        default_unknowns=(DEFAULT_UNKNOWN_FACTS,),
        default_prohibited=DEFAULT_PROHIBITED_CLAIMS,
        rule_version="cgf_rule_review_product_v1",
        default_status=STATUS_ACTIVE,
    ),
    KEY_VERIFY_GAP: _entry(
        key=KEY_VERIFY_GAP,
        definition=(
            "Verify or improve the missing evidence before drawing a stronger "
            "commercial conclusion."
        ),
        permitted_statuses=frozenset({STATUS_ELIGIBLE}),
        required_knowledge_types=("evidence_gap",),
        prohibited_blocks=(),
        max_claim_strength="verify_data",
        validity_days=7,
        default_unknowns=(DEFAULT_UNKNOWN_FACTS,),
        default_prohibited=DEFAULT_PROHIBITED_CLAIMS,
        rule_version="cgf_rule_verify_gap_v1",
        default_status=STATUS_ACTIVE,
    ),
}


def get_registry_entry_v1(guidance_key: str) -> dict[str, Any] | None:
    entry = GUIDANCE_REGISTRY_V1.get(str(guidance_key or ""))
    if not entry or not entry.get("active"):
        return None
    return dict(entry)


def list_active_guidance_keys_v1() -> list[str]:
    return sorted(
        k for k, v in GUIDANCE_REGISTRY_V1.items() if v.get("active")
    )


def registry_is_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not GUIDANCE_REGISTRY_V1:
        errors.append("empty_registry")
    for key, entry in GUIDANCE_REGISTRY_V1.items():
        if entry.get("guidance_key") != key:
            errors.append(f"key_mismatch:{key}")
        if not entry.get("rule_version"):
            errors.append(f"missing_rule_version:{key}")
        if key == KEY_NO_GUIDANCE and entry.get("default_guidance_status") != STATUS_ABSTAINED:
            errors.append("no_guidance_must_abstain")
    return (len(errors) == 0, errors)


__all__ = [
    "GUIDANCE_REGISTRY_V1",
    "get_registry_entry_v1",
    "list_active_guidance_keys_v1",
    "registry_is_valid_v1",
]
