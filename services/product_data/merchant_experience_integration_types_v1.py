# -*- coding: utf-8 -*-
"""Merchant Experience Integration Foundation V1 — constants."""
from __future__ import annotations

MEIF_VERSION_V1 = "meif_v1"
MEIF_GENERATION_VERSION_V1 = "meif_v1_gen"
INTEGRATION_MAP_VERSION_V1 = "meif_map_v1"

PAGE_HOME = "home"
PAGE_DECISION = "decision_workspace"
PAGE_CARTS = "carts"
PAGE_COMMUNICATION = "communication"
PAGE_SETTINGS = "settings"

PAGES_V1 = frozenset(
    {PAGE_HOME, PAGE_DECISION, PAGE_CARTS, PAGE_COMMUNICATION, PAGE_SETTINGS}
)

# Merchant questions (canonical).
QUESTION_HOME = "What should I know about my store right now?"
QUESTION_DECISION = "Why is this happening, and what should I review?"
QUESTION_CARTS = "What is happening in carts, and what needs attention?"
QUESTION_COMMUNICATION = "What happened in communication, and what needs follow-up?"
QUESTION_SETTINGS = "How do I control platform behavior and configuration?"

__all__ = [
    "MEIF_VERSION_V1",
    "MEIF_GENERATION_VERSION_V1",
    "INTEGRATION_MAP_VERSION_V1",
    "PAGE_HOME",
    "PAGE_DECISION",
    "PAGE_CARTS",
    "PAGE_COMMUNICATION",
    "PAGE_SETTINGS",
    "PAGES_V1",
    "QUESTION_HOME",
    "QUESTION_DECISION",
    "QUESTION_CARTS",
    "QUESTION_COMMUNICATION",
    "QUESTION_SETTINGS",
]
