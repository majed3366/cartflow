# -*- coding: utf-8 -*-
"""Clock providers — System / Fixed / Frozen / Simulation (WP-1)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from services.time_authority.contracts import ClockSourceKind, ensure_utc
from services.time_authority.exceptions import InvalidClockProvider


class SystemClockProvider:
    """Production wall-clock UTC — default source."""

    @property
    def source_id(self) -> str:
        return ClockSourceKind.SYSTEM.value

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedAsOfProvider:
    """Fixed as-of instant for historical / recovery replay contexts."""

    def __init__(self, as_of: datetime) -> None:
        self._as_of = ensure_utc(as_of)

    @property
    def source_id(self) -> str:
        return ClockSourceKind.FIXED_AS_OF.value

    def now(self) -> datetime:
        return self._as_of


class FrozenTestProvider:
    """Deterministic frozen clock for tests."""

    def __init__(self, when: datetime) -> None:
        self._when = ensure_utc(when)

    @property
    def source_id(self) -> str:
        return ClockSourceKind.FROZEN_TEST.value

    def now(self) -> datetime:
        return self._when

    def set_now(self, when: datetime) -> datetime:
        self._when = ensure_utc(when)
        return self._when


class SimulationClockProvider:
    """
    Simulation source placeholder (WP-1).

    Holds a mutable simulated instant. Full Reality Simulator bind is WP-10.
    """

    def __init__(self, start: datetime, *, run_id: str = "") -> None:
        self._current = ensure_utc(start)
        self._run_id = (run_id or "").strip()

    @property
    def source_id(self) -> str:
        return ClockSourceKind.SIMULATION.value

    @property
    def run_id(self) -> str:
        return self._run_id

    def now(self) -> datetime:
        return self._current

    def set_now(self, when: datetime) -> datetime:
        self._current = ensure_utc(when)
        return self._current

    def advance(self, *, seconds: float = 0) -> datetime:
        from datetime import timedelta

        self._current = self._current + timedelta(seconds=float(seconds))
        return self._current


def validate_provider(provider: object) -> None:
    """Ensure provider exposes source_id and now() → aware UTC datetime."""
    if provider is None:
        raise InvalidClockProvider("clock_provider_is_none")
    if not hasattr(provider, "source_id") or not hasattr(provider, "now"):
        raise InvalidClockProvider("clock_provider_missing_interface")
    try:
        sid = str(getattr(provider, "source_id"))
        if not sid:
            raise InvalidClockProvider("clock_provider_empty_source_id")
        n = provider.now()  # type: ignore[operator]
    except InvalidClockProvider:
        raise
    except Exception as exc:  # noqa: BLE001
        raise InvalidClockProvider(f"clock_provider_now_failed:{exc}") from exc
    if not isinstance(n, datetime):
        raise InvalidClockProvider("clock_provider_now_not_datetime")
    if n.tzinfo is None:
        raise InvalidClockProvider("clock_provider_now_naive")


_DEFAULT_SYSTEM: Optional[SystemClockProvider] = None


def default_system_provider() -> SystemClockProvider:
    global _DEFAULT_SYSTEM
    if _DEFAULT_SYSTEM is None:
        _DEFAULT_SYSTEM = SystemClockProvider()
    return _DEFAULT_SYSTEM
