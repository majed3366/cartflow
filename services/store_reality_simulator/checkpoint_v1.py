# -*- coding: utf-8 -*-
"""Checkpoint / pause / resume helpers — Phase 2."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from services.store_reality_simulator.contracts_v1 import (
    STATUS_FAILED,
    STATUS_PAUSED,
    STATUS_RUNNING,
)
from services.store_reality_simulator.progress_v1 import (
    normalize_progress,
    progress_from_json,
    progress_to_json,
)


def empty_checkpoint() -> dict[str, Any]:
    return {
        "checkpoint_id": None,
        "created_at": None,
        "current_step": 0,
        "current_day": None,
        "simulated_now": None,
        "last_simulated_event_id": None,
        "batch_index": 0,
        "reason": None,
    }


def normalize_checkpoint(raw: Any) -> dict[str, Any]:
    base = empty_checkpoint()
    if not isinstance(raw, dict):
        return base
    base.update({k: raw.get(k, base.get(k)) for k in base})
    try:
        base["current_step"] = max(0, int(raw.get("current_step", 0) or 0))
    except (TypeError, ValueError):
        base["current_step"] = 0
    try:
        base["batch_index"] = max(0, int(raw.get("batch_index", 0) or 0))
    except (TypeError, ValueError):
        base["batch_index"] = 0
    return base


def checkpoint_from_json(raw: Optional[str]) -> dict[str, Any]:
    if not raw:
        return empty_checkpoint()
    try:
        return normalize_checkpoint(json.loads(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return empty_checkpoint()


def checkpoint_to_json(checkpoint: dict[str, Any]) -> str:
    return json.dumps(normalize_checkpoint(checkpoint), ensure_ascii=False, sort_keys=True)


def build_checkpoint(
    *,
    current_step: int,
    current_day: Any = None,
    simulated_now: Any = None,
    last_simulated_event_id: Optional[str] = None,
    batch_index: int = 0,
    reason: str = "bounded_work",
) -> dict[str, Any]:
    return normalize_checkpoint(
        {
            "checkpoint_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "current_step": int(current_step),
            "current_day": (
                current_day.isoformat()
                if hasattr(current_day, "isoformat")
                else current_day
            ),
            "simulated_now": (
                simulated_now.isoformat()
                if hasattr(simulated_now, "isoformat")
                else simulated_now
            ),
            "last_simulated_event_id": last_simulated_event_id,
            "batch_index": int(batch_index),
            "reason": reason,
        }
    )


def apply_checkpoint_to_run(run_row: Any, checkpoint: dict[str, Any]) -> None:
    cp = normalize_checkpoint(checkpoint)
    run_row.checkpoint_json = checkpoint_to_json(cp)
    run_row.current_step = int(cp.get("current_step") or 0)
    progress = progress_from_json(getattr(run_row, "progress_json", None))
    progress = normalize_progress(progress)
    progress["current_step"] = run_row.current_step
    progress["last_checkpoint_id"] = cp.get("checkpoint_id")
    progress["resume_available"] = True
    run_row.progress_json = progress_to_json(progress)


def pause_run(run_row: Any, *, reason: str = "pause") -> dict[str, Any]:
    cp = build_checkpoint(
        current_step=int(getattr(run_row, "current_step", 0) or 0),
        current_day=getattr(run_row, "current_day", None),
        simulated_now=getattr(run_row, "simulated_now", None),
        batch_index=0,
        reason=reason,
    )
    apply_checkpoint_to_run(run_row, cp)
    run_row.status = STATUS_PAUSED
    return cp


def mark_failed_with_checkpoint(run_row: Any, *, error: str) -> dict[str, Any]:
    cp = pause_run(run_row, reason="failure")
    run_row.status = STATUS_FAILED
    errors = []
    raw = getattr(run_row, "errors_json", None)
    if raw:
        try:
            errors = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            errors = []
    if not isinstance(errors, list):
        errors = []
    errors.append({"error": str(error)[:500], "at": datetime.now(timezone.utc).isoformat()})
    run_row.errors_json = json.dumps(errors, ensure_ascii=False)
    return cp


def resume_plan(run_row: Any) -> dict[str, Any]:
    """Describe how to resume — does not execute scenarios."""
    status = str(getattr(run_row, "status", "") or "")
    cp = checkpoint_from_json(getattr(run_row, "checkpoint_json", None))
    if status not in (STATUS_PAUSED, STATUS_FAILED, STATUS_RUNNING):
        return {
            "ok": False,
            "resume_available": False,
            "reason": f"status_not_resumable:{status}",
        }
    return {
        "ok": True,
        "resume_available": True,
        "from_step": int(cp.get("current_step") or getattr(run_row, "current_step", 0) or 0),
        "checkpoint": cp,
        "next_status": STATUS_RUNNING,
        "event_generation_enabled": False,
        "note": "Phase 2 resume restores orchestration state only",
    }
