# -*- coding: utf-8 -*-
"""
Commercial Guidance Integration V1 — Knowledge intake policy registry (cguide_v1).

Code-owned. Maps governed Knowledge types to merchant objectives.
Does not invent causes, solutions, or automatic actions.
"""
from __future__ import annotations

from typing import Any, Optional

from services.product_data.commercial_guidance_knowledge_types_v1 import (
    ELIG_CONFLICTING,
    ELIG_ELIGIBLE,
    ELIG_INSUFFICIENT,
    ELIG_OBSERVE_ONLY,
    GUIDANCE_KEYS,
    KEY_COLLECT_EVIDENCE,
    KEY_DELAY_CONFLICT,
    KEY_INVESTIGATE_CONVERSION,
    KEY_INVESTIGATE_SHIPPING,
    KEY_NO_GUIDANCE,
    KEY_PRESERVE_INFLUENCE,
    KEY_REVIEW_PRODUCT_GAP,
    KEY_REVIEW_REPEATED,
    KEY_REVIEW_WA_RETURN,
    KT_EVIDENCE_CONFLICT,
    KT_EVIDENCE_GAP,
    KT_HESITATION_RECOVERY,
    KT_PRODUCT_INTEREST_GAP,
    KT_RECOVERY_INFLUENCE,
    KT_REPEATED_INTEREST,
    KT_TRAFFIC_GAP,
    KT_WA_RETURN,
    REGISTRY_VERSION_V1,
)


def _policy(
    *,
    knowledge_type: str,
    guidance_key: str,
    merchant_objective: str,
    eligibility_when_current: str,
    eligible_actions: tuple[str, ...],
    forbidden_actions: tuple[str, ...],
    minimum_confidence: str,
    freshness_days: int,
    contradiction_policy: str,
    abstention_policy: str,
    routing_eligibility: bool,
    active: bool = True,
    version: str = "1",
) -> dict[str, Any]:
    return {
        "knowledge_type": knowledge_type,
        "guidance_key": guidance_key,
        "merchant_objective": merchant_objective,
        "applicable_scope": "store_or_subject",
        "eligibility_when_current": eligibility_when_current,
        "minimum_confidence": minimum_confidence,
        "freshness_days": freshness_days,
        "evidence_requirements": ("current_knowledge_record",),
        "contradiction_policy": contradiction_policy,
        "abstention_policy": abstention_policy,
        "lifecycle": "create_update_supersede_expire",
        "routing_eligibility": routing_eligibility,
        "expiry_policy": f"valid_until_or_{freshness_days}d",
        "eligible_actions": list(eligible_actions),
        "forbidden_actions": list(forbidden_actions),
        "active": active,
        "version": version,
        "registry_version": REGISTRY_VERSION_V1,
    }


