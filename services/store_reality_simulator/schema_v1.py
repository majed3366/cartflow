# -*- coding: utf-8 -*-
"""Ensure Phase 3 simulator tables/columns exist (tests + soft-provision)."""
from __future__ import annotations

from sqlalchemy import inspect, text

from extensions import db
from models import SimulationEventLedger, SimulationRunArchive


def ensure_srs_phase3_schema() -> None:
    bind = db.engine
    insp = inspect(bind)
    tables = set(insp.get_table_names())
    if "simulation_event_ledger" not in tables:
        SimulationEventLedger.__table__.create(bind=bind, checkfirst=True)
    if "simulation_run_archives" not in tables:
        SimulationRunArchive.__table__.create(bind=bind, checkfirst=True)
    if "simulation_runs" not in tables:
        return
    cols = {c["name"] for c in insp.get_columns("simulation_runs")}
    statements = []
    for name, ddl in (
        ("scale_profile", "VARCHAR(32)"),
        ("manifest_json", "TEXT"),
        ("reality_score_json", "TEXT"),
        ("validation_report_json", "TEXT"),
        ("plan_summary_json", "TEXT"),
        ("throttle_state_json", "TEXT"),
        ("archived_at", "DATETIME"),
    ):
        if name not in cols:
            statements.append(
                f"ALTER TABLE simulation_runs ADD COLUMN {name} {ddl}"
            )
    if not statements:
        return
    with bind.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
