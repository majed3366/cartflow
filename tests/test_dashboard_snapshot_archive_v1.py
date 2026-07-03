# -*- coding: utf-8 -*-
"""Dashboard Snapshot Archive v1 — Data Growth Governance Phase 3 tests."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import main
from extensions import db
from models import DashboardSnapshot, DashboardSnapshotArchive
from services.dashboard_snapshot_archive_v1 import (
    ENV_ARCHIVE_ENABLED,
    ENV_BATCH_SIZE,
    ENV_MAX_BATCHES_PER_TICK,
    ENV_RETENTION_DAYS,
    ENV_TICK_MAX_SECONDS,
    assess_dashboard_snapshot_archive_status,
    count_archive_eligible_rows,
    resolve_latest_snapshot_ids,
    run_dashboard_snapshot_archive_tick,
)
from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_SUMMARY,
    fetch_latest_snapshot_row,
)


def _reset_tables() -> None:
    db.session.query(DashboardSnapshotArchive).delete()
    db.session.query(DashboardSnapshot).delete()
    db.session.commit()


def _add_snapshot(
    *,
    store_slug: str,
    snapshot_type: str,
    generated_at: datetime,
    version: int,
    payload: dict | None = None,
) -> DashboardSnapshot:
    now = datetime.now(timezone.utc)
    row = DashboardSnapshot(
        store_slug=store_slug,
        snapshot_type=snapshot_type,
        payload_json=json.dumps(payload or {"v": version}, ensure_ascii=False),
        generated_at=generated_at,
        expires_at=generated_at + timedelta(seconds=120),
        version=version,
        status="active",
        created_at=generated_at,
        updated_at=generated_at,
    )
    db.session.add(row)
    db.session.commit()
    db.session.refresh(row)
    return row


@pytest.fixture(autouse=True)
def _env_archive_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_ARCHIVE_ENABLED, "1")
    monkeypatch.setenv(ENV_RETENTION_DAYS, "30")
    monkeypatch.setenv(ENV_BATCH_SIZE, "100")
    monkeypatch.setenv(ENV_TICK_MAX_SECONDS, "30")
    monkeypatch.setenv("SECRET_KEY", "unit-test-dashboard-snapshot-archive")
    _reset_tables()
    yield
    os.environ.pop(ENV_ARCHIVE_ENABLED, None)
    _reset_tables()


def test_latest_snapshot_is_never_archived() -> None:
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=60)
    latest = _add_snapshot(
        store_slug="store-a",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=old,
        version=2,
        payload={"role": "latest"},
    )
    _add_snapshot(
        store_slug="store-a",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=old - timedelta(days=5),
        version=1,
        payload={"role": "historical"},
    )

    out = run_dashboard_snapshot_archive_tick()
    assert out["ok"] is True
    assert out["rows_archived_this_tick"] == 1

    still = db.session.get(DashboardSnapshot, latest.id)
    assert still is not None
    assert still.version == 2


def test_recent_rollback_window_is_preserved() -> None:
    now = datetime.now(timezone.utc)
    recent_hist = _add_snapshot(
        store_slug="store-b",
        snapshot_type=SNAPSHOT_TYPE_SUMMARY,
        generated_at=now - timedelta(days=10),
        version=1,
    )
    latest = _add_snapshot(
        store_slug="store-b",
        snapshot_type=SNAPSHOT_TYPE_SUMMARY,
        generated_at=now - timedelta(days=1),
        version=2,
    )

    out = run_dashboard_snapshot_archive_tick()
    assert out["rows_archived_this_tick"] == 0

    assert db.session.get(DashboardSnapshot, recent_hist.id) is not None
    assert db.session.get(DashboardSnapshot, latest.id) is not None


def test_old_historical_rows_are_archived() -> None:
    now = datetime.now(timezone.utc)
    old_hist = _add_snapshot(
        store_slug="store-c",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now - timedelta(days=45),
        version=1,
        payload={"keep": "archive"},
    )
    old_id = int(old_hist.id)
    _add_snapshot(
        store_slug="store-c",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now - timedelta(days=2),
        version=2,
    )

    out = run_dashboard_snapshot_archive_tick()
    assert out["rows_archived_this_tick"] == 1
    assert db.session.get(DashboardSnapshot, old_id) is None

    archived = (
        db.session.query(DashboardSnapshotArchive)
        .filter(DashboardSnapshotArchive.source_snapshot_id == old_id)
        .one()
    )
    assert json.loads(archived.payload_json)["keep"] == "archive"


def test_dashboard_read_still_returns_latest_snapshot() -> None:
    now = datetime.now(timezone.utc)
    _add_snapshot(
        store_slug="store-d",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now - timedelta(days=90),
        version=1,
        payload={"stale": True},
    )
    latest = _add_snapshot(
        store_slug="store-d",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now - timedelta(days=50),
        version=2,
        payload={"stale": False},
    )

    run_dashboard_snapshot_archive_tick()
    row = fetch_latest_snapshot_row(
        store_slug="store-d",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
    )
    assert row is not None
    assert row.id == latest.id
    assert json.loads(row.payload_json)["stale"] is False


def test_archive_job_is_bounded_and_resumable(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    for ver in range(1, 8):
        _add_snapshot(
            store_slug="store-e",
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            generated_at=now - timedelta(days=60 + ver),
            version=ver,
        )
    _add_snapshot(
        store_slug="store-e",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now - timedelta(days=1),
        version=8,
    )

    monkeypatch.setenv(ENV_BATCH_SIZE, "2")
    monkeypatch.setenv(ENV_MAX_BATCHES_PER_TICK, "1")

    first = run_dashboard_snapshot_archive_tick()
    assert first["rows_archived_this_tick"] == 2
    assert first["stopped_reason"] == "max_batches"
    assert first["resumable"] is True

    second = run_dashboard_snapshot_archive_tick()
    assert second["rows_archived_this_tick"] == 2

    while db.session.query(DashboardSnapshot).count() > 1:
        run_dashboard_snapshot_archive_tick()
    assert db.session.query(DashboardSnapshot).count() == 1


def test_no_payload_corruption_on_archive() -> None:
    now = datetime.now(timezone.utc)
    payload = {"rows": [{"id": 1, "name": "سلة"}], "meta": {"count": 1}}
    old = _add_snapshot(
        store_slug="store-f",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now - timedelta(days=40),
        version=1,
        payload=payload,
    )
    old_id = int(old.id)
    _add_snapshot(
        store_slug="store-f",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now,
        version=2,
    )

    run_dashboard_snapshot_archive_tick()
    archived = (
        db.session.query(DashboardSnapshotArchive)
        .filter(DashboardSnapshotArchive.source_snapshot_id == old_id)
        .one()
    )
    assert json.loads(archived.payload_json) == payload


@patch("services.dashboard_snapshot_v1.fetch_latest_snapshot_row")
def test_archive_does_not_change_fetch_latest_contract(mock_fetch) -> None:
    """Archive module never patches fetch_latest; guard against accidental wiring."""
    now = datetime.now(timezone.utc)
    _add_snapshot(
        store_slug="store-g",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now - timedelta(days=40),
        version=1,
    )
    _add_snapshot(
        store_slug="store-g",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now,
        version=2,
    )
    run_dashboard_snapshot_archive_tick()
    mock_fetch.assert_not_called()

    # Real fetch still works unchanged
    row = fetch_latest_snapshot_row(
        store_slug="store-g",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
    )
    assert row is not None
    assert row.version == 2


def test_diagnostics_endpoint_read_only() -> None:
    client = TestClient(main.app)
    resp = client.get("/dev/dashboard-snapshot-archive")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("endpoint") == "/dev/dashboard-snapshot-archive"
    assert body.get("read_only") is True
    assert "total_snapshot_rows_hot" in body
    assert "rows_eligible_for_archive" in body


def test_assess_status_counts() -> None:
    now = datetime.now(timezone.utc)
    _add_snapshot(
        store_slug="store-h",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now - timedelta(days=45),
        version=1,
    )
    latest = _add_snapshot(
        store_slug="store-h",
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        generated_at=now,
        version=2,
    )

    latest_ids = resolve_latest_snapshot_ids(db.session)
    assert latest.id in latest_ids
    assert count_archive_eligible_rows(db.session, latest_ids=latest_ids) == 1

    status = assess_dashboard_snapshot_archive_status(db.session)
    assert status["ok"] is True
    assert status["total_snapshot_rows_hot"] == 2
    assert status["latest_rows_kept"] == 1
    assert status["rows_eligible_for_archive"] == 1
