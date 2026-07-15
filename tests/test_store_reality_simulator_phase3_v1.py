# -*- coding: utf-8 -*-
"""Store Reality Simulator V1 — Phase 3 Reality Engine tests."""
from __future__ import annotations

import json

import pytest

from extensions import db
from models import (
    PurchaseTruthRecord,
    SimulationEventLedger,
    SimulationRowIndex,
    SimulationRun,
    SimulationRunArchive,
)
from services.store_reality_simulator.archive_v1 import archive_run, restore_run_metadata
from services.store_reality_simulator.config_loader_v1 import load_simulation_config
from services.store_reality_simulator.observability_v1 import build_simulation_dashboard
from services.store_reality_simulator.performance_guards_v1 import (
    PerformanceSnapshot,
    PerformanceThresholds,
    evaluate_stop_condition,
)
from services.store_reality_simulator.planner_v1 import build_reality_plan
from services.store_reality_simulator.reality_engine_v1 import (
    dry_run_reality,
    execute_reality_run,
)
from services.store_reality_simulator.reality_score_v1 import compute_reality_score
from services.store_reality_simulator.scale_profiles_v1 import get_scale_profile
from services.store_reality_simulator.scenario_registry_v1 import (
    require_scenario,
    scenario_versions_payload,
)
from services.store_reality_simulator.seed_v1 import normalize_seed


@pytest.fixture
def clean_srs():
    from services.store_reality_simulator.schema_v1 import ensure_srs_phase3_schema

    ensure_srs_phase3_schema()
    db.session.rollback()
    for model in (
        SimulationEventLedger,
        SimulationRowIndex,
        SimulationRunArchive,
        SimulationRun,
    ):
        db.session.query(model).delete()
    db.session.commit()
    yield
    db.session.rollback()
    for model in (
        SimulationEventLedger,
        SimulationRowIndex,
        SimulationRunArchive,
        SimulationRun,
    ):
        db.session.query(model).delete()
    db.session.commit()


def test_scenario_versioning():
    spec = require_scenario("shipping_hesitation")
    assert spec.scenario_id == "S03_shipping_cost_hesitation"
    assert spec.scenario_version == "v1"
    assert spec.scenario_revision == 1
    versions = scenario_versions_payload(["S01_normal_store_baseline", "shipping_hesitation"])
    assert versions[0]["scenario_version"] == "v1"
    assert versions[1]["versioned_id"].startswith("S03_")


def test_planner_determinism(clean_srs):
    from datetime import datetime, timezone

    profile = get_scale_profile("small")
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    a = build_reality_plan(
        simulation_run_id="srs_plan_a",
        seed=42,
        start_date=start,
        duration_days=3,
        scenario_ids=["S01_normal_store_baseline", "S03_shipping_cost_hesitation"],
        scale=profile,
    )
    b = build_reality_plan(
        simulation_run_id="srs_plan_a",
        seed=42,
        start_date=start,
        duration_days=3,
        scenario_ids=["S01_normal_store_baseline", "S03_shipping_cost_hesitation"],
        scale=profile,
    )
    assert [e.simulated_event_id for e in a.events] == [
        e.simulated_event_id for e in b.events
    ]
    assert [e.event_type for e in a.events] == [e.event_type for e in b.events]
    assert a.events[0].simulated_at <= a.events[-1].simulated_at
    assert any(e.support == "unsupported" for e in a.events)
    assert any(e.event_type == "hesitation_reason_selected" for e in a.events)


