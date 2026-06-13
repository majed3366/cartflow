# -*- coding: utf-8 -*-
"""
Optional automatic loop for ``scan_due_recovery_schedules`` (queue/worker readiness v1).

Disabled unless ``CARTFLOW_DB_DUE_SCANNER_ENABLED=true``. Does not replace asyncio delay
dispatch or startup future re-arm / resume scan.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

_log = logging.getLogger(__name__)

_loop_task: Optional[asyncio.Task[None]] = None
_tick_lock = asyncio.Lock()
_DEFAULT_INTERVAL_SECONDS = 30.0
_DEFAULT_LIMIT = 25
_LOOP_SOURCE = "db_due_scanner_loop"


def _env_truthy(name: str, *, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def is_db_due_scanner_loop_enabled() -> bool:
    return _env_truthy("CARTFLOW_DB_DUE_SCANNER_ENABLED", default=False)


def db_due_scanner_loop_interval_seconds() -> float:
    try:
        v = float(
            (os.getenv("CARTFLOW_DB_DUE_SCANNER_INTERVAL_SECONDS") or "").strip()
            or _DEFAULT_INTERVAL_SECONDS
        )
    except (TypeError, ValueError):
        v = _DEFAULT_INTERVAL_SECONDS
    return max(5.0, v)


def db_due_scanner_loop_limit() -> int:
    raw = (
        (os.getenv("CARTFLOW_DUE_SCANNER_LIMIT") or "").strip()
        or (os.getenv("CARTFLOW_DB_DUE_SCANNER_LIMIT") or "").strip()
        or str(_DEFAULT_LIMIT)
    )
    try:
        v = int(raw)
    except (TypeError, ValueError):
        v = _DEFAULT_LIMIT
    return max(1, v)


def _log_loop(tag: str, **fields: Any) -> None:
    parts = [f"{k}={fields[k]}" for k in sorted(fields) if fields[k] is not None]
    suffix = f" {' '.join(parts)}" if parts else ""
    print(f"[DB DUE SCANNER LOOP {tag}]{suffix}", flush=True)


def is_db_due_scanner_loop_task_running() -> bool:
    return _loop_task is not None and not _loop_task.done()


async def run_db_due_scanner_loop_tick() -> Dict[str, Any]:
    """
    One scanner pass. Skips if a previous tick is still running (no overlap).
    """
    if _tick_lock.locked():
        _log_loop("SKIPPED", reason="tick_in_progress")
        try:
            from services.db_due_scanner_health import record_db_due_scanner_tick_skipped

            record_db_due_scanner_tick_skipped(reason="tick_in_progress")
        except Exception:  # noqa: BLE001
            pass
        return {"skipped": True, "reason": "tick_in_progress"}

    async with _tick_lock:
        _log_loop(
            "TICK",
            interval_seconds=db_due_scanner_loop_interval_seconds(),
            limit=db_due_scanner_loop_limit(),
        )
        try:
            from services.recovery_db_due_scanner import scan_due_recovery_schedules

            out = await scan_due_recovery_schedules(
                limit=db_due_scanner_loop_limit(),
                source=_LOOP_SOURCE,
            )
            _log_loop(
                "TICK",
                phase="done",
                found=out.get("found", 0),
                dispatched=out.get("dispatched", 0),
                skipped=out.get("skipped", 0),
            )
            try:
                from services.db_due_scanner_health import record_db_due_scanner_tick_result

                record_db_due_scanner_tick_result(out)
            except Exception:  # noqa: BLE001
                pass
            return out
        except Exception as exc:  # noqa: BLE001
            _log_loop("ERROR", detail=str(exc)[:200])
            err_out: Dict[str, Any] = {"error": str(exc), "skipped": False}
            try:
                from services.db_due_scanner_health import (
                    record_db_due_scanner_loop_error,
                    record_db_due_scanner_tick_result,
                )

                record_db_due_scanner_loop_error(detail=str(exc))
                record_db_due_scanner_tick_result(err_out)
            except Exception:  # noqa: BLE001
                pass
            return err_out
        finally:
            from services.db_session_lifecycle import release_scoped_db_session

            release_scoped_db_session()


async def _db_due_scanner_loop_forever() -> None:
    interval = db_due_scanner_loop_interval_seconds()
    while True:
        try:
            await asyncio.sleep(interval)
            await run_db_due_scanner_loop_tick()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            _log_loop("ERROR", detail=str(exc)[:200])
            _log.warning("db due scanner loop tick failed: %s", exc)
            try:
                from services.db_due_scanner_health import record_db_due_scanner_loop_error

                record_db_due_scanner_loop_error(detail=str(exc))
            except Exception:  # noqa: BLE001
                pass


def start_db_due_recovery_scanner_loop() -> None:
    """Start background loop on the running event loop (call from FastAPI startup)."""
    global _loop_task

    from services.recovery_process_role_v1 import evaluate_scheduler_ownership_policy

    policy = evaluate_scheduler_ownership_policy(force=False)
    if not policy.get("may_due_scan"):
        _log_loop(
            "SKIPPED",
            reason=str(policy.get("block_reason") or "ownership_blocked"),
        )
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _log.warning("db due scanner loop: no running event loop")
        return

    if _loop_task is not None and not _loop_task.done():
        _log_loop("SKIPPED", reason="loop_already_started")
        return

    _log_loop(
        "STARTED",
        interval_seconds=db_due_scanner_loop_interval_seconds(),
        limit=db_due_scanner_loop_limit(),
    )
    _loop_task = loop.create_task(
        _db_due_scanner_loop_forever(),
        name="recovery_db_due_scanner_loop",
    )
    try:
        from services.db_due_scanner_health import record_db_due_scanner_loop_started

        record_db_due_scanner_loop_started()
    except Exception:  # noqa: BLE001
        pass


async def stop_db_due_recovery_scanner_loop() -> None:
    """Cancel loop task (tests / graceful shutdown)."""
    global _loop_task
    if _loop_task is None:
        return
    _loop_task.cancel()
    try:
        await _loop_task
    except asyncio.CancelledError:
        pass
    finally:
        _loop_task = None
        try:
            from services.db_due_scanner_health import record_db_due_scanner_loop_stopped

            record_db_due_scanner_loop_stopped()
        except Exception:  # noqa: BLE001
            pass
