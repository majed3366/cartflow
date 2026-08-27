# -*- coding: utf-8 -*-
"""Per-cycle snapshot byte budget (in addition to per-record JSON caps)."""
from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

ENV_CYCLE_BUDGET = "CARTFLOW_DASHBOARD_SNAPSHOT_CYCLE_BYTE_BUDGET"
_DEFAULT_CYCLE_BUDGET = 1_500_000
_MIN_CYCLE_BUDGET = 50_000
_MAX_CYCLE_BUDGET = 8_000_000


class SnapshotCycleBudgetExceeded(RuntimeError):
    """Tick aborted after the total-per-cycle byte budget was reached."""


def snapshot_cycle_byte_budget() -> int:
    raw = (os.getenv(ENV_CYCLE_BUDGET) or "").strip()
    try:
        v = int(raw or _DEFAULT_CYCLE_BUDGET)
    except (TypeError, ValueError):
        v = _DEFAULT_CYCLE_BUDGET
    return max(_MIN_CYCLE_BUDGET, min(_MAX_CYCLE_BUDGET, v))


_active: ContextVar["SnapshotCycleBudget | None"] = ContextVar(
    "snapshot_cycle_budget", default=None
)


@contextmanager
def using_cycle_budget(budget: "SnapshotCycleBudget") -> Iterator["SnapshotCycleBudget"]:
    token = _active.set(budget)
    try:
        yield budget
    finally:
        _active.reset(token)


def current_cycle_budget() -> "SnapshotCycleBudget | None":
    return _active.get()


class SnapshotCycleBudget:
    def __init__(self, limit_bytes: int | None = None) -> None:
        self.limit_bytes = int(limit_bytes if limit_bytes is not None else snapshot_cycle_byte_budget())
        self.used_bytes = 0
        self.record_count = 0
        self.aborted = False

    def add(self, nbytes: int) -> None:
        n = max(0, int(nbytes))
        if self.used_bytes + n > self.limit_bytes:
            self.aborted = True
            raise SnapshotCycleBudgetExceeded(
                f"snapshot cycle byte budget reached used={self.used_bytes} limit={self.limit_bytes}"
            )
        self.used_bytes += n
        self.record_count += 1

    def metrics(self) -> dict[str, Any]:
        return {
            "cycle_bytes": self.used_bytes,
            "cycle_records": self.record_count,
            "cycle_byte_budget": self.limit_bytes,
            "cycle_aborted": self.aborted,
        }


__all__ = [
    "ENV_CYCLE_BUDGET",
    "SnapshotCycleBudget",
    "SnapshotCycleBudgetExceeded",
    "current_cycle_budget",
    "snapshot_cycle_byte_budget",
    "using_cycle_budget",
]