def test_dry_run_manifest_and_score(clean_srs):
    out = dry_run_reality(
        {
            "scenario_ids": ["S01_normal_store_baseline", "S03_shipping_cost_hesitation"],
            "seed": 7,
            "start_date": "2026-05-01",
            "scale_profile": "small",
        }
    )
    assert out["ok"] is True
    manifest = out["manifest"]
    assert manifest["seed"] == 7
    assert "commit_hash" in manifest
    assert manifest["scenario_versions"]
    assert manifest["expected_event_total"] > 0
    assert out["reality_score"]["merchant_facing"] is False
    assert out["reality_score"]["overall"] > 0
    run_id = out["simulation_run_id"]
    row = db.session.query(SimulationRun).filter_by(simulation_run_id=run_id).one()
    assert row.status == "dry_run"
    ledger_n = (
        db.session.query(SimulationEventLedger)
        .filter_by(simulation_run_id=run_id)
        .count()
    )
    assert ledger_n == manifest["expected_event_total"]


def test_execute_small_run_purchase_truth(clean_srs):
    planned = dry_run_reality(
        {
            "scenario_ids": ["S13_organic_purchase", "S06_wa_success"],
            "seed": 11,
            "start_date": "2026-05-01",
            "scale_profile": "small",
            "mode": "execute",
        }
    )
    run_id = planned["simulation_run_id"]
    # Force execute mode status
    row = db.session.query(SimulationRun).filter_by(simulation_run_id=run_id).one()
    row.status = "created"
    db.session.commit()

    # SQLite + first purchase can warm DB READY (~tens of seconds); do not
    # false-pause the validation run on batch wall time alone.
    result = execute_reality_run(
        run_id,
        max_batches=20,
        thresholds=PerformanceThresholds(batch_wall_ms_max=180_000.0),
    )
    assert result["ok"] is True
    assert result["reality_score"]["overall"] > 0
    assert result["validation_report"]["product_logic_changed"] is False
    assert result["manifest"]["clock_mode"] == "SimulationClock"
    # Phase 3.1: Purchase Truth must remain under demo (no Zid remapping).
    purchases = (
        db.session.query(PurchaseTruthRecord)
        .filter(
            PurchaseTruthRecord.purchase_source == "store_reality_simulator",
            PurchaseTruthRecord.store_slug == "demo",
        )
        .count()
    )
    assert purchases >= 1
    dash = build_simulation_dashboard(run_id)
    assert dash["merchant_facing"] is False
    assert dash["events_generated"] >= 1


def test_performance_guard_pause_reason():
    snap = PerformanceSnapshot(
        pool_exhausted=True,
        consecutive_failures=0,
        batch_wall_ms=10,
        failure_rate=0,
    )
    assert evaluate_stop_condition(snap) == "pool_exhausted"
    snap2 = PerformanceSnapshot(
        pool_exhausted=False,
        batch_wall_ms=999999,
        notes=["pool_not_queuepool_skip_pressure"],
    )
    assert evaluate_stop_condition(snap2) == "batch_latency"


def test_archive_restore(clean_srs):
    out = dry_run_reality(
        {
            "scenario_ids": ["S16_insufficient_data"],
            "seed": 3,
            "start_date": "2026-05-01",
            "scale_profile": "small",
        }
    )
    run_id = out["simulation_run_id"]
    arch = archive_run(run_id)
    assert arch["ok"] is True
    restored = restore_run_metadata(run_id)
    assert restored["ok"] is True
    assert restored["archive"]["replayable"] is True
    assert restored["archive"]["seed"] == 3


def test_scale_profile_config():
    cfg = load_simulation_config(
        {
            "scenario_ids": ["S01_normal_store_baseline"],
            "seed": 1,
            "start_date": "2026-05-01",
            "scale_profile": "medium",
        }
    )
    assert cfg.duration_days == 14
    assert cfg.metadata["scale_profile"] == "medium"


def test_score_internal_only():
    from datetime import datetime, timezone

    plan = build_reality_plan(
        simulation_run_id="srs_score",
        seed=normalize_seed(1),
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        duration_days=3,
        scenario_ids=["S01_normal_store_baseline"],
        scale=get_scale_profile("small"),
    )
    score = compute_reality_score(plan)
    assert score["internal_only"] is True
    assert "dimensions" in score