GUIDANCE_INTAKE_POLICIES_V1: tuple[dict[str, Any], ...] = (
    _policy(
        knowledge_type=KT_HESITATION_RECOVERY,
        guidance_key=KEY_INVESTIGATE_SHIPPING,
        merchant_objective=(
            "Investigate checkout friction related to shipping."
        ),
        eligibility_when_current=ELIG_ELIGIBLE,
        eligible_actions=("review_checkout_shipping_experience",),
        forbidden_actions=(
            "reduce_shipping_cost",
            "offer_shipping_discount",
            "claim_shipping_cost_caused_abandonment",
        ),
        minimum_confidence="from_knowledge",
        freshness_days=7,
        contradiction_policy="abstain_if_prohibited_missing",
        abstention_policy="truthful_abstain",
        routing_eligibility=False,
    ),
    _policy(
        knowledge_type=KT_PRODUCT_INTEREST_GAP,
        guidance_key=KEY_REVIEW_PRODUCT_GAP,
        merchant_objective=(
            "Review why this product attracts interest but completes fewer purchases."
        ),
        eligibility_when_current=ELIG_ELIGIBLE,
        eligible_actions=("review_product_journey",),
        forbidden_actions=(
            "lower_the_price",
            "claim_price_is_the_cause",
            "guarantee_conversion_lift",
        ),
        minimum_confidence="from_knowledge",
        freshness_days=7,
        contradiction_policy="abstain_if_prohibited_missing",
        abstention_policy="truthful_abstain",
        routing_eligibility=False,
    ),
    _policy(
        knowledge_type=KT_WA_RETURN,
        guidance_key=KEY_REVIEW_WA_RETURN,
        merchant_objective=(
            "Review the customer journey after WhatsApp engagement."
        ),
        eligibility_when_current=ELIG_ELIGIBLE,
        eligible_actions=("review_post_whatsapp_journey",),
        forbidden_actions=(
            "claim_whatsapp_ineffective",
            "stop_whatsapp_recovery",
            "claim_whatsapp_caused_return",
        ),
        minimum_confidence="from_knowledge",
        freshness_days=7,
        contradiction_policy="abstain_if_prohibited_missing",
        abstention_policy="truthful_abstain",
        routing_eligibility=False,
    ),
    _policy(
        knowledge_type=KT_TRAFFIC_GAP,
        guidance_key=KEY_INVESTIGATE_CONVERSION,
        merchant_objective="Investigate conversion bottlenecks.",
        eligibility_when_current=ELIG_ELIGIBLE,
        eligible_actions=("investigate_conversion_path",),
        forbidden_actions=(
            "increase_advertising",
            "claim_traffic_quality_is_the_cause",
        ),
        minimum_confidence="from_knowledge",
        freshness_days=7,
        contradiction_policy="abstain_if_prohibited_missing",
        abstention_policy="truthful_abstain",
        routing_eligibility=False,
    ),
    _policy(
        knowledge_type=KT_REPEATED_INTEREST,
        guidance_key=KEY_REVIEW_REPEATED,
        merchant_objective="Review unresolved customer hesitation.",
        eligibility_when_current=ELIG_ELIGIBLE,
        eligible_actions=("review_unresolved_hesitation",),
        forbidden_actions=(
            "claim_root_cause_known",
            "force_discount_campaign",
        ),
        minimum_confidence="from_knowledge",
        freshness_days=7,
        contradiction_policy="abstain_if_prohibited_missing",
        abstention_policy="truthful_abstain",
        routing_eligibility=False,
    ),
    _policy(
        knowledge_type=KT_RECOVERY_INFLUENCE,
        guidance_key=KEY_PRESERVE_INFLUENCE,
        merchant_objective=(
            "Review recovery influence classifications without collapsing "
            "Confirmed Recovery, High Confidence, Possible Influence, or "
            "Unattributed Purchase."
        ),
        eligibility_when_current=ELIG_OBSERVE_ONLY,
        eligible_actions=("review_attribution_boundaries",),
        forbidden_actions=(
            "collapse_influence_into_recovered_revenue",
            "claim_roi_from_possible_influence",
        ),
        minimum_confidence="from_knowledge",
        freshness_days=7,
        contradiction_policy="preserve_all_classes",
        abstention_policy="observe_without_action_prescription",
        routing_eligibility=False,
    ),
    _policy(
        knowledge_type=KT_EVIDENCE_GAP,
        guidance_key=KEY_COLLECT_EVIDENCE,
        merchant_objective=(
            "Collect additional evidence before changing strategy."
        ),
        eligibility_when_current=ELIG_INSUFFICIENT,
        eligible_actions=("collect_additional_evidence",),
        forbidden_actions=(
            "change_strategy_on_insufficient_evidence",
            "invent_commercial_conclusion",
        ),
        minimum_confidence="any",
        freshness_days=7,
        contradiction_policy="prefer_gap_over_conclusion",
        abstention_policy="gap_is_valid_guidance",
        routing_eligibility=False,
    ),
    _policy(
        knowledge_type=KT_EVIDENCE_CONFLICT,
        guidance_key=KEY_DELAY_CONFLICT,
        merchant_objective=(
            "Delay operational decisions until evidence becomes clearer."
        ),
        eligibility_when_current=ELIG_CONFLICTING,
        eligible_actions=("delay_operational_decision",),
        forbidden_actions=(
            "pick_one_explanation_arbitrarily",
            "force_commercial_conclusion",
        ),
        minimum_confidence="any",
        freshness_days=7,
        contradiction_policy="do_not_resolve_arbitrarily",
        abstention_policy="conflict_is_valid_guidance",
        routing_eligibility=False,
    ),
)


_BY_KTYPE: dict[str, dict[str, Any]] = {
    str(p["knowledge_type"]): p for p in GUIDANCE_INTAKE_POLICIES_V1
}


def intake_policy_for_knowledge_type_v1(
    knowledge_type: str,
) -> Optional[dict[str, Any]]:
    return _BY_KTYPE.get(str(knowledge_type or ""))


def list_active_guidance_keys_v1() -> list[str]:
    keys = sorted(
        {
            str(p["guidance_key"])
            for p in GUIDANCE_INTAKE_POLICIES_V1
            if p.get("active") and p.get("guidance_key") in GUIDANCE_KEYS
        }
        | {KEY_NO_GUIDANCE}
    )
    return keys


def registry_is_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not GUIDANCE_INTAKE_POLICIES_V1:
        errors.append("empty_registry")
    seen: set[str] = set()
    for p in GUIDANCE_INTAKE_POLICIES_V1:
        kt = str(p.get("knowledge_type") or "")
        gk = str(p.get("guidance_key") or "")
        if not kt:
            errors.append("missing_knowledge_type")
        if kt in seen:
            errors.append(f"duplicate_knowledge_type:{kt}")
        seen.add(kt)
        if gk not in GUIDANCE_KEYS:
            errors.append(f"unknown_guidance_key:{gk}")
        if not str(p.get("merchant_objective") or "").strip():
            errors.append(f"missing_objective:{kt}")
        if not list(p.get("forbidden_actions") or []):
            errors.append(f"missing_forbidden:{kt}")
        if str(p.get("registry_version") or "") != REGISTRY_VERSION_V1:
            errors.append(f"bad_registry_version:{kt}")
    return (not errors), errors


__all__ = [
    "GUIDANCE_INTAKE_POLICIES_V1",
    "intake_policy_for_knowledge_type_v1",
    "list_active_guidance_keys_v1",
    "registry_is_valid_v1",
]
