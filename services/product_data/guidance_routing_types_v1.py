# -*- coding: utf-8 -*-
"""Guidance Routing Foundation V1 — catalog constants."""
from __future__ import annotations

ROUTING_VERSION_V1 = "grf_v1"
EVALUATOR_VERSION_V1 = "grf_v1_eval"
SURFACE_REGISTRY_VERSION_V1 = "gsurf_v1"
ROUTING_REGISTRY_VERSION_V1 = "grule_v1"
SOURCE_CONTRACT_VERSION_V1 = "cgf_v1_routing_context"

SURFACE_HOME = "home"
SURFACE_DECISION = "decision_workspace"
SURFACE_CARTS = "carts"
SURFACE_COMMUNICATION = "communication"
SURFACE_SETTINGS = "settings"

SURFACES_V1 = frozenset(
    {
        SURFACE_HOME,
        SURFACE_DECISION,
        SURFACE_CARTS,
        SURFACE_COMMUNICATION,
        SURFACE_SETTINGS,
    }
)

SCOPE_SUMMARY = "summary"
SCOPE_FULL = "full_context"
SCOPE_OPERATIONAL = "operational"
SCOPE_FOLLOW_UP = "follow_up"
SCOPE_CONTROL = "control"
SCOPE_INTERNAL = "internal_only"

ROUTE_SCOPES = frozenset(
    {
        SCOPE_SUMMARY,
        SCOPE_FULL,
        SCOPE_OPERATIONAL,
        SCOPE_FOLLOW_UP,
        SCOPE_CONTROL,
        SCOPE_INTERNAL,
    }
)

ROLE_AWARENESS = "awareness"
ROLE_INVESTIGATION = "investigation"
ROLE_DECISION = "decision_support"
ROLE_OPERATIONAL = "operational_attention"
ROLE_COMM_FOLLOWUP = "communication_followup"
ROLE_CONFIG = "configuration_context"
ROLE_SUPPRESSED = "suppressed"

ROUTE_ROLES = frozenset(
    {
        ROLE_AWARENESS,
        ROLE_INVESTIGATION,
        ROLE_DECISION,
        ROLE_OPERATIONAL,
        ROLE_COMM_FOLLOWUP,
        ROLE_CONFIG,
        ROLE_SUPPRESSED,
    }
)

ROUTE_ELIGIBLE = "eligible"
ROUTE_INELIGIBLE = "ineligible"
ROUTE_DEFERRED = "deferred"
ROUTE_BLOCKED = "blocked"
ROUTE_EXPIRED = "expired"
ROUTE_SUPERSEDED = "superseded"
ROUTE_FAILED = "failed"

ROUTE_STATUSES = frozenset(
    {
        ROUTE_ELIGIBLE,
        ROUTE_INELIGIBLE,
        ROUTE_DEFERRED,
        ROUTE_BLOCKED,
        ROUTE_EXPIRED,
        ROUTE_SUPERSEDED,
        ROUTE_FAILED,
    }
)

__all__ = [
    "ROUTING_VERSION_V1",
    "EVALUATOR_VERSION_V1",
    "SURFACE_REGISTRY_VERSION_V1",
    "ROUTING_REGISTRY_VERSION_V1",
    "SOURCE_CONTRACT_VERSION_V1",
    "SURFACE_HOME",
    "SURFACE_DECISION",
    "SURFACE_CARTS",
    "SURFACE_COMMUNICATION",
    "SURFACE_SETTINGS",
    "SURFACES_V1",
    "SCOPE_SUMMARY",
    "SCOPE_FULL",
    "SCOPE_OPERATIONAL",
    "SCOPE_FOLLOW_UP",
    "SCOPE_CONTROL",
    "SCOPE_INTERNAL",
    "ROUTE_SCOPES",
    "ROLE_AWARENESS",
    "ROLE_INVESTIGATION",
    "ROLE_DECISION",
    "ROLE_OPERATIONAL",
    "ROLE_COMM_FOLLOWUP",
    "ROLE_CONFIG",
    "ROLE_SUPPRESSED",
    "ROUTE_ROLES",
    "ROUTE_ELIGIBLE",
    "ROUTE_INELIGIBLE",
    "ROUTE_DEFERRED",
    "ROUTE_BLOCKED",
    "ROUTE_EXPIRED",
    "ROUTE_SUPERSEDED",
    "ROUTE_FAILED",
    "ROUTE_STATUSES",
]
