# -*- coding: utf-8 -*-
"""
Guidance Routing Foundation V1 — canonical routing rules registry.

Single source of truth for guidance→surface eligibility.
"""
from __future__ import annotations

from typing import Any

from services.product_data.commercial_guidance_types_v1 import (
    KEY_CONTINUE_OBSERVING,
    KEY_DEFER,
    KEY_INVESTIGATE_CONVERSION,
    KEY_MONITOR_NEW,
    KEY_NO_GUIDANCE,
    KEY_REVIEW_CART,
    KEY_REVIEW_PRODUCT,
    KEY_VERIFY_GAP,
)
from services.product_data.guidance_routing_types_v1 import (
    ROLE_AWARENESS,
    ROLE_DECISION,
    ROLE_INVESTIGATION,
    ROLE_OPERATIONAL,
    ROLE_SUPPRESSED,
    ROUTING_REGISTRY_VERSION_V1,
    SCOPE_FULL,
    SCOPE_INTERNAL,
    SCOPE_OPERATIONAL,
    SCOPE_SUMMARY,
    SURFACE_CARTS,
    SURFACE_DECISION,
    SURFACE_HOME,
)


def _rule(
    *,
    rule_key: str,
    guidance_keys: tuple[str, ...],
    guidance_statuses: tuple[str, ...],
    subject_types: tuple[str, ...],
    surface: str,
    route_scope: str,
    route_role: str,
    requires_cart_related: bool,
    priority: int,
    rule_version: str,
    active: bool = True,
) -> dict[str, Any]:
    return {
        "rule_key": rule_key,
        "accepted_guidance_keys": list(guidance_keys),
        "accepted_guidance_statuses": list(guidance_statuses),
        "accepted_subject_types": list(subject_types),
        "eligible_surface": surface,
        "route_scope": route_scope,
        "route_role": route_role,
        "requires_cart_related": requires_cart_related,
        "blocking_conditions": [],
        "expiry_behavior": "follow_guidance_valid_until",
        "rule_priority": priority,
        "rule_version": rule_version,
        "registry_version": ROUTING_REGISTRY_VERSION_V1,
        "active": active,
    }


