# -*- coding: utf-8 -*-
"""Simulation observability / dashboard payload — Phase 3 (internal only)."""
from __future__ import annotations

import json
from typing import Any

from services.store_reality_simulator.progress_v1 import build_progress_monitor
from services.store_reality_simulator.run_registry_v1 import require_run


def build_simulation_dashboard(simulation_run_id: str) -> dict[str, Any]:
    """Internal simulation control surface payload — never merchant-facing."""
    row = require_run(simulation_run_id)
    monitor = build_progress_monitor(row)
    pending = db_count_status(row.simulation_run_id, "planned")
    processed = (
        db_count_status(row.simulation_run_id, "processed")
        + db_count_status(row.simulation_run_id, "unsupported")
        + db_count_status(row.simulation_run_id, "rejected")
        + db_count_status(row.simulation_run_id, "failed")
    )
    total = db_count_status(row.simulation_run_id, None)
    score = {}
    if getattr(row, "reality_score_json", None):
        try:
            score = json.loads(row.reality_score_json or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            score = {}
    throttle = {}
    if getattr(row, "throttle_state_json", None):
        try:
            throttle = json.loads(row.throttle_state_json or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            throttle = {}
    progress = monitor.get("progress") or {}
    return {
        "surface": "simulation_dashboard",
        "merchant_facing": False,
        "simulation_run_id": row.simulation_run_id,
        "current_phase": progress.get("phase") or monitor.get("status"),
        "current_simulated_day": monitor.get("current_day"),
        "current_batch": progress.get("batches_done"),
        "events_generated": total,
        "events_processed": processed,
        "events_pending": pending,
        "reality_score": score.get("overall"),
        "reality_score_dimensions": score.get("dimensions"),
        "performance_impact": {
            "last_batch_ms": progress.get("last_batch_ms"),
            "throttle_state": throttle.get("state") or progress.get("throttle_state"),
        },
        "throttle_state": throttle.get("state") or progress.get("throttle_state"),
        "pause_reason": throttle.get("reason") or progress.get("pause_reason"),
        "estimated_completion": _estimate(total, processed, progress),
        "checkpoint_age": (monitor.get("checkpoint") or {}).get("created_at"),
        "seed": row.seed,
        "scale_profile": getattr(row, "scale_profile", None),
        "resume_available": monitor.get("resume_available"),
        "monitor": monitor,
    }


def db_count_status(run_id: str, status: str | None) -> int:
    from extensions import db
    from models import SimulationEventLedger

    q = db.session.query(SimulationEventLedger).filter(
        SimulationEventLedger.simulation_run_id == run_id
    )
    if status:
        q = q.filter(SimulationEventLedger.status == status)
    return int(q.count() or 0)


def _estimate(total: int, processed: int, progress: dict[str, Any]) -> dict[str, Any]:
    if total <= 0:
        return {"percent": 0.0, "note": "no_events"}
    pct = round(100.0 * processed / total, 1)
    return {
        "percent": pct,
        "processed": processed,
        "total": total,
        "batches_done": progress.get("batches_done"),
    }
