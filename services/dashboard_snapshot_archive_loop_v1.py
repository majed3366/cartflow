# -*- coding: utf-8 -*-
"""Async loop for dashboard snapshot archive job (scheduler / background only)."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

_log = logging.getLogger(__name__)

_loop_task: Optional[asyncio.Task[None]] = None
_tick_lock = asyncio.Lock()
_DEFAULT_INTERVAL_SECONDS = 3600.0


def dashboard_snapshot_archive_loop_interval_seconds() -> float:
    raw = (os.environ.get("CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_INTERVAL_SECONDS") or "").strip()
    try:
        v = float(raw or _DEFAULT_INTERVAL_SECONDS)
    except (TypeError, ValueError):
        v = _DEFAULT_INTERVAL_SECONDS
    return max(300.0, v)


def is_dashboard_snapshot_archive_loop_running() -> bool:
    return _loop_task is not None and not _loop_task.done()


def _emit_loop(tag: str, **fields: Any) -> None:
    parts = [f"{k}={fields[k]}" for k in sorted(fields) if fields[k] is not None]
    suffix = f" {' '.join(parts)}" if parts else ""
    line = f"[DASHBOARD SNAPSHOT ARCHIVE LOOP {tag}]{suffix}"
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        _log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


async def run_dashboard_snapshot_archive_loop_tick() -> dict[str, Any]:
    if _tick_lock.locked():
        return {"skipped": True, "reason": "tick_in_progress"}
    async with _tick_lock:
        from services.dashboard_snapshot_archive_v1 import (
            dashboard_snapshot_archive_enabled,
            run_dashboard_snapshot_archive_tick,
        )

        if not dashboard_snapshot_archive_enabled():
            return {"skipped": True, "reason": "archive_disabled"}
        try:
            return await asyncio.to_thread(run_dashboard_snapshot_archive_tick)
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:500]
            _emit_loop("TICK ERROR", detail=err)
            _log.warning("dashboard snapshot archive tick failed: %s", exc, exc_info=True)
            return {"ok": False, "error": err}


async def _dashboard_snapshot_archive_loop_main() -> None:
    interval = dashboard_snapshot_archive_loop_interval_seconds()
    _emit_loop("STARTED", interval_s=interval)
    while True:
        try:
            await run_dashboard_snapshot_archive_loop_tick()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _emit_loop("TICK ERROR", detail=str(exc)[:200])
            _log.warning("dashboard snapshot archive loop tick error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)


def start_dashboard_snapshot_archive_loop() -> None:
    global _loop_task
    from services.dashboard_snapshot_archive_v1 import dashboard_snapshot_archive_enabled

    if not dashboard_snapshot_archive_enabled():
        _emit_loop("SKIPPED", reason="archive_disabled")
        return
    if is_dashboard_snapshot_archive_loop_running():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _emit_loop("SKIPPED", reason="no_running_event_loop")
        return
    _loop_task = loop.create_task(
        _dashboard_snapshot_archive_loop_main(),
        name="dashboard_snapshot_archive_loop",
    )


async def stop_dashboard_snapshot_archive_loop() -> None:
    global _loop_task
    if _loop_task is None:
        return
    _loop_task.cancel()
    try:
        await _loop_task
    except asyncio.CancelledError:
        pass
    _loop_task = None


__all__ = [
    "dashboard_snapshot_archive_loop_interval_seconds",
    "is_dashboard_snapshot_archive_loop_running",
    "run_dashboard_snapshot_archive_loop_tick",
    "start_dashboard_snapshot_archive_loop",
    "stop_dashboard_snapshot_archive_loop",
]
