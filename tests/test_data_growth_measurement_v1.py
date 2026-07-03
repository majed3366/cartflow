# -*- coding: utf-8 -*-
"""Data Growth Measurement v1 — read-only table metrics tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import main
from extensions import db
from models import (
    AbandonedCart,
    CartRecoveryLog,
    DashboardSnapshot,
    RecoveryTruthTimelineEvent,
    Store,
)
from services.dashboard_snapshot_v1 import SNAPSHOT_TYPE_NORMAL_CARTS
from services.data_growth_measurement_v1 import (
    assess_dashboard_snapshot_accumulation,
    build_data_growth_measurement_report,
)


def _reset_db() -> None:
    for model in (
        DashboardSnapshot,
        RecoveryTruthTimelineEvent,
        CartRecoveryLog,
        AbandonedCart,
        Store,
    ):
        db.session.query(model).delete()
    db.session.commit()


@pytest.fixture()
def client() -> TestClient:
    _reset_db()
    return TestClient(main.app)


def _seed_store(slug: str) -> Store:
    st = Store(zid_store_id=f"zid-{slug}", is_active=True)
    db.session.add(st)
    db.session.commit()
    return st


def test_snapshot_accumulation_counts_historical_only() -> None:
    _reset_db()
    _seed_store("measure-store")
    now = datetime.now(timezone.utc)
    for ver in (1, 2, 3):
        db.session.add(
            DashboardSnapshot(
                store_slug="measure-store",
                snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
                payload_json='{"rows":[]}',
                generated_at=now,
                expires_at=now + timedelta(seconds=45),
                version=ver,
                status="active",
            )
        )
    db.session.commit()

    acc = assess_dashboard_snapshot_accumulation(db.session)
    assert acc["total_rows"] == 3
    assert acc["historical_only_rows"] == 2
    assert acc["rows_read_in_practice_estimate"] == 1
    assert acc["rows_ignored_estimate"] == 2
    assert acc["latest_row_per_store_type_count"] == 1
    assert acc["append_only_accumulation_confirmed"] is True
    assert acc["historical_pct"] == pytest.approx(66.67, abs=0.1)


def test_build_report_includes_log_density(client: TestClient) -> None:
    _reset_db()
    _seed_store("log-store")
    rk = "log-store:s_sess"
    now = datetime.now(timezone.utc)
    for i in range(4):
        db.session.add(
            RecoveryTruthTimelineEvent(
                recovery_key=rk,
                store_slug="log-store",
                session_id="s_sess",
                status=f"status_{i}",
                source="test",
                created_at=now,
            )
        )
    for i in range(6):
        db.session.add(
            CartRecoveryLog(
                store_slug="log-store",
                session_id="s_sess",
                recovery_key=rk,
                message="m",
                status="sent_real",
                created_at=now,
            )
        )
    db.session.commit()

    report = build_data_growth_measurement_report(db.session)
    assert report["ok"] is True
    tl = report["log_growth"]["recovery_truth_timeline_events"]
    logs = report["log_growth"]["cart_recovery_logs"]
    assert tl["total_rows"] == 4
    assert tl["distinct_recovery_keys"] == 1
    assert tl["avg_rows_per_recovery_key"] == 4.0
    assert logs["total_rows"] == 6
    assert logs["avg_rows_per_recovery_key"] == 6.0


def test_dev_data_growth_measurement_endpoint(client: TestClient) -> None:
    _reset_db()
    _seed_store("dev-endpoint-store")
    resp = client.get("/dev/data-growth-measurement")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert isinstance(body["tables"], list)
    assert "archive_readiness_priority" in body
    assert "growth_risk_score" in body
    assert body.get("read_only") is True
    assert body.get("endpoint") == "/dev/data-growth-measurement"
