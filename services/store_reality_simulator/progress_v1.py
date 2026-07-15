# -*- coding: utf-8 -*-
"""Simulation progress monitor payloads — Phase 2."""
from __future__ import annotations

import json
from typing import Any, Optional

from services.store_reality_simulator.accounting_v1 import (
    accounting_from_json,
    normalize_accounting,
    reconcile_accounting,
)
from services.store_reality_simulator.contracts_v1 import RUN_STATUSES


def empty_progress() -> dict[str, Any]:
    return {
        "phase": "infrastructure",
        "current_step": 0,
        "total_steps_estimate": 0,
        "current_day": None,
        "percent_complete": 0.0,
        "last_checkpoint_id": None,
        "resume_available": False,
        "events_generated": False,
        "message": "Phase 2 infrastructure — no event generation",
    }


def normalize_progress(raw: Any) -> dict[str, Any]:
    base = empty_progress()
    if not isinstance(raw, dict):
        return base
    base.update({k: raw[k] for k in raw if k in base or k.startswith("extra_")})
    try:
        base["current_step"] = max(0, int(raw.get("current_step", 0) or 0))
    except (TypeError, ValueError):
        base["current_step"] = 0
    try:
        base["percent_complete"] = float(raw.get("percent_complete", 0) or 0)
    except (TypeError, ValueError):
        base["percent_complete"] = 0.0
    base["resume_available"] = bool(raw.get("resume_available", False))
    base["events_generated"] = False  # Phase 2 hard rule
    return base


def progress_from_json(raw: Optional[str]) -> dict[str, Any]:
    if not raw:
        return empty_progress()
    try:
        return normalize_progress(json.loads(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return empty_progress()


def progress_to_json(progress: dict[str, Any]) -> str:
    return json.dumps(normalize_progress(progress), ensure_ascii=False, sort_keys=True)


def build_progress_monitor(run_row: Any) -> dict[str, Any]:
    """Observability surface for a SimulationRun ORM row."""
    status = str(getattr(run_row, "status", "") or "")
    accounting = accounting_from_json(getattr(run_row, "accounting_json", None))
    progress = progress_from_json(getattr(run_row, "progress_json", None))
    checkpoint_raw = getattr(run_row, "checkpoint_json", None) or "{}"
    try:
        checkpoint = json.loads(checkpoint_raw) if checkpoint_raw else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        checkpoint = {}

    resume_available = status in ("paused", "failed", "running") and bool(
        checkpoint.get("checkpoint_id") or checkpoint.get("last_simulated_event_id") is not None
        or int(progress.get("current_step") or 0) > 0
        or status == "paused"
    )
    progress["resume_available"] = resume_available

    return {
        "simulation_run_id": getattr(run_row, "simulation_run_id", None),
        "store_slug": getattr(run_row, "store_slug", None),
        "status": status,
        "status_known": status in RUN_STATUSES,
        "seed": getattr(run_row, "seed", None),
        "scenario_ids": _parse_json_list(getattr(run_row, "scenario_ids_json", None)),
        "start_date": _iso(getattr(run_row, "start_date", None)),
        "duration_days": getattr(run_row, "duration_days", None),
        "current_day": _iso(getattr(run_row, "current_day", None)),
        "current_step": getattr(run_row, "current_step", 0),
        "simulated_now": _iso(getattr(run_row, "simulated_now", None)),
        "phase": progress.get("phase"),
        "checkpoint": checkpoint,
        "progress": progress,
        "accounting": normalize_accounting(accounting),
        "accounting_reconcile": reconcile_accounting(accounting),
        "errors": _parse_json_list(getattr(run_row, "errors_json", None)),
        "warnings": _parse_json_list(getattr(run_row, "warnings_json", None)),
        "resume_available": resume_available,
        "event_generation_enabled": False,
    }


def _parse_json_list(raw: Any) -> list[Any]:
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
