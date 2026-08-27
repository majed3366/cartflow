# -*- coding: utf-8 -*-
"""In-process Scheduler liveness cache. Routine health must not query Postgres."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

_state: dict[str, Any] = {
    "process_role": "unset",
    "last_successful_cycle_at": None,
    "last_failure_at": None,
    "last_failure_kind": None,
    "next_scheduled_cycle_at": None,
    "enabled_jobs": [],
    "ready": False,
    "live": False,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def reset_scheduler_runtime_state() -> None:
    _state.update(
        {
            "process_role": "unset",
            "last_successful_cycle_at": None,
            "last_failure_at": None,
            "last_failure_kind": None,
            "next_scheduled_cycle_at": None,
            "enabled_jobs": [],
            "ready": False,
            "live": False,
        }
    )


def mark_scheduler_live(*, role: str, enabled_jobs: list[str], ready: bool) -> None:
    _state["process_role"] = role
    _state["enabled_jobs"] = list(enabled_jobs)
    _state["ready"] = bool(ready)
    _state["live"] = True


def record_cycle_success(*, job: str, next_run_at: Optional[datetime] = None) -> None:
    _state["last_successful_cycle_at"] = _utcnow().isoformat()
    _state["last_job"] = (job or "")[:64]
    if next_run_at is not None:
        _state["next_scheduled_cycle_at"] = next_run_at.isoformat()


def record_cycle_failure(*, job: str, kind: str = "error") -> None:
    _state["last_failure_at"] = _utcnow().isoformat()
    _state["last_failure_kind"] = (kind or "error")[:64]
    _state["last_job"] = (job or "")[:64]


def record_next_run(next_run_at: datetime) -> None:
    _state["next_scheduled_cycle_at"] = next_run_at.isoformat()


def snapshot_scheduler_runtime_state() -> dict[str, Any]:
    return {
        "ok": bool(_state.get("live")),
        "role": _state.get("process_role") or "unset",
        "last_successful_cycle": _state.get("last_successful_cycle_at"),
        "last_failure": _state.get("last_failure_at"),
        "last_failure_kind": _state.get("last_failure_kind"),
        "next_scheduled_cycle": _state.get("next_scheduled_cycle_at"),
        "enabled_jobs": list(_state.get("enabled_jobs") or []),
        "ready": bool(_state.get("ready")),
        "live": bool(_state.get("live")),
        "source": "in_process_cache",
    }


__all__ = [
    "mark_scheduler_live",
    "record_cycle_failure",
    "record_cycle_success",
    "record_next_run",
    "reset_scheduler_runtime_state",
    "snapshot_scheduler_runtime_state",
]
