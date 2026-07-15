# -*- coding: utf-8 -*-
"""Phase 3.1 — Store Reality Simulator identity isolation verification."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from extensions import db
from models import (
    AbandonedCart,
    PurchaseTruthRecord,
    RecoverySchedule,
    SimulationEventLedger,
    SimulationRowIndex,
    SimulationRun,
    SimulationRunArchive,
    Store,
)
from services.store_reality_simulator.cleanup_v1 import execute_cleanup
from services.store_reality_simulator.clock_v1 import SimulationClock
from services.store_reality_simulator.context_v1 import simulation_scope
from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG
from services.store_reality_simulator.identity_guard_v1 import (
    CRITICAL_ISOLATION_FAILURE,
    SimulationIdentityIsolationError,
    assert_recovery_key_isolated,
    assert_written_store_is_demo,
    predict_purchase_truth_escape,
    require_simulation_write_identity,
)
from services.store_reality_simulator.ingress_adapter_v1 import execute_planned_event
from services.store_reality_simulator.planner_v1 import PlannedEvent
from services.store_reality_simulator.reality_engine_v1 import (
    dry_run_reality,
    execute_reality_run,
)
from services.store_reality_simulator.performance_guards_v1 import PerformanceThresholds
from services.recovery_store_context import resolve_purchase_truth_store_slug


@pytest.fixture
def clean_srs():
    from services.store_reality_simulator.schema_v1 import ensure_srs_phase3_schema

    ensure_srs_phase3_schema()
    db.session.rollback()
    db.session.query(PurchaseTruthRecord).filter(
        PurchaseTruthRecord.purchase_source == "store_reality_simulator"
    ).delete(synchronize_session=False)
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
    db.session.query(PurchaseTruthRecord).filter(
        PurchaseTruthRecord.purchase_source == "store_reality_simulator"
    ).delete(synchronize_session=False)
    for model in (
        SimulationEventLedger,
        SimulationRowIndex,
        SimulationRunArchive,
        SimulationRun,
    ):
        db.session.query(model).delete()
    db.session.commit()


def _ensure_demo_and_linked_alias():
    """Reproduce the known risk: demo alias may point at a real Zid store."""
    demo = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    if demo is None:
        demo = Store(zid_store_id="demo", is_active=True, whatsapp_recovery_enabled=False)
        db.session.add(demo)
        db.session.flush()
    linked = (
        db.session.query(Store)
        .filter(Store.zid_store_id == "zid_iso_merchant_test_abc")
        .first()
    )
    if linked is None:
        linked = Store(
            zid_store_id="zid_iso_merchant_test_abc",
            is_active=True,
            whatsapp_recovery_enabled=False,
        )
        db.session.add(linked)
        db.session.flush()
    try:
        from services.store_identity_v1 import register_store_identity_alias

        register_store_identity_alias(
            store_id=int(linked.id),
            alias_kind="cartflow_zid",
            alias_value="demo",
            platform="cartflow",
        )
    except Exception:  # noqa: BLE001
        pass
    db.session.commit()
    return demo, linked


def test_identity_guard_requires_demo_and_run_id():
    with pytest.raises(SimulationIdentityIsolationError) as missing_run:
        require_simulation_write_identity(store_slug="demo", simulation_run_id="")
    assert missing_run.value.reason == "missing_simulation_run_id"

    with pytest.raises(SimulationIdentityIsolationError) as bad_slug:
        require_simulation_write_identity(
            store_slug="zid_iso_merchant_test_abc",
            simulation_run_id="srs_test",
        )
    assert bad_slug.value.reason == "non_demo_store_slug"
    assert CRITICAL_ISOLATION_FAILURE in str(bad_slug.value)

    ok = require_simulation_write_identity(
        store_slug="demo", simulation_run_id="srs_ok"
    )
    assert ok["store_slug"] == DEMO_STORE_SLUG


def test_recovery_key_must_be_demo_prefixed():
    with pytest.raises(SimulationIdentityIsolationError):
        assert_recovery_key_isolated("zid_iso_merchant_test_abc:sess1")
    assert assert_recovery_key_isolated("demo:srs_abc") == "demo:srs_abc"


def test_written_store_assertion():
    with pytest.raises(SimulationIdentityIsolationError) as exc:
        assert_written_store_is_demo("zid_iso_merchant_test_abc", surface="test")
    assert exc.value.reason == "written_store_escape"
    assert assert_written_store_is_demo("demo", surface="test") == "demo"


def test_invalid_merchant_config_aborts(clean_srs):
    from services.store_reality_simulator.config_loader_v1 import load_simulation_config

    with pytest.raises(ValueError, match="demo_only"):
        load_simulation_config(
            {
                "store_slug": "real_merchant",
                "scenario_ids": ["S01_normal_store_baseline"],
                "seed": 1,
                "start_date": "2026-05-01",
                "duration_days": 1,
            }
        )


def test_duplicate_identity_rejection_alias_does_not_escape_purchase(clean_srs):
    """Without pin, alias may remap demo→zid; with active simulation, must stay demo."""
    _ensure_demo_and_linked_alias()
    rk = "demo:srs_iso_sess_cart_1"
    pred = predict_purchase_truth_escape(
        recovery_key=rk, payload_store_slug="demo"
    )
    # Prediction (no sim context) documents the platform remap risk when alias exists
    # (may or may not escape depending on fixture alias ownership — record outcome)
    assert "would_escape" in pred

    clock = SimulationClock(start=datetime(2026, 5, 1, tzinfo=timezone.utc))
    with simulation_scope(
        simulation_run_id="srs_iso_pin",
        clock=clock,
        seed=1,
        store_slug="demo",
    ):
        resolved = resolve_purchase_truth_store_slug(
            recovery_key=rk, payload_store_slug="demo"
        )
        assert resolved == DEMO_STORE_SLUG


def test_no_purchase_truth_remapping_during_simulation(clean_srs):
    _ensure_demo_and_linked_alias()
    planned = dry_run_reality(
        {
            "scenario_ids": ["S13_organic_purchase"],
            "seed": 21,
            "start_date": "2026-05-01",
            "scale_profile": "small",
            "mode": "execute",
        }
    )
    run_id = planned["simulation_run_id"]
    row = db.session.query(SimulationRun).filter_by(simulation_run_id=run_id).one()
    row.status = "created"
    db.session.commit()

    result = execute_reality_run(
        run_id,
        max_batches=20,
        thresholds=PerformanceThresholds(batch_wall_ms_max=180_000.0),
    )
    assert result["ok"] is True

    pts = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.purchase_source == "store_reality_simulator")
        .all()
    )
    assert pts, "expected at least one purchase truth row"
    for pt in pts:
        assert pt.store_slug == DEMO_STORE_SLUG, pt.store_slug
        assert str(pt.recovery_key).startswith("demo:")


def test_ingress_rejects_missing_run_id_and_bad_recovery_key(clean_srs):
    clock = SimulationClock(start=datetime(2026, 5, 1, tzinfo=timezone.utc))
    ev = PlannedEvent(
        simulated_event_id="srs_evt_iso_1",
        event_index=0,
        simulated_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        event_type="cart_state_sync",
        scenario_id="S01_normal_store_baseline",
        scenario_version="v1",
        scenario_revision=1,
        customer_id="srs_cust_1",
        session_id="srs_sess_1",
        cart_id="srs_cart_iso1",
        recovery_key="merchant_x:sess",
        product_key="sku",
        product_id="demo_sku",
        product_price=10.0,
        reason_tag="",
        customer_phone="",
        archetype="browser",
        support="supported",
        payload={},
    )
    with simulation_scope(
        simulation_run_id="srs_iso_reject",
        clock=clock,
        seed=1,
        store_slug="demo",
    ):
        out = execute_planned_event(ev, simulation_run_id="srs_iso_reject", seed=1)
        assert out["ok"] is False
        assert out.get("isolation_failure") is True
        assert out["error"] == "recovery_key_not_demo_prefixed"

        ev_ok_key = PlannedEvent(
            simulated_event_id="srs_evt_iso_2",
            event_index=1,
            simulated_at=datetime(2026, 5, 1, 12, 1, tzinfo=timezone.utc),
            event_type="cart_state_sync",
            scenario_id="S01_normal_store_baseline",
            scenario_version="v1",
            scenario_revision=1,
            customer_id="srs_cust_1",
            session_id="srs_sess_1",
            cart_id="srs_cart_iso2",
            recovery_key="demo:srs_ok_key",
            product_key="sku",
            product_id="demo_sku",
            product_price=10.0,
            reason_tag="",
            customer_phone="",
            archetype="browser",
            support="supported",
            payload={},
        )
        out2 = execute_planned_event(ev_ok_key, simulation_run_id="", seed=1)
        assert out2["ok"] is False
        assert out2.get("isolation_failure") is True
        assert out2["error"] == "missing_simulation_run_id"


def test_cleanup_removes_only_tagged_simulation_rows(clean_srs):
    _ensure_demo_and_linked_alias()
    # Untouched demo row (must survive cleanup)
    demo_store = db.session.query(Store).filter_by(zid_store_id="demo").one()
    keeper = (
        db.session.query(AbandonedCart)
        .filter_by(zid_cart_id="keeper_cart_not_sim")
        .first()
    )
    if keeper is None:
        keeper = AbandonedCart(
            store_id=int(demo_store.id),
            zid_cart_id="keeper_cart_not_sim",
            status="abandoned",
            cart_value=1.0,
            recovery_session_id="keeper_sess",
        )
        db.session.add(keeper)
        db.session.commit()
    keeper_id = keeper.id

    planned = dry_run_reality(
        {
            "scenario_ids": ["S13_organic_purchase"],
            "seed": 33,
            "start_date": "2026-05-01",
            "scale_profile": "small",
            "mode": "execute",
        }
    )
    run_id = planned["simulation_run_id"]
    row = db.session.query(SimulationRun).filter_by(simulation_run_id=run_id).one()
    row.status = "created"
    db.session.commit()
    execute_reality_run(
        run_id,
        max_batches=20,
        thresholds=PerformanceThresholds(batch_wall_ms_max=180_000.0),
    )

    tagged_before = (
        db.session.query(SimulationRowIndex)
        .filter_by(simulation_run_id=run_id)
        .count()
    )
    assert tagged_before >= 1

    pt_pks = [
        t.row_pk
        for t in db.session.query(SimulationRowIndex)
        .filter_by(simulation_run_id=run_id, table_name="purchase_truth_records")
        .all()
    ]
    cleaned = execute_cleanup(run_id, dry_run=False)
    assert cleaned["ok"] is True

    for pk in pt_pks:
        assert db.session.get(PurchaseTruthRecord, int(pk)) is None
    assert (
        db.session.query(SimulationRowIndex)
        .filter_by(simulation_run_id=run_id)
        .count()
        == 0
    )
    # Keeper untouched
    assert db.session.get(AbandonedCart, keeper_id) is not None
    # Linked merchant store untouched
    assert (
        db.session.query(Store)
        .filter_by(zid_store_id="zid_iso_merchant_test_abc")
        .count()
        == 1
    )


def test_timeline_and_schedule_isolation(clean_srs):
    clock = SimulationClock(start=datetime(2026, 5, 1, tzinfo=timezone.utc))
    ev = PlannedEvent(
        simulated_event_id="srs_evt_sched",
        event_index=0,
        simulated_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        event_type="whatsapp_scheduled",
        scenario_id="S06_wa_success",
        scenario_version="v1",
        scenario_revision=1,
        customer_id="srs_cust_s",
        session_id="srs_sess_s",
        cart_id="srs_cart_s",
        recovery_key="demo:srs_sched_1",
        product_key="sku",
        product_id="demo_sku",
        product_price=50.0,
        reason_tag="price",
        customer_phone="966500000001",
        archetype="hesitator",
        support="supported",
        payload={},
    )
    with simulation_scope(
        simulation_run_id="srs_iso_sched",
        clock=clock,
        seed=2,
        store_slug="demo",
    ):
        out = execute_planned_event(ev, simulation_run_id="srs_iso_sched", seed=2)
        assert out["ok"] is True
    sched = (
        db.session.query(RecoverySchedule)
        .filter_by(recovery_key="demo:srs_sched_1")
        .one()
    )
    assert sched.store_slug == DEMO_STORE_SLUG


def test_provider_outbound_never_on_non_demo():
    from services.store_reality_simulator.safe_delivery_adapter_v1 import (
        simulation_outbound_guard,
    )

    clock = SimulationClock(start=datetime(2026, 5, 1, tzinfo=timezone.utc))
    with simulation_scope(
        simulation_run_id="srs_iso_wa",
        clock=clock,
        seed=1,
        store_slug="demo",
    ):
        rejected = simulation_outbound_guard(
            store_slug="zid_iso_merchant_test_abc", channel="whatsapp"
        )
        assert rejected is not None
        assert rejected.get("error") == "simulation_non_demo_rejected"
        ok = simulation_outbound_guard(store_slug="demo", channel="whatsapp")
        assert ok is not None
        assert ok.get("mock") is True


def test_knowledge_dashboard_monthly_surfaces_do_not_inject_from_simulator():
    """Simulator never writes Knowledge/Dashboard/Monthly — only source events."""
    import services.store_reality_simulator.ingress_adapter_v1 as ingress
    import services.store_reality_simulator.reality_engine_v1 as engine

    for mod in (ingress, engine):
        src = open(mod.__file__, encoding="utf-8").read()
        assert "merchant_home" not in src
        assert "monthly_summary" not in src
        assert "knowledge_layer_v" not in src
        assert "dashboard_snapshot" not in src
        assert "inject_confidence" not in src
