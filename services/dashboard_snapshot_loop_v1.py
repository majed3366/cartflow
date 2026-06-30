# -*- coding: utf-8 -*-
"""Async loop for dashboard snapshot builder (scheduler / background only)."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

_log = logging.getLogger(__name__)

_loop_task: Optional[asyncio.Task[None]] = None
_tick_lock = asyncio.Lock()
_DEFAULT_INTERVAL_SECONDS = 45.0


def dashboard_snapshot_loop_interval_seconds() -> float:
    raw = (os.environ.get("CARTFLOW_DASHBOARD_SNAPSHOT_INTERVAL_SECONDS") or "").strip()
    try:
        v = float(raw or _DEFAULT_INTERVAL_SECONDS)
    except (TypeError, ValueError):
        v = _DEFAULT_INTERVAL_SECONDS
    return max(15.0, v)


def is_dashboard_snapshot_loop_running() -> bool:
    return _loop_task is not None and not _loop_task.done()


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
        return await asyncio.to_thread(run_dashboard_snapshot_builder_tick)


async def _dashboard_snapshot_loop_main() -> None:
    interval = dashboard_snapshot_loop_interval_seconds()
    print(
        f"[DASHBOARD SNAPSHOT LOOP STARTED] interval_s={interval}",
        flush=True,
    )
    while True:
        try:
            await run_dashboard_snapshot_loop_tick()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _log.warning("dashboard snapshot loop tick error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)


def start_dashboard_snapshot_builder_loop() -> None:
    global _loop_task
    from services.dashboard_snapshot_builder_v1 import dashboard_snapshot_builder_enabled

    if not dashboard_snapshot_builder_enabled():
        print("[DASHBOARD SNAPSHOT LOOP SKIPPED] builder_disabled", flush=True)
        return
    if is_dashboard_snapshot_loop_running():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _loop_task = loop.create_task(_dashboard_snapshot_loop_main())


__all__ = [
    "dashboard_snapshot_loop_interval_seconds",
    "is_dashboard_snapshot_loop_running",
    "run_dashboard_snapshot_loop_tick",
    "start_dashboard_snapshot_builder_loop",
]
