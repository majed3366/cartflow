# -*- coding: utf-8 -*-
"""
Performance protection for Reality Engine batches — Phase 3.

Production architecture always wins: exceed thresholds → pause.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional


@dataclass
class PerformanceThresholds:
    pool_checked_out_max: int = 24
    pool_exhausted: bool = True  # pause if exhausted flag
    batch_wall_ms_max: float = 15000.0
    failure_rate_max: float = 0.35
    consecutive_failures_max: int = 8
    memory_mb_max: float = 0.0  # 0 = disabled


@dataclass
class PerformanceSnapshot:
    available: bool = True
    pool_checked_out: Optional[int] = None
    pool_exhausted: bool = False
    pool_impl: str = ""
    memory_mb: Optional[float] = None
    batch_wall_ms: float = 0.0
    failure_rate: float = 0.0
    consecutive_failures: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def capture_performance_snapshot(
    *,
    batch_wall_ms: float = 0.0,
    failure_rate: float = 0.0,
    consecutive_failures: int = 0,
) -> PerformanceSnapshot:
    snap = PerformanceSnapshot(
        batch_wall_ms=float(batch_wall_ms),
        failure_rate=float(failure_rate),
        consecutive_failures=int(consecutive_failures),
    )
    try:
        from services.db_pool_diagnostics import (
            build_db_pool_health_snapshot,
            pool_status_snapshot,
        )

        health = build_db_pool_health_snapshot()
        basic = pool_status_snapshot()
        snap.pool_impl = str(basic.get("pool_impl") or health.get("pool_class") or "")
        if health.get("available") is False and basic.get("pool_impl") in (
            "NullPool",
            "StaticPool",
            "SingletonThreadPool",
        ):
            # SQLite/test pools — do not false-pause
            snap.available = True
            snap.notes.append("pool_not_queuepool_skip_pressure")
        else:
            snap.available = True
            co = health.get("checked_out")
            if co is None:
                co = basic.get("checkedout")
            try:
                snap.pool_checked_out = int(co) if co is not None else None
            except (TypeError, ValueError):
                snap.pool_checked_out = None
            snap.pool_exhausted = bool(health.get("exhausted"))
    except Exception as exc:  # noqa: BLE001
        snap.notes.append(f"pool_probe_error:{str(exc)[:120]}")

    try:
        import resource  # type: ignore

        ru = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is KB on Linux, bytes on macOS — best-effort
        rss = float(getattr(ru, "ru_maxrss", 0) or 0)
        if rss > 10_000_000:
            snap.memory_mb = rss / (1024 * 1024)
        else:
            snap.memory_mb = rss / 1024.0
    except Exception:  # noqa: BLE001
        snap.memory_mb = None
        snap.notes.append("memory_probe_unavailable")

    return snap


def evaluate_stop_condition(
    snap: PerformanceSnapshot,
    thresholds: Optional[PerformanceThresholds] = None,
) -> Optional[str]:
    """Return pause reason or None if safe to continue."""
    th = thresholds or PerformanceThresholds()
    if snap.pool_exhausted and th.pool_exhausted:
        if "pool_not_queuepool_skip_pressure" not in (snap.notes or []):
            return "pool_exhausted"
    if (
        snap.pool_checked_out is not None
        and snap.pool_checked_out >= th.pool_checked_out_max
        and "pool_not_queuepool_skip_pressure" not in (snap.notes or [])
    ):
        return "pool_pressure"
    if snap.batch_wall_ms > th.batch_wall_ms_max:
        return "batch_latency"
    if snap.failure_rate > th.failure_rate_max and snap.consecutive_failures >= 3:
        return "failure_rate"
    if snap.consecutive_failures >= th.consecutive_failures_max:
        return "consecutive_failures"
    if (
        th.memory_mb_max > 0
        and snap.memory_mb is not None
        and snap.memory_mb > th.memory_mb_max
    ):
        return "memory_pressure"
    return None


class BatchTimer:
    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0


def sleep_between_batches(pause_ms: int, sleeper: Optional[Callable[[float], None]] = None) -> None:
    ms = max(0, int(pause_ms))
    if ms <= 0:
        return
    fn = sleeper or time.sleep
    fn(ms / 1000.0)
