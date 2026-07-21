# -*- coding: utf-8 -*-
"""Merchant Presentation Foundation V1 — presentation rule registry."""
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
    ROUTE_BLOCKED,
    ROUTE_DEFERRED,
    ROUTE_ELIGIBLE,
    SCOPE_FULL,
    SCOPE_INTERNAL,
    SCOPE_OPERATIONAL,
    SCOPE_SUMMARY,
    SURFACE_CARTS,
    SURFACE_DECISION,
    SURFACE_HOME,
)
from services.product_data.merchant_presentation_types_v1 import (
    AFFORDANCE_INSPECT,
    AFFORDANCE_NAVIGATE,
    AFFORDANCE_NONE,
    AFFORDANCE_REVIEW,
    PRESENTATION_REGISTRY_VERSION_V1,
    STATE_BLOCKED,
    STATE_DEFERRED,
    STATE_INSUFFICIENT,
    STATE_MONITORING,
    STATE_READY,
    TYPE_ABSTENTION,
    TYPE_DECISION_PROMPT,
    TYPE_EVIDENCE_GAP,
    TYPE_EXECUTIVE_SUMMARY,
    TYPE_MONITORING,
    TYPE_OPERATIONAL_NOTICE,
)


def _rule(
    *,
    key: str,
    surfaces: tuple[str, ...],
    scopes: tuple[str, ...],
    roles: tuple[str, ...],
    guidance_keys: tuple[str, ...],
    subjects: tuple[str, ...],
    route_statuses: tuple[str, ...],
    presentation_type: str,
    template_key: str,
    affordance: str,
    presentation_state: str,
    slots: tuple[str, ...],
    priority: int,
    version: str,
) -> dict[str, Any]:
    return {
        "presentation_rule_key": key,
        "accepted_surface_keys": list(surfaces),
        "accepted_route_scopes": list(scopes),
        "accepted_route_roles": list(roles),
        "accepted_guidance_keys": list(guidance_keys),
        "accepted_subject_types": list(subjects),
        "accepted_route_statuses": list(route_statuses),
        "presentation_type": presentation_type,
        "template_key": template_key,
        "action_affordance": affordance,
        "presentation_state": presentation_state,
        "permitted_content_slots": list(slots),
        "prohibited_claims": [
            "Do not claim a specific root cause.",
            "Do not recommend price, discount, or campaign changes.",
        ],
        "fallback_behavior": "failed_no_match",
        "validity_behavior": "follow_route_valid_until",
        "rule_priority": priority,
        "rule_version": version,
        "registry_version": PRESENTATION_REGISTRY_VERSION_V1,
        "active": True,
    }


_SLOTS_FULL = (
    "headline",
    "primary_statement",
    "supporting_statement",
    "known_facts",
    "unknown_facts",
    "evidence_state",
    "merchant_relevance",
    "action_affordance",
    "action_label_key",
    "disclaimer_key",
    "status_label_key",
)
_SLOTS_SUMMARY = (
    "headline",
    "primary_statement",
    "supporting_statement",
    "evidence_state",
    "merchant_relevance",
    "action_affordance",
    "status_label_key",
)

