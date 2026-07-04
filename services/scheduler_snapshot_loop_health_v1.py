# -*- coding: utf-8 -*-
"""In-process health state for dashboard snapshot builder loop (diagnostics only)."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Optional

_lock = threading.Lock()
_state: dict[str, Any] = {
    "snapshot_loop_started_at": None,
    "snapshot_loop_interval_seconds": None,
    "snapshot_loop_last_tick_at": None,
    "snapshot_loop_last_success_at": None,
    "snapshot_loop_last_error_at": None,
    "snapshot_loop_last_error": None,
    "snapshot_loop_tick_count": 0,
    "snapshot_loop_success_count": 0,
    "snapshot_loop_failure_count": 0,
    "last_tick_stores_seen": None,
    "last_tick_stores_built": None,
    "last_tick_at": None,
    "last_store_selected": None,
    "last_store_selection_reason": None,
    "last_snapshot_write_store_slug": None,
    "last_snapshot_write_type": None,
    "last_snapshot_write_generated_at": None,
    "loop_start_skipped_at": None,
    "loop_start_skipped_reason": None,
    "loop_task_exited": False,
    "loop_task_exit_reason": None,
    "loop_task_exit_at": None,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        raw = str(s).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def clear_scheduler_snapshot_loop_health_for_tests() -> None:
    with _lock:
        for key in list(_state.keys()):
            if key.endswith("_count"):
                _state[key] = 0
            elif key.endswith("_at") or key.endswith("_reason") or key.endswith("_error"):
                _state[key] = None
            elif key == "snapshot_loop_interval_seconds":
                _state[key] = None
            elif key == "loop_task_exited":
                _state[key] = False
            else:
                _state[key] = None


def record_loop_start_skipped(*, reason: str) -> None:
    with _lock:
        _state["loop_start_skipped_at"] = _iso(_utcnow())
        _state["loop_start_skipped_reason"] = (reason or "")[:256]


def record_loop_started(*, interval_seconds: float) -> None:
    now = _utcnow()
    with _lock:
        _state["snapshot_loop_started_at"] = _iso(now)
        _state["snapshot_loop_interval_seconds"] = float(interval_seconds)
        _state["loop_start_skipped_at"] = None
        _state["loop_start_skipped_reason"] = None
        _state["loop_task_exited"] = False
        _state["loop_task_exit_reason"] = None
        _state["loop_task_exit_at"] = None


def record_loop_tick_started() -> None:
    with _lock:
        _state["snapshot_loop_last_tick_at"] = _iso(_utcnow())
        _state["snapshot_loop_tick_count"] = int(_state.get("snapshot_loop_tick_count") or 0) + 1


def record_loop_tick_success(*, result: Optional[dict[str, Any]] = None) -> None:
    with _lock:
        now = _utcnow()
        _state["snapshot_loop_last_success_at"] = _iso(now)
        _state["snapshot_loop_success_count"] = int(
            _state.get("snapshot_loop_success_count") or 0
        ) + 1
        if isinstance(result, dict):
            if result.get("stores_seen") is not None:
                _state["last_tick_stores_seen"] = int(result.get("stores_seen") or 0)
            if result.get("stores_built") is not None:
                _state["last_tick_stores_built"] = int(result.get("stores_built") or 0)
            _state["last_tick_at"] = _iso(now)


def record_loop_tick_failure(*, error: str) -> None:
    with _lock:
        now = _utcnow()
        _state["snapshot_loop_last_error_at"] = _iso(now)
        _state["snapshot_loop_last_error"] = (error or "unknown")[:500]
        _state["snapshot_loop_failure_count"] = int(
            _state.get("snapshot_loop_failure_count") or 0
        ) + 1


def record_loop_task_exited(*, reason: str, error: Optional[str] = None) -> None:
    with _lock:
        _state["loop_task_exited"] = True
        _state["loop_task_exit_reason"] = (reason or "unknown")[:256]
        _state["loop_task_exit_at"] = _iso(_utcnow())
        if error:
            now = _utcnow()
            _state["snapshot_loop_last_error_at"] = _iso(now)
            _state["snapshot_loop_last_error"] = (error or "unknown")[:500]
            _state["snapshot_loop_failure_count"] = int(
                _state.get("snapshot_loop_failure_count") or 0
            ) + 1


def record_store_selected(*, store_slug: str, reason: str = "") -> None:
    with _lock:
        _state["last_store_selected"] = (store_slug or "")[:255] or None
        _state["last_store_selection_reason"] = (reason or "")[:128] or None


def record_snapshot_write(
    *,
    store_slug: str,
    snapshot_type: str,
    generated_at: datetime,
) -> None:
    with _lock:
        _state["last_snapshot_write_store_slug"] = (store_slug or "")[:255] or None
        _state["last_snapshot_write_type"] = (snapshot_type or "")[:64] or None
        _state["last_snapshot_write_generated_at"] = _iso(generated_at)


def _next_tick_due_in_seconds(
    *,
    last_tick_at: Optional[str],
    interval_seconds: Optional[float],
    loop_running: bool,
) -> Optional[float]:
    if not loop_running or not last_tick_at or interval_seconds is None:
        return None
    last = _parse_iso(last_tick_at)
    if last is None:
        return None
    elapsed = (_utcnow() - last).total_seconds()
    return round(max(0.0, float(interval_seconds) - elapsed), 1)


def build_scheduler_snapshot_loop_status() -> dict[str, Any]:
    from services.dashboard_snapshot_builder_v1 import dashboard_snapshot_builder_enabled
    from services.dashboard_snapshot_loop_v1 import (
        dashboard_snapshot_loop_interval_seconds,
        get_dashboard_snapshot_loop_task_state,
        is_dashboard_snapshot_loop_running,
    )
    from services.recovery_process_role_v1 import resolve_process_role

    with _lock:
        snap = dict(_state)

    task_state = get_dashboard_snapshot_loop_task_state()
    loop_running = is_dashboard_snapshot_loop_running()
    interval = snap.get("snapshot_loop_interval_seconds")
    if interval is None:
        interval = dashboard_snapshot_loop_interval_seconds()

    process_role = resolve_process_role()
    builder_enabled = dashboard_snapshot_builder_enabled()

    return {
        "ok": True,
        "process_role": process_role,
        "dashboard_snapshot_builder_enabled": bool(builder_enabled),
        "snapshot_loop_started_at": snap.get("snapshot_loop_started_at"),
        "snapshot_loop_last_tick_at": snap.get("snapshot_loop_last_tick_at"),
        "snapshot_loop_last_success_at": snap.get("snapshot_loop_last_success_at"),
        "snapshot_loop_last_error_at": snap.get("snapshot_loop_last_error_at"),
        "snapshot_loop_last_error": snap.get("snapshot_loop_last_error"),
        "snapshot_loop_tick_count": int(snap.get("snapshot_loop_tick_count") or 0),
        "snapshot_loop_success_count": int(snap.get("snapshot_loop_success_count") or 0),
        "snapshot_loop_failure_count": int(snap.get("snapshot_loop_failure_count") or 0),
        "last_tick_stores_seen": snap.get("last_tick_stores_seen"),
        "last_tick_stores_built": snap.get("last_tick_stores_built"),
        "last_tick_at": snap.get("last_tick_at"),
        "last_store_selected": snap.get("last_store_selected"),
        "last_snapshot_write_store_slug": snap.get("last_snapshot_write_store_slug"),
        "last_snapshot_write_type": snap.get("last_snapshot_write_type"),
        "last_snapshot_write_generated_at": snap.get("last_snapshot_write_generated_at"),
        "next_tick_due_in_seconds": _next_tick_due_in_seconds(
            last_tick_at=snap.get("snapshot_loop_last_tick_at"),
            interval_seconds=float(interval) if interval is not None else None,
            loop_running=loop_running,
        ),
        "loop_running": loop_running,
        "loop_task_alive": bool(task_state.get("task_alive")),
        "loop_task_exited": bool(snap.get("loop_task_exited")),
        "loop_task_exit_reason": snap.get("loop_task_exit_reason"),
        "loop_task_exit_at": snap.get("loop_task_exit_at"),
        "loop_start_skipped_at": snap.get("loop_start_skipped_at"),
        "loop_start_skipped_reason": snap.get("loop_start_skipped_reason"),
        "snapshot_loop_interval_seconds": float(interval),
        "last_store_selection_reason": snap.get("last_store_selection_reason"),
        "loop_task_done": bool(task_state.get("task_done")),
        "loop_task_cancelled": bool(task_state.get("task_cancelled")),
    }


__all__ = [
    "build_scheduler_snapshot_loop_status",
    "clear_scheduler_snapshot_loop_health_for_tests",
    "record_loop_start_skipped",
    "record_loop_started",
    "record_loop_task_exited",
    "record_loop_tick_failure",
    "record_loop_tick_started",
    "record_loop_tick_success",
    "record_snapshot_write",
    "record_store_selected",
]
