# -*- coding: utf-8 -*-
"""TABF V1 — temporal model constants."""
from __future__ import annotations

TABF_VERSION_V1 = "tabf_v1"
TABF_GENERATION_VERSION_V1 = "tabf_v1_gen"
TABF_REGISTRY_VERSION_V1 = "tabf_reg_v1"

# Canonical clocks — every layer must declare which it consumes.
CLOCK_EVENT = "event_time"
CLOCK_PROCESSING = "processing_time"
CLOCK_OBSERVATION = "observation_time"
CLOCK_DISPLAY = "display_time"
CLOCK_REPLAY = "replay_time"

CANONICAL_CLOCKS_V1 = frozenset(
    {
        CLOCK_EVENT,
        CLOCK_PROCESSING,
        CLOCK_OBSERVATION,
        CLOCK_DISPLAY,
        CLOCK_REPLAY,
    }
)

BINDING_BOUND = "bound"
BINDING_PARTIAL = "partial"
BINDING_UNBOUND = "unbound"
BINDING_LEGACY = "legacy_wall_clock"

__all__ = [
    "TABF_VERSION_V1",
    "TABF_GENERATION_VERSION_V1",
    "TABF_REGISTRY_VERSION_V1",
    "CLOCK_EVENT",
    "CLOCK_PROCESSING",
    "CLOCK_OBSERVATION",
    "CLOCK_DISPLAY",
    "CLOCK_REPLAY",
    "CANONICAL_CLOCKS_V1",
    "BINDING_BOUND",
    "BINDING_PARTIAL",
    "BINDING_UNBOUND",
    "BINDING_LEGACY",
]
