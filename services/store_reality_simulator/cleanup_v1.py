# -*- coding: utf-8 -*-
"""
Tagged-only cleanup engine — Phase 2.

Deletes only rows registered under simulation_run_id.
Never broad demo cleanup. Never timestamp-based deletion.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from extensions import db
from models import (
    AbandonedCart,
    AbandonmentReasonLog,
    CartRecoveryLog,
    CartRecoveryReason,
    LifecycleClosureRecord,
    MovementSnapshot,
    PurchaseTruthRecord,
    RecoverySchedule,
    RecoveryTruthTimelineEvent,
    SimulationRowIndex,
    SimulationRun,
)
from services.store_reality_simulator.contracts_v1 import (
    DEMO_STORE_SLUG,
    STATUS_CLEANED,
    assert_demo_store,
)
from services.store_reality_simulator.row_index_v1 import list_tagged_rows
from services.store_reality_simulator.run_registry_v1 import get_run, require_run

# Allowed cleanup targets only — explicit allowlist (no wild deletes)
_TABLE_DELETERS: dict[str, Callable[[str], int]] = {}


def _register(table: str, fn: Callable[[str], int]) -> None:
    _TABLE_DELETERS[table] = fn


def _delete_by_pk(model: Any, pk_attr: str, row_pk: str) -> int:
    col = getattr(model, pk_attr)
    # Prefer integer pk when numeric
    try:
        if pk_attr == "id":
            q = db.session.query(model).filter(col == int(row_pk))
        else:
            q = db.session.query(model).filter(col == row_pk)
    except (TypeError, ValueError):
        q = db.session.query(model).filter(col == row_pk)
    n = q.delete(synchronize_session=False)
    return int(n or 0)


def _init_deleters() -> None:
    if _TABLE_DELETERS:
        return
    _register("abandoned_carts", lambda pk: _delete_by_pk(AbandonedCart, "id", pk))
    _register("cart_recovery_logs", lambda pk: _delete_by_pk(CartRecoveryLog, "id", pk))
    _register(
        "cart_recovery_reasons", lambda pk: _delete_by_pk(CartRecoveryReason, "id", pk)
    )
    _register(
        "abandonment_reason_logs",
        lambda pk: _delete_by_pk(AbandonmentReasonLog, "id", pk),
    )
    _register("recovery_schedules", lambda pk: _delete_by_pk(RecoverySchedule, "id", pk))
    _register(
        "recovery_truth_timeline_events",
        lambda pk: _delete_by_pk(RecoveryTruthTimelineEvent, "id", pk),
    )
    _register(
        "purchase_truth_records",
        lambda pk: _delete_by_pk(PurchaseTruthRecord, "id", pk),
    )
    _register(
        "lifecycle_closure_records",
        lambda pk: _delete_by_pk(LifecycleClosureRecord, "id", pk),
    )
    _register("movement_snapshots", lambda pk: _delete_by_pk(MovementSnapshot, "id", pk))


def build_cleanup_plan(simulation_run_id: str) -> dict[str, Any]:
    _init_deleters()
    run_id = str(simulation_run_id or "").strip()
    row = get_run(run_id)
    if row is None:
        return {
            "ok": False,
            "error": "simulation_run_not_found",
            "simulation_run_id": run_id,
        }
    assert_demo_store(getattr(row, "store_slug", DEMO_STORE_SLUG))

    tagged = list_tagged_rows(run_id)
    by_table: dict[str, list[str]] = {}
    unknown_tables: list[str] = []
    for t in tagged:
        table = str(t.table_name or "").strip()
        pk = str(t.row_pk or "").strip()
        if table not in _TABLE_DELETERS:
            unknown_tables.append(table)
            continue
        by_table.setdefault(table, []).append(pk)

    return {
        "ok": True,
        "simulation_run_id": run_id,
        "store_slug": DEMO_STORE_SLUG,
        "strategy": "tagged_only",
        "indexed_row_count": len(tagged),
        "tables": {k: len(v) for k, v in sorted(by_table.items())},
        "row_pks_by_table": by_table,
        "unknown_tables": sorted(set(unknown_tables)),
        "will_mark_run_cleaned": True,
        "will_clear_row_index": True,
        "broad_demo_cleanup": False,
        "timestamp_based": False,
    }


def execute_cleanup(
    simulation_run_id: str,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    plan = build_cleanup_plan(simulation_run_id)
    if not plan.get("ok"):
        return plan

    report: dict[str, Any] = {
        "ok": True,
        "dry_run": bool(dry_run),
        "simulation_run_id": plan["simulation_run_id"],
        "strategy": "tagged_only",
        "planned": plan,
        "deleted": {},
        "index_rows_removed": 0,
        "run_status": None,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    if dry_run:
        report["note"] = "dry_cleanup — no rows deleted"
        return report

    _init_deleters()
    deleted: dict[str, int] = {}
    for table, pks in (plan.get("row_pks_by_table") or {}).items():
        deleter = _TABLE_DELETERS.get(table)
        if deleter is None:
            continue
        total = 0
        for pk in pks:
            total += deleter(pk)
        deleted[table] = total

    run_id = plan["simulation_run_id"]
    index_removed = (
        db.session.query(SimulationRowIndex)
        .filter(SimulationRowIndex.simulation_run_id == run_id)
        .delete(synchronize_session=False)
    )
    ledger_removed = 0
    try:
        from services.store_reality_simulator.event_ledger_v1 import delete_ledger_for_run

        ledger_removed = delete_ledger_for_run(run_id)
    except Exception:  # noqa: BLE001
        db.session.rollback()

    run_row = require_run(run_id)
    run_row.status = STATUS_CLEANED
    run_row.updated_at = datetime.now(timezone.utc)
    # Preserve run orchestration record for audit; clear mutable work queues
    run_row.warnings_json = json.dumps(
        [
            {
                "cleanup_executed_at": report["executed_at"],
                "deleted": deleted,
                "index_rows_removed": int(index_removed or 0),
                "ledger_rows_removed": int(ledger_removed or 0),
            }
        ],
        ensure_ascii=False,
    )
    db.session.add(run_row)
    db.session.commit()

    report["deleted"] = deleted
    report["index_rows_removed"] = int(index_removed or 0)
    report["ledger_rows_removed"] = int(ledger_removed or 0)
    report["run_status"] = STATUS_CLEANED
    report["note"] = "tagged_cleanup_executed"
    return report