PRESENTATION_RULES_V1: list[dict[str, Any]] = [
    _rule(
        key="pres_home_investigate",
        surfaces=(SURFACE_HOME,),
        scopes=(SCOPE_SUMMARY,),
        roles=(ROLE_AWARENESS,),
        guidance_keys=(KEY_INVESTIGATE_CONVERSION,),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_ELIGIBLE,),
        presentation_type=TYPE_EXECUTIVE_SUMMARY,
        template_key="tpl_exec_investigate_v1",
        affordance=AFFORDANCE_NAVIGATE,
        presentation_state=STATE_READY,
        slots=_SLOTS_SUMMARY,
        priority=10,
        version="mpres_home_investigate_v1",
    ),
    _rule(
        key="pres_decision_investigate",
        surfaces=(SURFACE_DECISION,),
        scopes=(SCOPE_FULL,),
        roles=(ROLE_INVESTIGATION, ROLE_DECISION),
        guidance_keys=(KEY_INVESTIGATE_CONVERSION,),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_ELIGIBLE,),
        presentation_type=TYPE_DECISION_PROMPT,
        template_key="tpl_decision_investigate_v1",
        affordance=AFFORDANCE_REVIEW,
        presentation_state=STATE_READY,
        slots=_SLOTS_FULL,
        priority=10,
        version="mpres_decision_investigate_v1",
    ),
    _rule(
        key="pres_carts_investigate",
        surfaces=(SURFACE_CARTS,),
        scopes=(SCOPE_OPERATIONAL,),
        roles=(ROLE_OPERATIONAL,),
        guidance_keys=(KEY_INVESTIGATE_CONVERSION,),
        subjects=("product", "cart"),
        route_statuses=(ROUTE_ELIGIBLE,),
        presentation_type=TYPE_OPERATIONAL_NOTICE,
        template_key="tpl_ops_investigate_v1",
        affordance=AFFORDANCE_INSPECT,
        presentation_state=STATE_READY,
        slots=_SLOTS_FULL,
        priority=10,
        version="mpres_carts_investigate_v1",
    ),
    _rule(
        key="pres_home_monitor",
        surfaces=(SURFACE_HOME,),
        scopes=(SCOPE_SUMMARY,),
        roles=(ROLE_AWARENESS,),
        guidance_keys=(KEY_MONITOR_NEW, KEY_CONTINUE_OBSERVING),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_ELIGIBLE,),
        presentation_type=TYPE_MONITORING,
        template_key="tpl_monitor_v1",
        affordance=AFFORDANCE_NONE,
        presentation_state=STATE_MONITORING,
        slots=_SLOTS_SUMMARY,
        priority=20,
        version="mpres_home_monitor_v1",
    ),
    _rule(
        key="pres_decision_monitor",
        surfaces=(SURFACE_DECISION,),
        scopes=(SCOPE_FULL,),
        roles=(ROLE_DECISION, ROLE_AWARENESS),
        guidance_keys=(KEY_MONITOR_NEW, KEY_CONTINUE_OBSERVING),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_ELIGIBLE,),
        presentation_type=TYPE_MONITORING,
        template_key="tpl_monitor_v1",
        affordance=AFFORDANCE_REVIEW,
        presentation_state=STATE_MONITORING,
        slots=_SLOTS_FULL,
        priority=20,
        version="mpres_decision_monitor_v1",
    ),
    _rule(
        key="pres_gap",
        surfaces=(SURFACE_HOME, SURFACE_DECISION),
        scopes=(SCOPE_SUMMARY, SCOPE_FULL),
        roles=(ROLE_AWARENESS, ROLE_DECISION),
        guidance_keys=(KEY_VERIFY_GAP,),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_ELIGIBLE,),
        presentation_type=TYPE_EVIDENCE_GAP,
        template_key="tpl_gap_v1",
        affordance=AFFORDANCE_REVIEW,
        presentation_state=STATE_READY,
        slots=_SLOTS_FULL,
        priority=15,
        version="mpres_gap_v1",
    ),
    _rule(
        key="pres_carts_review_cart",
        surfaces=(SURFACE_CARTS,),
        scopes=(SCOPE_OPERATIONAL,),
        roles=(ROLE_OPERATIONAL,),
        guidance_keys=(KEY_REVIEW_CART, KEY_REVIEW_PRODUCT),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_ELIGIBLE,),
        presentation_type=TYPE_OPERATIONAL_NOTICE,
        template_key="tpl_review_cart_ops_v1",
        affordance=AFFORDANCE_INSPECT,
        presentation_state=STATE_READY,
        slots=_SLOTS_FULL,
        priority=15,
        version="mpres_carts_review_v1",
    ),
    _rule(
        key="pres_home_continue",
        surfaces=(SURFACE_HOME, SURFACE_DECISION),
        scopes=(SCOPE_SUMMARY, SCOPE_FULL),
        roles=(ROLE_AWARENESS, ROLE_DECISION),
        guidance_keys=(KEY_CONTINUE_OBSERVING,),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_ELIGIBLE,),
        presentation_type=TYPE_MONITORING,
        template_key="tpl_continue_v1",
        affordance=AFFORDANCE_NONE,
        presentation_state=STATE_MONITORING,
        slots=_SLOTS_SUMMARY,
        priority=25,
        version="mpres_continue_v1",
    ),
    _rule(
        key="pres_blocked_abstain",
        surfaces=(SURFACE_HOME, SURFACE_DECISION),
        scopes=(SCOPE_INTERNAL, SCOPE_SUMMARY, SCOPE_FULL),
        roles=(ROLE_SUPPRESSED, ROLE_AWARENESS, ROLE_DECISION),
        guidance_keys=(KEY_NO_GUIDANCE,),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_BLOCKED,),
        presentation_type=TYPE_ABSTENTION,
        template_key="tpl_abstain_v1",
        affordance=AFFORDANCE_NONE,
        presentation_state=STATE_INSUFFICIENT,
        slots=_SLOTS_SUMMARY,
        priority=100,
        version="mpres_abstain_v1",
    ),
    _rule(
        key="pres_deferred",
        surfaces=(SURFACE_HOME, SURFACE_DECISION),
        scopes=(SCOPE_SUMMARY, SCOPE_FULL),
        roles=(ROLE_AWARENESS, ROLE_DECISION),
        guidance_keys=(KEY_DEFER,),
        subjects=("store", "product", "cart"),
        route_statuses=(ROUTE_DEFERRED, ROUTE_ELIGIBLE),
        presentation_type=TYPE_MONITORING,
        template_key="tpl_defer_v1",
        affordance=AFFORDANCE_NONE,
        presentation_state=STATE_DEFERRED,
        slots=_SLOTS_SUMMARY,
        priority=30,
        version="mpres_defer_v1",
    ),
]


