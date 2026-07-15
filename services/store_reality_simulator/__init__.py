# -*- coding: utf-8 -*-
"""
Store Reality Simulator V1 — Phase 2 core infrastructure.

Exercises the real platform. Does not inject derived truth.
Phase 2: clock, run registry, accounting, checkpoints, identity,
safe delivery adapter, cleanup — no event generation.
"""
from __future__ import annotations

from services.store_reality_simulator.clock_v1 import (
    SimulationClock,
    SystemClock,
    get_clock,
    reset_clock_to_system,
    utc_now,
)
from services.store_reality_simulator.context_v1 import (
    SimulationContext,
    get_simulation_context,
    is_simulation_active,
    simulation_scope,
)

__all__ = [
    "SimulationClock",
    "SystemClock",
    "SimulationContext",
    "get_clock",
    "get_simulation_context",
    "is_simulation_active",
    "reset_clock_to_system",
    "simulation_scope",
    "utc_now",
]
