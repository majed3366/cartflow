# -*- coding: utf-8 -*-
"""Cold simulation event ledger — Phase 3 (archive-ready, not merchant hot path)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import SimulationEventLedger
from services.store_reality_simulator.planner_v1 import PlannedEvent, RealityPlan


def persist_plan_to_ledger(plan: RealityPlan) -> int:
    """Write planned events as cold ledger rows (idempotent by simulated_event_id)."""
    n = 0
    for ev in plan.events:
        existing = (
            db.session.query(SimulationEventLedger)
            .filter(
                SimulationEventLedger.simulation_run_id == plan.simulation_run_id,
                SimulationEventLedger.simulated_event_id == ev.simulated_event_id,
            )
            .first()
        )
        if existing is not None:
            continue
        row = SimulationEventLedger(
            simulation_run_id=plan.simulation_run_id,
            store_slug="demo",
            simulated_event_id=ev.simulated_event_id,
            event_index=int(ev.event_index),
            event_type=ev.event_type,
            support=ev.support,
            status="planned",
            scenario_id=ev.scenario_id,
            scenario_version=ev.scenario_version,
            scenario_revision=int(ev.scenario_revision),
            simulated_at=ev.simulated_at,
            payload_json=json.dumps(ev.to_dict(), ensure_ascii=False),
            result_json="{}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(row)
        n += 1
    db.session.commit()
    return n


def list_ledger_events(
    simulation_run_id: str,
    *,
    status: Optional[str] = None,
    limit: int = 5000,
) -> list[SimulationEventLedger]:
    q = db.session.query(SimulationEventLedger).filter(
        SimulationEventLedger.simulation_run_id == str(simulation_run_id)
    )
    if status:
        q = q.filter(SimulationEventLedger.status == status)
    return q.order_by(SimulationEventLedger.event_index.asc()).limit(int(limit)).all()


def mark_ledger_result(
    row: SimulationEventLedger | int,
    *,
    status: str,
    result: Optional[dict[str, Any]] = None,
) -> None:
    """Update ledger status on the *current* session (ingress may rotate sessions)."""
    ledger_id: Optional[int]
    simulated_event_id: Optional[str] = None
    if isinstance(row, int):
        ledger_id = row
    else:
        ledger_id = getattr(row, "id", None)
        simulated_event_id = getattr(row, "simulated_event_id", None)

    live: Optional[SimulationEventLedger] = None
    if ledger_id is not None:
        live = db.session.get(SimulationEventLedger, ledger_id)
    if live is None and simulated_event_id:
        live = (
            db.session.query(SimulationEventLedger)
            .filter(SimulationEventLedger.simulated_event_id == str(simulated_event_id))
            .first()
        )
    if live is None:
        return
    live.status = str(status)
    live.result_json = json.dumps(result or {}, ensure_ascii=False)
    live.updated_at = datetime.now(timezone.utc)


def planned_event_from_ledger(row: SimulationEventLedger) -> PlannedEvent:
    data = {}
    try:
        data = json.loads(row.payload_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        data = {}
    at = row.simulated_at
    if at and getattr(at, "tzinfo", None) is None:
        at = at.replace(tzinfo=timezone.utc)
    return PlannedEvent(
        simulated_event_id=row.simulated_event_id,
        event_index=int(row.event_index),
        simulated_at=at or datetime.now(timezone.utc),
        event_type=row.event_type,
        scenario_id=row.scenario_id or "",
        scenario_version=row.scenario_version or "v1",
        scenario_revision=int(row.scenario_revision or 1),
        customer_id=str(data.get("customer_id") or ""),
        session_id=str(data.get("session_id") or ""),
        cart_id=str(data.get("cart_id") or ""),
        recovery_key=str(data.get("recovery_key") or ""),
        product_key=str(data.get("product_key") or ""),
        product_id=str(data.get("product_id") or ""),
        product_price=float(data.get("product_price") or 0),
        reason_tag=str(data.get("reason_tag") or ""),
        customer_phone=str(data.get("customer_phone") or ""),
        archetype=str(data.get("archetype") or ""),
        support=str(row.support or data.get("support") or "supported"),
        payload=dict(data.get("payload") or {}),
    )


def delete_ledger_for_run(simulation_run_id: str) -> int:
    n = (
        db.session.query(SimulationEventLedger)
        .filter(SimulationEventLedger.simulation_run_id == str(simulation_run_id))
        .delete(synchronize_session=False)
    )
    return int(n or 0)
