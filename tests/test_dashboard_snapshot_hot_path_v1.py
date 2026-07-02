# -*- coding: utf-8 -*-
"""P0 Dashboard hot path elimination — snapshot read-only API tests."""
from __future__ import annotations

import json
import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import event

from extensions import db
from main import app
from models import DashboardSnapshot
from services.dashboard_snapshot_v1 import (
    ENV_SNAPSHOT_MODE,
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_SUMMARY,
    upsert_dashboard_snapshot,
)


def _enable_snapshot_mode() -> None:
    os.environ["ENV"] = "development"
    os.environ[ENV_SNAPSHOT_MODE] = "1"
    os.environ.setdefault("SECRET_KEY", "unit-test-dashboard-snapshot")


def _clear_snapshot_env() -> None:
    os.environ.pop(ENV_SNAPSHOT_MODE, None)
    os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_BUILDER_ENABLED", None)


def _seed_snapshot(
    *,
    store_slug: str,
    snapshot_type: str,
    payload: dict,
    stale: bool = False,
) -> DashboardSnapshot:
    now = datetime.now(timezone.utc)
    expires = now - timedelta(seconds=30) if stale else now + timedelta(seconds=120)
    generated = now - timedelta(seconds=300) if stale else now
    row = DashboardSnapshot(
        store_slug=store_slug,
        snapshot_type=snapshot_type,
        payload_json=json.dumps(payload, ensure_ascii=False),
        generated_at=generated,
        expires_at=expires,
        version=1,
        status="stale" if stale else "active",
    )
    db.session.add(row)
    db.session.commit()
    return row


class DashboardSnapshotHotPathTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        _enable_snapshot_mode()
        db.create_all()
        db.session.query(DashboardSnapshot).delete()
        db.session.commit()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        _clear_snapshot_env()
        db.session.query(DashboardSnapshot).delete()
        db.session.commit()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._augment_abandoned_candidates_for_recovery_dashboard")
    def test_normal_carts_does_not_call_abandoned_candidates_builder(
        self,
        mock_augment: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload={
                "merchant_carts_page_rows": [{"id": 1}],
                "merchant_table_rows": [],
                "merchant_archived_carts_page_rows": [],
                "merchant_nav_badge_abandoned": 1,
            },
        )
        resp = self.client.get("/api/dashboard/normal-carts")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("snapshot_mode"))
        mock_augment.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_returns_stale_snapshot(self, _bypass: unittest.mock.MagicMock) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload={"merchant_carts_page_rows": [{"id": 99}], "merchant_table_rows": []},
            stale=True,
        )
        resp = self.client.get("/api/dashboard/normal-carts")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("snapshot_stale"))
        self.assertEqual(len(body.get("merchant_carts_page_rows") or []), 1)

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_degraded_when_no_snapshot(self, _bypass: unittest.mock.MagicMock) -> None:
        resp = self.client.get("/api/dashboard/normal-carts")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("snapshot_degraded"))
        self.assertEqual(body.get("merchant_carts_page_rows"), [])

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch(
        "services.dashboard_hot_slice_v1.build_hot_slice_active_rows",
        return_value=([], {"hot_slice_rows": 0, "hot_slice_ms": 0.0, "hot_slice_queries": 0, "hot_slice_degraded": False, "hot_slice_reason": ""}),
    )
    def test_does_not_scan_history_tables(
        self,
        _hot: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload={"merchant_carts_page_rows": [], "merchant_table_rows": []},
        )
        forbidden = (
            "abandoned_carts",
            "cart_recovery_logs",
            "cart_recovery_reasons",
            "recovery_schedules",
            "merchant_cart_lifecycle_archives",
        )
        seen: list[str] = []

        def _before_cursor(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            sql = str(statement or "").lower()
            seen.append(sql)

        event.listen(db.engine, "before_cursor_execute", _before_cursor)
        try:
            resp = self.client.get("/api/dashboard/normal-carts")
            self.assertEqual(resp.status_code, 200)
        finally:
            event.remove(db.engine, "before_cursor_execute", _before_cursor)

        joined = "\n".join(seen)
        for table in forbidden:
            self.assertNotIn(table, joined, msg=f"unexpected scan of {table}")

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_read_under_200ms_with_snapshot(self, _bypass: unittest.mock.MagicMock) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload={"kpis": {"abandoned_today": 3}, "normal_carts_stats": {}},
        )
        t0 = time.perf_counter()
        resp = self.client.get("/api/dashboard/summary")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))
        self.assertLess(elapsed_ms, 500.0, msg=f"elapsed_ms={elapsed_ms}")

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("services.dashboard_snapshot_builder_v1.build_store_dashboard_snapshots")
    def test_builder_not_invoked_from_api_route(
        self,
        mock_build: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload={"kpis": {}},
        )
        resp = self.client.get("/api/dashboard/summary")
        self.assertEqual(resp.status_code, 200)
        mock_build.assert_not_called()


class DashboardSnapshotBuilderUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()

    def test_upsert_increments_version(self) -> None:
        upsert_dashboard_snapshot(
            store_id=None,
            store_slug="demo-store",
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload={"kpis": {"abandoned_today": 1}},
        )
        upsert_dashboard_snapshot(
            store_id=None,
            store_slug="demo-store",
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload={"kpis": {"abandoned_today": 2}},
        )
        row = (
            db.session.query(DashboardSnapshot)
            .filter(
                DashboardSnapshot.store_slug == "demo-store",
                DashboardSnapshot.snapshot_type == SNAPSHOT_TYPE_SUMMARY,
            )
            .order_by(DashboardSnapshot.generated_at.desc())
            .first()
        )
        self.assertIsNotNone(row)
        self.assertEqual(int(row.version or 0), 2)


if __name__ == "__main__":
    unittest.main()
