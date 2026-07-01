# -*- coding: utf-8 -*-
"""Async loop for dashboard snapshot builder (scheduler / background only)."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

_log = logging.getLogger(__name__)

_loop_task: Optional[asyncio.Task[None]] = None
_watchdog_task: Optional[asyncio.Task[None]] = None
_tick_lock = asyncio.Lock()
_DEFAULT_INTERVAL_SECONDS = 45.0
_WATCHDOG_INTERVAL_SECONDS = 90.0


def dashboard_snapshot_loop_interval_seconds() -> float:
    raw = (os.environ.get("CARTFLOW_DASHBOARD_SNAPSHOT_INTERVAL_SECONDS") or "").strip()
    try:
        v = float(raw or _DEFAULT_INTERVAL_SECONDS)
    except (TypeError, ValueError):
        v = _DEFAULT_INTERVAL_SECONDS
    return max(15.0, v)


def is_dashboard_snapshot_loop_running() -> bool:
    return _loop_task is not None and not _loop_task.done()


def get_dashboard_snapshot_loop_task_state() -> dict[str, bool]:
    task = _loop_task
    if task is None:
        return {
            "task_alive": False,
            "task_done": False,
            "task_cancelled": False,
        }
    return {
        "task_alive": not task.done(),
        "task_done": task.done(),
        "task_cancelled": task.cancelled(),
    }


def _loop_health_module() -> Any | None:
    try:
        import services.scheduler_snapshot_loop_health_v1 as mod  # noqa: PLC0415

        return mod
    except ImportError:
        return None


def _emit_loop(tag: str, **fields: Any) -> None:
    parts = [f"{k}={fields[k]}" for k in sorted(fields) if fields[k] is not None]
    suffix = f" {' '.join(parts)}" if parts else ""
    line = f"[DASHBOARD SNAPSHOT LOOP {tag}]{suffix}"
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        _log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _record_tick_outcome(result: dict[str, Any]) -> None:
    health = _loop_health_module()
    if health is None:
        return

    if result.get("error"):
        health.record_loop_tick_failure(error=str(result.get("error"))[:500])
        return
    if result.get("skipped"):
        reason = str(result.get("reason") or "skipped")
        if reason in ("builder_disabled", "tick_in_progress"):
            return
        health.record_loop_tick_failure(error=f"tick_skipped:{reason}")
        return
    errors = int(result.get("errors") or 0)
    if errors > 0:
        health.record_loop_tick_failure(
            error=f"builder_tick_errors:{errors} stores_built={result.get('stores_built')}"
        )
        return
    health.record_loop_tick_success(result=result)


def _maybe_restart_snapshot_loop(*, reason: str) -> None:
    from services.dashboard_snapshot_builder_v1 import dashboard_snapshot_builder_enabled  # noqa: PLC0415

    if not dashboard_snapshot_builder_enabled():
        return
    if is_dashboard_snapshot_loop_running():
        return
    _emit_loop("RESTART", reason=reason)
    start_dashboard_snapshot_builder_loop()


def _on_loop_task_done(task: asyncio.Task[None]) -> None:
    global _loop_task
    health = _loop_health_module()

    if task.cancelled():
        if health is not None:
            health.record_loop_task_exited(reason="cancelled")
        if _loop_task is task:
            _loop_task = None
        return
    exc = task.exception()
    if exc is not None:
        if health is not None:
            health.record_loop_task_exited(reason="exception", error=str(exc)[:500])
        _emit_loop("EXIT", reason="exception", detail=str(exc)[:200])
    else:
        if health is not None:
            health.record_loop_task_exited(reason="completed")
        _emit_loop("EXIT", reason="completed")
    if _loop_task is task:
        _loop_task = None
    _maybe_restart_snapshot_loop(reason="loop_task_exited")


async def run_dashboard_snapshot_loop_tick() -> dict[str, Any]:
    if _tick_lock.locked():
        return {"skipped": True, "reason": "tick_in_progress"}
    async with _tick_lock:
        from services.dashboard_snapshot_builder_v1 import (
            dashboard_snapshot_builder_enabled,
            run_dashboard_snapshot_builder_tick,
        )

        if not dashboard_snapshot_builder_enabled():
            return {"skipped": True, "reason": "builder_disabled"}
        health = _loop_health_module()
        if health is not None:
            health.record_loop_tick_started()
        try:
            result = await asyncio.to_thread(run_dashboard_snapshot_builder_tick)
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:500]
            _emit_loop("TICK ERROR", detail=err)
            _log.warning("dashboard snapshot builder tick failed: %s", exc, exc_info=True)
            out: dict[str, Any] = {"error": err, "skipped": False}
            _record_tick_outcome(out)
            return out
        _record_tick_outcome(result)
        return result


async def _dashboard_snapshot_loop_main() -> None:
    interval = dashboard_snapshot_loop_interval_seconds()
    health = _loop_health_module()
    if health is not None:
        health.record_loop_started(interval_seconds=interval)
    _emit_loop("STARTED", interval_s=interval)
    while True:
        try:
            await run_dashboard_snapshot_loop_tick()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _emit_loop("TICK ERROR", detail=str(exc)[:200])
            _log.warning("dashboard snapshot loop tick error: %s", exc, exc_info=True)
            health = _loop_health_module()
            if health is not None:
                try:
                    health.record_loop_tick_failure(error=str(exc)[:500])
                except Exception:  # noqa: BLE001
                    pass
        await asyncio.sleep(interval)


async def _snapshot_loop_watchdog_forever() -> None:
    while True:
        try:
            await asyncio.sleep(_WATCHDOG_INTERVAL_SECONDS)
            if not is_dashboard_snapshot_loop_running():
                _maybe_restart_snapshot_loop(reason="watchdog_loop_not_running")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _log.warning("dashboard snapshot loop watchdog error: %s", exc, exc_info=True)


def _ensure_watchdog_started() -> None:
    global _watchdog_task
    if _watchdog_task is not None and not _watchdog_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _watchdog_task = loop.create_task(
        _snapshot_loop_watchdog_forever(),
        name="dashboard_snapshot_builder_watchdog",
    )


def start_dashboard_snapshot_builder_loop() -> None:
    global _loop_task
    from services.dashboard_snapshot_builder_v1 import dashboard_snapshot_builder_enabled

    health = _loop_health_module()

    if not dashboard_snapshot_builder_enabled():
        _emit_loop("SKIPPED", reason="builder_disabled")
        if health is not None:
            health.record_loop_start_skipped(reason="builder_disabled")
        return
    if is_dashboard_snapshot_loop_running():
        _ensure_watchdog_started()
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        if health is not None:
            health.record_loop_start_skipped(reason="no_running_event_loop")
        _emit_loop("SKIPPED", reason="no_running_event_loop")
        return
    _loop_task = loop.create_task(
        _dashboard_snapshot_loop_main(),
        name="dashboard_snapshot_builder_loop",
    )
    _loop_task.add_done_callback(_on_loop_task_done)
    _ensure_watchdog_started()


async def stop_dashboard_snapshot_builder_loop() -> None:
    """Cancel loop + watchdog (tests / graceful shutdown)."""
    global _loop_task, _watchdog_task
    for attr in ("_watchdog_task", "_loop_task"):
        task = _watchdog_task if attr == "_watchdog_task" else _loop_task
        if task is None:
            continue
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _watchdog_task = None
    _loop_task = None


__all__ = [
    "dashboard_snapshot_loop_interval_seconds",
    "get_dashboard_snapshot_loop_task_state",
    "is_dashboard_snapshot_loop_running",
    "run_dashboard_snapshot_loop_tick",
    "start_dashboard_snapshot_builder_loop",
    "stop_dashboard_snapshot_builder_loop",
]
