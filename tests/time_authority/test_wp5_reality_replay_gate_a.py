# -*- coding: utf-8 -*-
"""
INV-001 Reality Replay Gate A (after WP-5).

Proves Lab V1-class contrast for demo-like May history:
- Production / July context → Knowledge + Dashboard agree empty for last-7d
- Simulation as-of May end → Knowledge + Dashboard agree non-zero + same windows

Full Lab campaign remains WP-13. This is the frozen Gate A acceptance pack.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from extensions import db
from models import AbandonedCart, Store
from services.dashboard_kpi_time_v1 import (
    merchant_month_window_projection,
    resolve_dashboard_rolling_windows,
)
from services.knowledge_metrics_v1 import collect_knowledge_metrics
from services.knowledge_time_authority_v1 import resolve_knowledge_windows
from services.time_authority import clear_query_time_context, simulation_scope

# Lab V1-class anchors (INV-001 review / Reality Lab Small)
MAY_END = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
JULY_WALL = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
_DEMO = "demo-gate-a-wp5"


def setup_function() -> None:
    clear_query_time_context()


def teardown_function() -> None:
    clear_query_time_context()


def _reset() -> None:
    for model in (AbandonedCart, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()


@pytest.fixture()
def gate_db():
    _reset()
    db.create_all()
    yield
    _reset()


def _seed_may_history() -> Store:
    store = Store(zid_store_id=_DEMO, access_token="t", is_active=True)
    db.session.add(store)
    db.session.commit()
    db.session.refresh(store)
    for i in range(27):
        t = datetime(2026, 5, 1, 8, 0, 0) + timedelta(hours=i * 2)
        db.session.add(
            AbandonedCart(
                store_id=store.id,
                zid_cart_id=f"gate-a-{i}",
                status="abandoned",
                recovery_session_id=f"gate-s-{i}",
                first_seen_at=t,
                last_seen_at=t,
                vip_mode=False,
                cart_value=100.0,
            )
        )
    db.session.commit()
    return store


def test_gate_a_production_empty_simulation_rich_agreement(gate_db) -> None:
    store = _seed_may_history()

    # Production-style July window
    kl_july = collect_knowledge_metrics(
        db.session, _DEMO, window_days=7, now=JULY_WALL
    )
    dash_july = merchant_month_window_projection(store, days=7, now=JULY_WALL)
    w_july_k = resolve_knowledge_windows(window_days=7, now=JULY_WALL)
    w_july_d = resolve_dashboard_rolling_windows(window_days=7, now=JULY_WALL)

    assert (w_july_k.start, w_july_k.end) == (w_july_d.start, w_july_d.end)
    assert kl_july.cart_count == 0
    assert dash_july["abandoned_total"] == 0
    # History exists but is out of window — not a second temporal truth
    assert kl_july.window_start == w_july_k.start
    assert kl_july.window_end == w_july_k.end

    # Simulation freeze at May end
    with simulation_scope(simulation_run_id="srs_gate_a", start=MAY_END):
        kl_may = collect_knowledge_metrics(db.session, _DEMO, window_days=7)
        dash_may = merchant_month_window_projection(store, days=7)
        w_may_k = resolve_knowledge_windows(window_days=7)
        w_may_d = resolve_dashboard_rolling_windows(window_days=7)

    assert (w_may_k.start, w_may_k.end) == (w_may_d.start, w_may_d.end)
    assert kl_may.cart_count == 27
    assert dash_may["abandoned_total"] == 27
    assert w_may_k.context.simulation_run_id == "srs_gate_a"

    evidence = {
        "gate": "A",
        "investigation": "INV-001",
        "after_wp": "WP-5",
        "store_slug": _DEMO,
        "production_july": {
            "knowledge_cart_count": kl_july.cart_count,
            "dashboard_abandoned_total": dash_july["abandoned_total"],
            "window_start": w_july_k.start.isoformat(),
            "window_end": w_july_k.end.isoformat(),
            "windows_equal": True,
        },
        "simulation_may_end": {
            "knowledge_cart_count": kl_may.cart_count,
            "dashboard_abandoned_total": dash_may["abandoned_total"],
            "window_start": w_may_k.start.isoformat(),
            "window_end": w_may_k.end.isoformat(),
            "simulation_run_id": "srs_gate_a",
            "windows_equal": True,
        },
        "verdict": "PASS",
    }
    out_dir = Path("docs/architecture/reality_replay_gate_a_wp5")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "gate_a_evidence.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    assert evidence["verdict"] == "PASS"
