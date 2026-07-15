# -*- coding: utf-8 -*-
"""Active simulation context (contextvars) — Phase 2."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator, Optional

from services.store_reality_simulator.clock_v1 import (
    SimulationClock,
    install_simulation_clock_patches,
    reset_clock_to_system,
    restore_simulation_clock_patches,
    set_clock,
)
from services.store_reality_simulator.contracts_v1 import (
    DEMO_STORE_SLUG,
    assert_demo_store,
)


@dataclass
class SimulationContext:
    simulation_run_id: str
    store_slug: str = DEMO_STORE_SLUG
    seed: int = 0
    scenario_ids: list[str] = field(default_factory=list)
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        assert_demo_store(self.store_slug)
        self.simulation_run_id = str(self.simulation_run_id or "").strip()
        if not self.simulation_run_id:
            raise ValueError("simulation_run_id_required")


_active_context: ContextVar[Optional[SimulationContext]] = ContextVar(
    "store_reality_simulator_context", default=None
)


def get_simulation_context() -> Optional[SimulationContext]:
    return _active_context.get()


def is_simulation_active() -> bool:
    ctx = get_simulation_context()
    return bool(ctx is not None and ctx.active)


@contextmanager
def simulation_scope(
    *,
    simulation_run_id: str,
    clock: SimulationClock,
    seed: int = 0,
    scenario_ids: Optional[list[str]] = None,
    store_slug: str = DEMO_STORE_SLUG,
    metadata: Optional[dict[str, Any]] = None,
) -> Iterator[SimulationContext]:
    """
    Activate simulation clock + context for the duration of the block.
    Restores SystemClock and clears context on exit.
    """
    assert_demo_store(store_slug)
    ctx = SimulationContext(
        simulation_run_id=simulation_run_id,
        store_slug=store_slug,
        seed=int(seed),
        scenario_ids=list(scenario_ids or []),
        metadata=dict(metadata or {}),
    )
    token_ctx = _active_context.set(ctx)
    token_clock = set_clock(clock)
    patch_originals = install_simulation_clock_patches()
    try:
        yield ctx
    finally:
        from services.store_reality_simulator.clock_v1 import reset_token

        restore_simulation_clock_patches(patch_originals)
        reset_token(token_clock)
        _active_context.reset(token_ctx)
        # Ensure default is system if no nested scopes remain
        if get_simulation_context() is None:
            reset_clock_to_system()


def require_active_simulation() -> SimulationContext:
    ctx = get_simulation_context()
    if ctx is None or not ctx.active:
        raise RuntimeError("simulation_context_required")
    return ctx


def simulated_now_or_none() -> Optional[datetime]:
    if not is_simulation_active():
        return None
    from services.store_reality_simulator.clock_v1 import utc_now

    return utc_now()
