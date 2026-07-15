# -*- coding: utf-8 -*-
"""Simulation run registry — persistence for Phase 2 orchestration."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from extensions import db
from models import SimulationRun
from services.store_reality_simulator.accounting_v1 import (
    accounting_to_json,
    empty_accounting,
)
from services.store_reality_simulator.checkpoint_v1 import (
    checkpoint_to_json,
    empty_checkpoint,
    resume_plan,
)
from services.store_reality_simulator.clock_v1 import SimulationClock
from services.store_reality_simulator.config_loader_v1 import (
    SimulationConfig,
    load_simulation_config,
)
from services.store_reality_simulator.contracts_v1 import (
    DEMO_STORE_SLUG,
    STATUS_CREATED,
    STATUS_PAUSED,
    STATUS_RUNNING,
    assert_demo_store,
)
from services.store_reality_simulator.progress_v1 import (
    build_progress_monitor,
    empty_progress,
    progress_to_json,
)


def _wall_now() -> datetime:
    return datetime.now(timezone.utc)


def new_simulation_run_id() -> str:
    return f"srs_{uuid.uuid4().hex}"


def create_simulation_run(
    config: SimulationConfig | dict[str, Any],
    *,
    simulation_run_id: Optional[str] = None,
) -> SimulationRun:
    cfg = (
        config
        if isinstance(config, SimulationConfig)
        else load_simulation_config(config)
    )
    assert_demo_store(cfg.store_slug)
    run_id = (simulation_run_id or new_simulation_run_id()).strip()
    if not run_id:
        raise ValueError("simulation_run_id_required")

    existing = get_run(run_id)
    if existing is not None:
        raise ValueError(f"simulation_run_exists:{run_id}")

    now = _wall_now()
    start_dt = datetime(
        cfg.start_date.year,
        cfg.start_date.month,
        cfg.start_date.day,
        tzinfo=timezone.utc,
    )
    row = SimulationRun(
        simulation_run_id=run_id,
        store_slug=DEMO_STORE_SLUG,
        scenario_ids_json=json.dumps(cfg.scenario_ids, ensure_ascii=False),
        seed=int(cfg.seed),
        start_date=start_dt,
        duration_days=int(cfg.duration_days),
        status=STATUS_CREATED,
        current_day=start_dt,
        current_step=0,
        simulated_now=start_dt,
        config_json=json.dumps(cfg.to_dict(), ensure_ascii=False, sort_keys=True),
        accounting_json=accounting_to_json(empty_accounting()),
        checkpoint_json=checkpoint_to_json(empty_checkpoint()),
        progress_json=progress_to_json(empty_progress()),
        errors_json="[]",
        warnings_json="[]",
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    db.session.commit()
    return row


def get_run(simulation_run_id: str) -> Optional[SimulationRun]:
    run_id = str(simulation_run_id or "").strip()
    if not run_id:
        return None
    return (
        db.session.query(SimulationRun)
        .filter(SimulationRun.simulation_run_id == run_id)
        .first()
    )


def require_run(simulation_run_id: str) -> SimulationRun:
    row = get_run(simulation_run_id)
    if row is None:
        raise KeyError(f"simulation_run_not_found:{simulation_run_id}")
    return row


def touch_run(run_row: SimulationRun) -> None:
    run_row.updated_at = _wall_now()


def persist_run(run_row: SimulationRun) -> SimulationRun:
    touch_run(run_row)
    db.session.add(run_row)
    db.session.commit()
    return run_row


def set_run_status(run_row: SimulationRun, status: str) -> SimulationRun:
    run_row.status = str(status)
    return persist_run(run_row)


def clock_for_run(run_row: SimulationRun) -> SimulationClock:
    when = getattr(run_row, "simulated_now", None)
    if when is None:
        sd = run_row.start_date
        if isinstance(sd, date) and not isinstance(sd, datetime):
            when = datetime(sd.year, sd.month, sd.day, tzinfo=timezone.utc)
        elif isinstance(sd, datetime):
            when = sd
        else:
            when = _wall_now()
    if getattr(when, "tzinfo", None) is None:
        when = when.replace(tzinfo=timezone.utc)
    return SimulationClock(when)


def sync_clock_to_run(run_row: SimulationRun, clock: SimulationClock) -> None:
    run_row.simulated_now = clock.now()
    d = clock.current_day()
    run_row.current_day = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def resume_run(simulation_run_id: str) -> dict[str, Any]:
    """Mark run running from checkpoint — no event generation."""
    row = require_run(simulation_run_id)
    plan = resume_plan(row)
    if not plan.get("ok"):
        return plan
    row.status = STATUS_RUNNING
    persist_run(row)
    plan["status"] = row.status
    plan["monitor"] = build_progress_monitor(row)
    return plan


def pause_run_by_id(simulation_run_id: str, *, reason: str = "pause") -> dict[str, Any]:
    from services.store_reality_simulator.checkpoint_v1 import pause_run

    row = require_run(simulation_run_id)
    cp = pause_run(row, reason=reason)
    persist_run(row)
    return {"ok": True, "status": STATUS_PAUSED, "checkpoint": cp}


def monitor_run(simulation_run_id: str) -> dict[str, Any]:
    row = require_run(simulation_run_id)
    return build_progress_monitor(row)
