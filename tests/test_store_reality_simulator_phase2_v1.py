# -*- coding: utf-8 -*-
"""Store Reality Simulator V1 — Phase 2 infrastructure tests (no event generation)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from extensions import db
from models import AbandonedCart, SimulationRowIndex, SimulationRun
import services.recovery_truth_timeline_v1 as recovery_truth_timeline_v1
from services.store_reality_simulator.accounting_v1 import (
    empty_accounting,
    increment_bucket,
    reconcile_accounting,
)
from services.store_reality_simulator.checkpoint_v1 import pause_run, resume_plan
from services.store_reality_simulator.cleanup_v1 import build_cleanup_plan, execute_cleanup
from services.store_reality_simulator.clock_v1 import (
    SimulationClock,
    SystemClock,
    get_clock,
    is_simulation_clock_active,
    reset_clock_to_system,
    utc_now,
)
from services.store_reality_simulator.config_loader_v1 import load_simulation_config
from services.store_reality_simulator.context_v1 import (
    is_simulation_active,
    simulation_scope,
)
from services.store_reality_simulator.contracts_v1 import (
    BUCKET_FAILED,
    BUCKET_PLANNED,
    DEMO_STORE_SLUG,
)
from services.store_reality_simulator.identity_v1 import (
    simulation_cart_id,
    simulation_customer_id,
    simulation_event_id,
    simulation_recovery_key,
    simulation_session_id,
)
from services.store_reality_simulator.progress_v1 import build_progress_monitor
from services.store_reality_simulator.row_index_v1 import register_tagged_row
from services.store_reality_simulator.run_registry_v1 import (
    create_simulation_run,
    get_run,
    pause_run_by_id,
    persist_run,
    resume_run,
)
from services.store_reality_simulator.safe_delivery_adapter_v1 import (
    guard_meta_whatsapp_message,
    guard_send_whatsapp,
    simulation_outbound_guard,
)
from services.store_reality_simulator.scenario_registry_v1 import (
    list_scenarios,
    registry_snapshot,
    require_scenario,
)
from services.store_reality_simulator.seed_v1 import make_rng, normalize_seed
from services.whatsapp_send import send_whatsapp


@pytest.fixture(autouse=True)
def _reset_sim_clock():
    reset_clock_to_system()
    yield
    reset_clock_to_system()


@pytest.fixture
def clean_sim_tables():
    db.session.rollback()
    db.session.query(SimulationRowIndex).delete()
    db.session.query(SimulationRun).delete()
    db.session.query(AbandonedCart).filter(
        AbandonedCart.zid_cart_id.like("%srs_p2%")
    ).delete(synchronize_session=False)
    db.session.commit()
    yield
    db.session.rollback()
    db.session.query(SimulationRowIndex).delete()
    db.session.query(SimulationRun).delete()
    db.session.query(AbandonedCart).filter(
        AbandonedCart.zid_cart_id.like("%srs_p2%")
    ).delete(synchronize_session=False)
    db.session.commit()


def test_system_clock_default():
    assert isinstance(get_clock(), SystemClock)
    assert not is_simulation_clock_active()
    assert abs((utc_now() - datetime.now(timezone.utc)).total_seconds()) < 5


def test_clock_injection_and_timeline_uses_simulation_clock():
    start = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    clock = SimulationClock(start)
    with simulation_scope(
        simulation_run_id="srs_clock_test",
        clock=clock,
        seed=1,
        scenario_ids=["S01_normal_store_baseline"],
    ):
        assert is_simulation_active()
        assert is_simulation_clock_active()
        assert utc_now() == start
        # Patch replaces module attribute; call via module (not a stale import binding)
        assert recovery_truth_timeline_v1._utc_now() == start
        clock.advance(timedelta(days=2, hours=3))
        assert utc_now() == start + timedelta(days=2, hours=3)
        assert recovery_truth_timeline_v1._utc_now() == start + timedelta(
            days=2, hours=3
        )
        assert clock.current_day().isoformat() == "2026-05-03"
    assert not is_simulation_active()
    assert isinstance(get_clock(), SystemClock)
    assert recovery_truth_timeline_v1._utc_now() != start


def test_seed_determinism():
    assert normalize_seed("42") == 42
    a = make_rng(99).sample(range(1000), 20)
    b = make_rng(99).sample(range(1000), 20)
    c = make_rng(100).sample(range(1000), 20)
    assert a == b
    assert a != c


def test_identity_determinism():
    kwargs = dict(
        simulation_run_id="srs_id_run",
        seed=7,
        scenario_id="S03_shipping_cost_hesitation",
        customer_index=3,
    )
    assert simulation_customer_id(**kwargs) == simulation_customer_id(**kwargs)
    assert simulation_session_id(**kwargs, session_index=1) == simulation_session_id(
        **kwargs, session_index=1
    )
    assert simulation_cart_id(**kwargs, cart_index=0) == simulation_cart_id(
        **kwargs, cart_index=0
    )
    assert simulation_event_id(
        simulation_run_id="srs_id_run",
        seed=7,
        scenario_id="S03_shipping_cost_hesitation",
        event_index=10,
        event_type="cart_abandoned",
    ) == simulation_event_id(
        simulation_run_id="srs_id_run",
        seed=7,
        scenario_id="S03_shipping_cost_hesitation",
        event_index=10,
        event_type="cart_abandoned",
    )
    rk = simulation_recovery_key(**kwargs, cart_index=0)
    assert rk.startswith("demo:srs_")


def test_config_loader_demo_only_and_scenarios(clean_sim_tables):
    cfg = load_simulation_config(
        {
            "store_slug": "demo",
            "scenario_ids": ["S01_normal_store_baseline", "S03_shipping_cost_hesitation"],
            "seed": 11,
            "start_date": "2026-05-01",
            "duration_days": 3,
            "scale": 1.0,
        }
    )
    assert cfg.store_slug == DEMO_STORE_SLUG
    assert cfg.seed == 11
    assert cfg.duration_days == 3
    with pytest.raises(ValueError):
        load_simulation_config(
            {
                "store_slug": "merchant_x",
                "scenario_ids": ["S01_normal_store_baseline"],
                "seed": 1,
                "start_date": "2026-05-01",
                "duration_days": 3,
            }
        )
    with pytest.raises(KeyError):
        load_simulation_config(
            {
                "scenario_ids": ["S99_not_real"],
                "seed": 1,
                "start_date": "2026-05-01",
                "duration_days": 3,
            }
        )


def test_scenario_registry_no_execution():
    snap = registry_snapshot()
    assert snap["execution_implemented"] is True  # Phase 3 Reality Engine
    assert len(list_scenarios()) == 20
    assert require_scenario("S16_insufficient_data").name


def test_run_persistence_and_accounting_init(clean_sim_tables):
    row = create_simulation_run(
        {
            "scenario_ids": ["S01_normal_store_baseline"],
            "seed": 5,
            "start_date": "2026-05-01",
            "duration_days": 3,
        }
    )
    assert row.simulation_run_id.startswith("srs_")
    assert row.store_slug == "demo"
    assert row.status == "created"
    loaded = get_run(row.simulation_run_id)
    assert loaded is not None
    assert loaded.seed == 5
    acc = empty_accounting()
    assert acc[BUCKET_PLANNED] == 0
    acc = increment_bucket(acc, BUCKET_PLANNED, 10)
    acc = increment_bucket(acc, BUCKET_FAILED, 2)
    recon = reconcile_accounting(acc)
    assert recon["planned"] == 10
    assert "delta" in recon


def test_checkpoint_pause_resume(clean_sim_tables):
    row = create_simulation_run(
        {
            "scenario_ids": ["S03_shipping_cost_hesitation"],
            "seed": 2,
            "start_date": "2026-05-01",
            "duration_days": 3,
        }
    )
    row.current_step = 4
    persist_run(row)
    pause_run_by_id(row.simulation_run_id, reason="test_pause")
    paused = get_run(row.simulation_run_id)
    assert paused is not None
    assert paused.status == "paused"
    plan = resume_plan(paused)
    assert plan["ok"] is True
    assert plan["resume_available"] is True
    resumed = resume_run(row.simulation_run_id)
    assert resumed["ok"] is True
    assert get_run(row.simulation_run_id).status == "running"


def test_progress_monitor(clean_sim_tables):
    row = create_simulation_run(
        {
            "scenario_ids": ["S01_normal_store_baseline"],
            "seed": 3,
            "start_date": "2026-05-01",
            "duration_days": 3,
        }
    )
    mon = build_progress_monitor(row)
    assert mon["event_generation_enabled"] is False
    assert mon["seed"] == 3
    assert mon["accounting"][BUCKET_PLANNED] == 0


def test_safe_delivery_adapter_intercepts_and_blocks_non_demo():
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    with simulation_scope(
        simulation_run_id="srs_safe_1",
        clock=SimulationClock(start),
        seed=1,
        scenario_ids=["S01_normal_store_baseline"],
    ):
        blocked = simulation_outbound_guard(store_slug="other_store", channel="whatsapp")
        assert blocked is not None
        assert blocked["ok"] is False
        assert blocked["error"] == "simulation_non_demo_rejected"

        mock = guard_send_whatsapp(store_slug="demo", reason_tag="price")
        assert mock is not None
        assert mock["ok"] is True
        assert mock["provider_called"] is False
        assert mock["external_api_called"] is False
        assert mock["provider_suppressed_simulation"] is True

        meta = guard_meta_whatsapp_message()
        assert meta is not None
        assert meta[0] is True
        assert str(meta[2]).startswith("SIM_META_")

        # Real send_whatsapp entry must not reach Twilio
        out = send_whatsapp(
            "966500000000",
            "test",
            reason_tag="price",
            wa_trace_store_slug="demo",
        )
        assert out.get("simulation") is True
        assert out.get("provider_suppressed_simulation") is True

    # Outside simulation — adapter returns None (production path)
    assert guard_send_whatsapp(store_slug="demo") is None


def test_demo_store_protection_on_context():
    with pytest.raises(ValueError):
        with simulation_scope(
            simulation_run_id="srs_bad",
            clock=SimulationClock(datetime(2026, 5, 1, tzinfo=timezone.utc)),
            store_slug="not_demo",
        ):
            pass


def test_cleanup_isolation_tagged_only(clean_sim_tables):
    run = create_simulation_run(
        {
            "scenario_ids": ["S01_normal_store_baseline"],
            "seed": 9,
            "start_date": "2026-05-01",
            "duration_days": 1,
        }
    )
    suffix = uuid.uuid4().hex[:10]
    # Untagged demo cart — must survive cleanup
    other = AbandonedCart(
        zid_cart_id=f"untagged_demo_cart_srs_p2_{suffix}",
        status="detected",
        cart_value=10.0,
        recovery_session_id="untagged_demo_session",
    )
    db.session.add(other)
    db.session.commit()
    other_id = other.id

    tagged = AbandonedCart(
        zid_cart_id=f"tagged_demo_cart_srs_p2_{suffix}",
        status="detected",
        cart_value=20.0,
        recovery_session_id="srs_tagged_session",
    )
    db.session.add(tagged)
    db.session.commit()
    tagged_id = int(tagged.id)
    register_tagged_row(
        simulation_run_id=run.simulation_run_id,
        table_name="abandoned_carts",
        row_pk=str(tagged_id),
    )
    db.session.commit()

    plan = build_cleanup_plan(run.simulation_run_id)
    assert plan["ok"] is True
    assert plan["strategy"] == "tagged_only"
    assert plan["broad_demo_cleanup"] is False
    assert plan["tables"].get("abandoned_carts") == 1

    dry = execute_cleanup(run.simulation_run_id, dry_run=True)
    assert dry["dry_run"] is True
    assert db.session.get(AbandonedCart, tagged_id) is not None

    executed = execute_cleanup(run.simulation_run_id, dry_run=False)
    assert executed["dry_run"] is False
    assert executed["deleted"].get("abandoned_carts") == 1
    db.session.expire_all()
    assert db.session.get(AbandonedCart, tagged_id) is None
    assert db.session.get(AbandonedCart, other_id) is not None
    assert get_run(run.simulation_run_id).status == "cleaned"

    # cleanup other cart
    leftover = db.session.get(AbandonedCart, other_id)
    if leftover is not None:
        db.session.delete(leftover)
        db.session.commit()


def test_restart_recovery_via_checkpoint(clean_sim_tables):
    row = create_simulation_run(
        {
            "scenario_ids": ["S01_normal_store_baseline"],
            "seed": 4,
            "start_date": "2026-05-01",
            "duration_days": 3,
        }
    )
    row.current_step = 12
    persist_run(row)
    pause_run(row, reason="process_interrupt")
    persist_run(row)
    # Simulate process restart: reload from DB
    reloaded = get_run(row.simulation_run_id)
    plan = resume_plan(reloaded)
    assert plan["from_step"] == 12
    assert plan["event_generation_enabled"] is False
