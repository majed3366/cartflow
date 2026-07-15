# -*- coding: utf-8 -*-
"""
Tagged row index for cleanup isolation — Phase 2.

Phase 3+ registers operational rows created under a simulation_run_id.
Cleanup deletes only indexed rows + the run itself.
"""
from __future__ import annotations

from typing import Any, Optional

from extensions import db
from models import SimulationRowIndex
from services.store_reality_simulator.clock_v1 import utc_now
from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG, assert_demo_store


def register_tagged_row(
    *,
    simulation_run_id: str,
    table_name: str,
    row_pk: str,
    store_slug: str = DEMO_STORE_SLUG,
) -> SimulationRowIndex:
    assert_demo_store(store_slug)
    run_id = str(simulation_run_id or "").strip()
    table = str(table_name or "").strip()
    pk = str(row_pk or "").strip()
    if not run_id or not table or not pk:
        raise ValueError("tagged_row_identity_incomplete")

    existing = (
        db.session.query(SimulationRowIndex)
        .filter(
            SimulationRowIndex.simulation_run_id == run_id,
            SimulationRowIndex.table_name == table,
            SimulationRowIndex.row_pk == pk,
        )
        .first()
    )
    if existing is not None:
        return existing

    row = SimulationRowIndex(
        simulation_run_id=run_id,
        store_slug=store_slug,
        table_name=table,
        row_pk=pk,
        created_at=utc_now(),
    )
    db.session.add(row)
    return row


def list_tagged_rows(simulation_run_id: str) -> list[SimulationRowIndex]:
    run_id = str(simulation_run_id or "").strip()
    if not run_id:
        return []
    return (
        db.session.query(SimulationRowIndex)
        .filter(SimulationRowIndex.simulation_run_id == run_id)
        .order_by(SimulationRowIndex.id.asc())
        .all()
    )


def count_tagged_rows(simulation_run_id: str) -> int:
    run_id = str(simulation_run_id or "").strip()
    if not run_id:
        return 0
    return (
        db.session.query(SimulationRowIndex)
        .filter(SimulationRowIndex.simulation_run_id == run_id)
        .count()
    )
