# -*- coding: utf-8 -*-
"""Async loop for exposure_retention_tick_v1 (scheduler process only). Default OFF."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

_log = logging.getLogger(__name__)

_loop_task: Optional[asyncio.Task[None]] = None
_tick_lock = asyncio.Lock()
_DEFAULT_INTERVAL_SECONDS = 3600.0


def exposure_retention_loop_interval_seconds() -> float:
    raw = (os.environ.get("CARTFLOW_EXPOSURE_RETENTION_INTERVAL_SECONDS") or "").strip()
    try:
        v = float(raw or _DEFAULT_INTERVAL_SECONDS)
    except (TypeError, ValueError):
        v = _DEFAULT_INTERVAL_SECONDS
    return max(300.0, v)


def is_exposure_retention_loop_running() -> bool:
    return _loop_task is not None and not _loop_task.done()


def _emit_loop(tag: str, **fields: Any) -> None:
    parts = [f"{k}={fields[k]}" for k in sorted(fields) if fields[k] is not None]
    suffix = f" {' '.join(parts)}" if parts else ""
    line = f"[EXPOSURE RETENTION LOOP {tag}]{suffix}"
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        _log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


async def run_exposure_retention_loop_tick() -> dict[str, Any]:
    if _tick_lock.locked():
        return {"skipped": True, "reason": "tick_in_progress"}
    async with _tick_lock:
        from services.product_exposure_v1.retention_v1 import (
            exposure_retention_enabled,
            run_exposure_retention_tick,
        )

        if not exposure_retention_enabled():
            return {"skipped": True, "reason": "retention_disabled"}
        try:
            return await asyncio.to_thread(run_exposure_retention_tick)
        except Exception as exc:  # noqa: BLE001
            err = str(exc)[:500]
            _emit_loop("TICK ERROR", detail=err)
            _log.warning("exposure retention tick failed: %s", exc, exc_info=True)
            return {"ok": False, "error": err}


async def _exposure_retention_loop_main() -> None:
    interval = exposure_retention_loop_interval_seconds()
    _emit_loop("STARTED", interval_s=interval)
    while True:
        try:
            await run_exposure_retention_loop_tick()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _emit_loop("TICK ERROR", detail=str(exc)[:200])
            _log.warning("exposure retention loop tick error: %s", exc, exc_info=True)
        await asyncio.sleep(interval)


def start_exposure_retention_loop() -> None:
    global _loop_task
    from services.product_exposure_v1.retention_v1 import exposure_retention_enabled

    if not exposure_retention_enabled():
        _emit_loop("SKIPPED", reason="retention_disabled")
        return
    if is_exposure_retention_loop_running():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _emit_loop("SKIPPED", reason="no_running_event_loop")
        return
    _loop_task = loop.create_task(
        _exposure_retention_loop_main(),
        name="exposure_retention_loop",
    )


async def stop_exposure_retention_loop() -> None:
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
    "exposure_retention_loop_interval_seconds",
    "is_exposure_retention_loop_running",
    "run_exposure_retention_loop_tick",
    "start_exposure_retention_loop",
    "stop_exposure_retention_loop",
]