# Positive eligibility rules (first matching rule for a surface wins among eligibles).
# Surfaces without a matching rule are marked ineligible/blocked by evaluator defaults.
ROUTING_RULES_V1: list[dict[str, Any]] = [
    _rule(
        rule_key="monitor_home_summary",
        guidance_keys=(KEY_MONITOR_NEW,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_HOME,
        route_scope=SCOPE_SUMMARY,
        route_role=ROLE_AWARENESS,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_monitor_home_v1",
    ),
    _rule(
        rule_key="monitor_decision_full",
        guidance_keys=(KEY_MONITOR_NEW,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_DECISION,
        route_scope=SCOPE_FULL,
        route_role=ROLE_DECISION,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_monitor_decision_v1",
    ),
    _rule(
        rule_key="monitor_carts_operational",
        guidance_keys=(KEY_MONITOR_NEW,),
        guidance_statuses=("active",),
        subject_types=("product", "cart"),
        surface=SURFACE_CARTS,
        route_scope=SCOPE_OPERATIONAL,
        route_role=ROLE_OPERATIONAL,
        requires_cart_related=True,
        priority=20,
        rule_version="grule_monitor_carts_v1",
    ),
    _rule(
        rule_key="investigate_home_summary",
        guidance_keys=(KEY_INVESTIGATE_CONVERSION,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_HOME,
        route_scope=SCOPE_SUMMARY,
        route_role=ROLE_AWARENESS,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_investigate_home_v1",
    ),
    _rule(
        rule_key="investigate_decision_full",
        guidance_keys=(KEY_INVESTIGATE_CONVERSION,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_DECISION,
        route_scope=SCOPE_FULL,
        route_role=ROLE_INVESTIGATION,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_investigate_decision_v1",
    ),
    _rule(
        rule_key="investigate_carts_operational",
        guidance_keys=(KEY_INVESTIGATE_CONVERSION,),
        guidance_statuses=("active",),
        subject_types=("product", "cart"),
        surface=SURFACE_CARTS,
        route_scope=SCOPE_OPERATIONAL,
        route_role=ROLE_OPERATIONAL,
        requires_cart_related=True,
        priority=15,
        rule_version="grule_investigate_carts_v1",
    ),
    _rule(
        rule_key="review_cart_home",
        guidance_keys=(KEY_REVIEW_CART,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_HOME,
        route_scope=SCOPE_SUMMARY,
        route_role=ROLE_AWARENESS,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_review_cart_home_v1",
    ),
    _rule(
        rule_key="review_cart_decision",
        guidance_keys=(KEY_REVIEW_CART,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_DECISION,
        route_scope=SCOPE_FULL,
        route_role=ROLE_DECISION,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_review_cart_decision_v1",
    ),
    _rule(
        rule_key="review_cart_carts",
        guidance_keys=(KEY_REVIEW_CART,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_CARTS,
        route_scope=SCOPE_OPERATIONAL,
        route_role=ROLE_OPERATIONAL,
        requires_cart_related=False,
        priority=5,
        rule_version="grule_review_cart_carts_v1",
    ),
    _rule(
        rule_key="review_product_home",
        guidance_keys=(KEY_REVIEW_PRODUCT,),
        guidance_statuses=("active",),
        subject_types=("product",),
        surface=SURFACE_HOME,
        route_scope=SCOPE_SUMMARY,
        route_role=ROLE_AWARENESS,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_review_product_home_v1",
    ),
    _rule(
        rule_key="review_product_decision",
        guidance_keys=(KEY_REVIEW_PRODUCT,),
        guidance_statuses=("active",),
        subject_types=("product",),
        surface=SURFACE_DECISION,
        route_scope=SCOPE_FULL,
        route_role=ROLE_DECISION,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_review_product_decision_v1",
    ),
    _rule(
        rule_key="review_product_carts",
        guidance_keys=(KEY_REVIEW_PRODUCT,),
        guidance_statuses=("active",),
        subject_types=("product",),
        surface=SURFACE_CARTS,
        route_scope=SCOPE_OPERATIONAL,
        route_role=ROLE_OPERATIONAL,
        requires_cart_related=True,
        priority=15,
        rule_version="grule_review_product_carts_v1",
    ),
    _rule(
        rule_key="verify_gap_home",
        guidance_keys=(KEY_VERIFY_GAP,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_HOME,
        route_scope=SCOPE_SUMMARY,
        route_role=ROLE_AWARENESS,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_verify_gap_home_v1",
    ),
    _rule(
        rule_key="verify_gap_decision",
        guidance_keys=(KEY_VERIFY_GAP,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_DECISION,
        route_scope=SCOPE_FULL,
        route_role=ROLE_DECISION,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_verify_gap_decision_v1",
    ),
    _rule(
        rule_key="continue_home",
        guidance_keys=(KEY_CONTINUE_OBSERVING,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_HOME,
        route_scope=SCOPE_SUMMARY,
        route_role=ROLE_AWARENESS,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_continue_home_v1",
    ),
    _rule(
        rule_key="continue_decision",
        guidance_keys=(KEY_CONTINUE_OBSERVING,),
        guidance_statuses=("active",),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_DECISION,
        route_scope=SCOPE_FULL,
        route_role=ROLE_DECISION,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_continue_decision_v1",
    ),
    _rule(
        rule_key="defer_home",
        guidance_keys=(KEY_DEFER,),
        guidance_statuses=("deferred", "active"),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_HOME,
        route_scope=SCOPE_SUMMARY,
        route_role=ROLE_AWARENESS,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_defer_home_v1",
    ),
    _rule(
        rule_key="defer_decision",
        guidance_keys=(KEY_DEFER,),
        guidance_statuses=("deferred", "active"),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_DECISION,
        route_scope=SCOPE_FULL,
        route_role=ROLE_DECISION,
        requires_cart_related=False,
        priority=10,
        rule_version="grule_defer_decision_v1",
    ),
    _rule(
        rule_key="no_guidance_home_internal",
        guidance_keys=(KEY_NO_GUIDANCE,),
        guidance_statuses=("abstained", "active", "deferred"),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_HOME,
        route_scope=SCOPE_INTERNAL,
        route_role=ROLE_SUPPRESSED,
        requires_cart_related=False,
        priority=100,
        rule_version="grule_no_guidance_home_v1",
    ),
    _rule(
        rule_key="no_guidance_decision_internal",
        guidance_keys=(KEY_NO_GUIDANCE,),
        guidance_statuses=("abstained", "active", "deferred"),
        subject_types=("store", "product", "cart"),
        surface=SURFACE_DECISION,
        route_scope=SCOPE_INTERNAL,
        route_role=ROLE_SUPPRESSED,
        requires_cart_related=False,
        priority=100,
        rule_version="grule_no_guidance_decision_v1",
    ),
]


def matching_rules_for_surface_v1(
    *,
    guidance_key: str,
    guidance_status: str,
    subject_type: str,
    surface_key: str,
    cart_related: bool,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for rule in ROUTING_RULES_V1:
        if not rule.get("active"):
            continue
        if rule.get("eligible_surface") != surface_key:
            continue
        if guidance_key not in (rule.get("accepted_guidance_keys") or []):
            continue
        if guidance_status not in (rule.get("accepted_guidance_statuses") or []):
            continue
        accepted_subjects = rule.get("accepted_subject_types") or []
        if accepted_subjects and subject_type not in accepted_subjects:
            continue
        if rule.get("requires_cart_related") and not cart_related:
            continue
        matches.append(rule)
    matches.sort(key=lambda r: int(r.get("rule_priority") or 100))
    return matches


def routing_registry_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not ROUTING_RULES_V1:
        errors.append("empty_routing_registry")
    keys = set()
    for rule in ROUTING_RULES_V1:
        rk = str(rule.get("rule_key") or "")
        if not rk:
            errors.append("missing_rule_key")
            continue
        if rk in keys:
            errors.append(f"duplicate_rule_key:{rk}")
        keys.add(rk)
        if not rule.get("rule_version"):
            errors.append(f"missing_rule_version:{rk}")
    return (len(errors) == 0, errors)


__all__ = [
    "ROUTING_RULES_V1",
    "matching_rules_for_surface_v1",
    "routing_registry_valid_v1",
]
