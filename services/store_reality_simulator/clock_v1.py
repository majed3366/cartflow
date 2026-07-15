# -*- coding: utf-8 -*-
"""
Simulation Clock — platform time abstraction (Phase 2).

Production → SystemClock
Simulation → SimulationClock

Services participating in simulation must use utc_now() / get_clock().
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional, Protocol, runtime_checkable


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Wall-clock UTC — production default."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class SimulationClock:
    """Deterministic injectable clock — historical simulation time."""

    def __init__(self, start: datetime) -> None:
        self._current = _ensure_utc(start)

    def now(self) -> datetime:
        return self._current

    def current_day(self) -> date:
        return self._current.date()

    def set_now(self, when: datetime) -> datetime:
        self._current = _ensure_utc(when)
        return self._current

    def advance(self, delta: timedelta) -> datetime:
        self._current = self._current + delta
        return self._current

    def advance_days(self, days: int) -> datetime:
        return self.advance(timedelta(days=int(days)))

    def advance_to(self, when: datetime) -> datetime:
        target = _ensure_utc(when)
        if target < self._current:
            raise ValueError("simulation_clock_cannot_move_backward")
        self._current = target
        return self._current


_SYSTEM_CLOCK = SystemClock()
_active_clock: ContextVar[Clock] = ContextVar(
    "store_reality_simulator_clock", default=_SYSTEM_CLOCK
)


def get_clock() -> Clock:
    return _active_clock.get()


def utc_now() -> datetime:
    """Platform-facing now() — SystemClock or SimulationClock."""
    return get_clock().now()


def set_clock(clock: Clock) -> Token:
    return _active_clock.set(clock)


def reset_token(token: Token) -> None:
    _active_clock.reset(token)


def reset_clock_to_system() -> None:
    _active_clock.set(_SYSTEM_CLOCK)


def is_simulation_clock_active() -> bool:
    return isinstance(get_clock(), SimulationClock)


def get_simulation_clock() -> Optional[SimulationClock]:
    clock = get_clock()
    return clock if isinstance(clock, SimulationClock) else None


# Modules whose `_utc_now` is patched for the duration of simulation_scope.
# Avoids permanent edits to unrelated WIP in those files; platform believes
# SimulationClock while the scope is active.
_CLOCK_PATCH_MODULES: tuple[str, ...] = (
    "services.recovery_truth_timeline_v1",
    "services.customer_movement_snapshot_v1",
    "services.cartflow_purchase_truth",
    "services.lifecycle_closure_records_v1",
    "services.recovery_restart_survival",
    "services.purchase_truth",
)


def install_simulation_clock_patches() -> dict[str, Any]:
    """Replace participating modules' `_utc_now` with SimulationClock-aware utc_now."""
    import importlib

    originals: dict[str, Any] = {}
    for name in _CLOCK_PATCH_MODULES:
        try:
            mod = importlib.import_module(name)
        except Exception:  # noqa: BLE001
            continue
        if not hasattr(mod, "_utc_now"):
            continue
        originals[name] = mod._utc_now
        mod._utc_now = utc_now  # type: ignore[attr-defined]
    return originals


def restore_simulation_clock_patches(originals: dict[str, Any]) -> None:
    import importlib

    for name, fn in (originals or {}).items():
        try:
            mod = importlib.import_module(name)
            mod._utc_now = fn  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            continue