def matching_presentation_rules_v1(route: dict[str, Any]) -> list[dict[str, Any]]:
    surface = str(route.get("surface_key") or "")
    scope = str(route.get("route_scope") or "")
    role = str(route.get("route_role") or "")
    gkey = str(route.get("guidance_key") or "")
    subject = str(route.get("subject_type") or "")
    status = str(route.get("route_status") or "")
    matches: list[dict[str, Any]] = []
    for rule in PRESENTATION_RULES_V1:
        if not rule.get("active"):
            continue
        if surface not in (rule.get("accepted_surface_keys") or []):
            continue
        if scope not in (rule.get("accepted_route_scopes") or []):
            continue
        if role not in (rule.get("accepted_route_roles") or []):
            continue
        if gkey not in (rule.get("accepted_guidance_keys") or []):
            continue
        subjects = rule.get("accepted_subject_types") or []
        if subjects and subject not in subjects:
            continue
        if status not in (rule.get("accepted_route_statuses") or []):
            continue
        matches.append(rule)
    matches.sort(key=lambda r: int(r.get("rule_priority") or 100))
    return matches


def presentation_registry_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not PRESENTATION_RULES_V1:
        errors.append("empty_presentation_registry")
    keys = set()
    for rule in PRESENTATION_RULES_V1:
        rk = str(rule.get("presentation_rule_key") or "")
        if not rk:
            errors.append("missing_rule_key")
            continue
        if rk in keys:
            errors.append(f"duplicate:{rk}")
        keys.add(rk)
        for banned in ("show_on_home", "home_card_title", "home_guidance_color"):
            if banned in rule:
                errors.append(f"home_field:{banned}")
    return (len(errors) == 0, errors)


__all__ = [
    "PRESENTATION_RULES_V1",
    "matching_presentation_rules_v1",
    "presentation_registry_valid_v1",
]
