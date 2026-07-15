# -*- coding: utf-8 -*-
"""Archive / restore / delete simulation runs — Phase 3."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import SimulationEventLedger, SimulationRun, SimulationRunArchive
from services.store_reality_simulator.cleanup_v1 import execute_cleanup
from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG, assert_demo_store
from services.store_reality_simulator.event_ledger_v1 import delete_ledger_for_run
from services.store_reality_simulator.run_registry_v1 import get_run, persist_run, require_run


def archive_run(simulation_run_id: str) -> dict[str, Any]:
    row = require_run(simulation_run_id)
    assert_demo_store(row.store_slug)
    ledger = (
        db.session.query(SimulationEventLedger)
        .filter(SimulationEventLedger.simulation_run_id == row.simulation_run_id)
        .order_by(SimulationEventLedger.event_index.asc())
        .all()
    )
    blob = {
        "simulation_run_id": row.simulation_run_id,
        "store_slug": row.store_slug,
        "seed": row.seed,
        "config_json": row.config_json,
        "accounting_json": row.accounting_json,
        "checkpoint_json": row.checkpoint_json,
        "progress_json": row.progress_json,
        "manifest_json": getattr(row, "manifest_json", None),
        "reality_score_json": getattr(row, "reality_score_json", None),
        "validation_report_json": getattr(row, "validation_report_json", None),
        "plan_summary_json": getattr(row, "plan_summary_json", None),
        "scale_profile": getattr(row, "scale_profile", None),
        "scenario_ids_json": row.scenario_ids_json,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "duration_days": row.duration_days,
        "ledger": [
            {
                "simulated_event_id": r.simulated_event_id,
                "event_index": r.event_index,
                "event_type": r.event_type,
                "support": r.support,
                "status": r.status,
                "scenario_id": r.scenario_id,
                "scenario_version": r.scenario_version,
                "scenario_revision": r.scenario_revision,
                "simulated_at": r.simulated_at.isoformat() if r.simulated_at else None,
                "payload_json": r.payload_json,
                "result_json": r.result_json,
            }
            for r in ledger
        ],
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "replayable": True,
    }
    existing = (
        db.session.query(SimulationRunArchive)
        .filter(SimulationRunArchive.simulation_run_id == row.simulation_run_id)
        .first()
    )
    if existing is None:
        existing = SimulationRunArchive(
            simulation_run_id=row.simulation_run_id,
            store_slug=DEMO_STORE_SLUG,
            archive_json=json.dumps(blob, ensure_ascii=False),
            archived_at=datetime.now(timezone.utc),
        )
        db.session.add(existing)
    else:
        existing.archive_json = json.dumps(blob, ensure_ascii=False)
        existing.archived_at = datetime.now(timezone.utc)
        db.session.add(existing)
    row.archived_at = datetime.now(timezone.utc)
    persist_run(row)
    db.session.commit()
    return {
        "ok": True,
        "simulation_run_id": row.simulation_run_id,
        "archived": True,
        "ledger_events": len(ledger),
    }


def restore_run_metadata(simulation_run_id: str) -> dict[str, Any]:
    """Return archived blob for replay planning (does not re-execute)."""
    arch = (
        db.session.query(SimulationRunArchive)
        .filter(SimulationRunArchive.simulation_run_id == str(simulation_run_id))
        .first()
    )
    if arch is None:
        return {"ok": False, "error": "archive_not_found"}
    try:
        blob = json.loads(arch.archive_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"ok": False, "error": "archive_corrupt"}
    return {
        "ok": True,
        "simulation_run_id": simulation_run_id,
        "archive": blob,
        "replayable": True,
    }


def delete_run(simulation_run_id: str, *, dry_run: bool = True) -> dict[str, Any]:
    """
    Tagged cleanup of operational rows + cold ledger.
    Archive blob is preserved unless explicitly removed.
    """
    row = get_run(simulation_run_id)
    if row is None:
        return {"ok": False, "error": "simulation_run_not_found"}
    cleanup = execute_cleanup(simulation_run_id, dry_run=dry_run)
    ledger_n = 0
    if not dry_run:
        ledger_n = delete_ledger_for_run(simulation_run_id)
        db.session.commit()
    return {
        "ok": True,
        "dry_run": dry_run,
        "cleanup": cleanup,
        "ledger_deleted": ledger_n if not dry_run else 0,
        "archive_preserved": True,
    }
