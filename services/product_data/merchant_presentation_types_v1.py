# -*- coding: utf-8 -*-
"""Merchant Presentation Foundation V1 — catalog constants."""
from __future__ import annotations

PRESENTATION_VERSION_V1 = "mpf_v1"
GENERATION_VERSION_V1 = "mpf_v1_gen"
PRESENTATION_REGISTRY_VERSION_V1 = "mpres_v1"
TEMPLATE_REGISTRY_VERSION_V1 = "mtpl_v1"
SOURCE_CONTRACT_VERSION_V1 = "grf_v1_presentation_context"
LANGUAGE_CODE_V1 = "en"

TYPE_EXECUTIVE_SUMMARY = "executive_summary"
TYPE_DECISION_PROMPT = "decision_prompt"
TYPE_OPERATIONAL_NOTICE = "operational_notice"
TYPE_MONITORING = "monitoring_state"
TYPE_EVIDENCE_GAP = "evidence_gap_state"
TYPE_FOLLOW_UP = "follow_up_context"
TYPE_CONFIGURATION = "configuration_context"
TYPE_ABSTENTION = "abstention_state"

PRESENTATION_TYPES = frozenset(
    {
        TYPE_EXECUTIVE_SUMMARY,
        TYPE_DECISION_PROMPT,
        TYPE_OPERATIONAL_NOTICE,
        TYPE_MONITORING,
        TYPE_EVIDENCE_GAP,
        TYPE_FOLLOW_UP,
        TYPE_CONFIGURATION,
        TYPE_ABSTENTION,
    }
)

STATE_READY = "ready"
STATE_MONITORING = "monitoring"
STATE_INSUFFICIENT = "insufficient_evidence"
STATE_DEFERRED = "deferred"
STATE_BLOCKED = "blocked"
STATE_EXPIRED = "expired"
STATE_SUPERSEDED = "superseded"
STATE_FAILED = "failed"

PRESENTATION_STATES = frozenset(
    {
        STATE_READY,
        STATE_MONITORING,
        STATE_INSUFFICIENT,
        STATE_DEFERRED,
        STATE_BLOCKED,
        STATE_EXPIRED,
        STATE_SUPERSEDED,
        STATE_FAILED,
    }
)

AFFORDANCE_NONE = "none"
AFFORDANCE_NAVIGATE = "navigate"
AFFORDANCE_REVIEW = "review"
AFFORDANCE_INSPECT = "inspect"
AFFORDANCE_CONFIGURE = "configure"
AFFORDANCE_ACKNOWLEDGE = "acknowledge"

ACTION_AFFORDANCES = frozenset(
    {
        AFFORDANCE_NONE,
        AFFORDANCE_NAVIGATE,
        AFFORDANCE_REVIEW,
        AFFORDANCE_INSPECT,
        AFFORDANCE_CONFIGURE,
        AFFORDANCE_ACKNOWLEDGE,
    }
)

CONTENT_SLOTS = (
    "headline",
    "primary_statement",
    "supporting_statement",
    "known_facts",
    "unknown_facts",
    "evidence_state",
    "merchant_relevance",
    "action_label_key",
    "action_affordance",
    "disclaimer_key",
    "status_label_key",
)

__all__ = [
    "PRESENTATION_VERSION_V1",
    "GENERATION_VERSION_V1",
    "PRESENTATION_REGISTRY_VERSION_V1",
    "TEMPLATE_REGISTRY_VERSION_V1",
    "SOURCE_CONTRACT_VERSION_V1",
    "LANGUAGE_CODE_V1",
    "TYPE_EXECUTIVE_SUMMARY",
    "TYPE_DECISION_PROMPT",
    "TYPE_OPERATIONAL_NOTICE",
    "TYPE_MONITORING",
    "TYPE_EVIDENCE_GAP",
    "TYPE_FOLLOW_UP",
    "TYPE_CONFIGURATION",
    "TYPE_ABSTENTION",
    "PRESENTATION_TYPES",
    "STATE_READY",
    "STATE_MONITORING",
    "STATE_INSUFFICIENT",
    "STATE_DEFERRED",
    "STATE_BLOCKED",
    "STATE_EXPIRED",
    "STATE_SUPERSEDED",
    "STATE_FAILED",
    "PRESENTATION_STATES",
    "AFFORDANCE_NONE",
    "AFFORDANCE_NAVIGATE",
    "AFFORDANCE_REVIEW",
    "AFFORDANCE_INSPECT",
    "AFFORDANCE_CONFIGURE",
    "AFFORDANCE_ACKNOWLEDGE",
    "ACTION_AFFORDANCES",
    "CONTENT_SLOTS",
]
