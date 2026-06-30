# -*- coding: utf-8 -*-
"""Dashboard hot path elimination — Phase 1B tests."""
from __future__ import annotations

import json
import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import DashboardSnapshot, Store
from services.dashboard_snapshot_v1 import (
    ENV_SNAPSHOT_MODE,
    SNAPSHOT_TYPE_REFRESH_STATE,
    SNAPSHOT_TYPE_STORE_CONNECTION,
    SNAPSHOT_TYPE_SUMMARY,
    SNAPSHOT_TYPE_WIDGET_PANEL,
    any_store_needs_failsafe_snapshot_build,
)


def _enable_snapshot_mode() -> None:
    os.environ["ENV"] = "development"
    os.environ[ENV_SNAPSHOT_MODE] = "1"
    os.environ.setdefault("SECRET_KEY", "unit-test-dashboard-snapshot-1b")


def _clear_snapshot_env() -> None:
    os.environ.pop(ENV_SNAPSHOT_MODE, None)


def _seed_snapshot(*, store_slug: str, snapshot_type: str, payload: dict) -> None:
    now = datetime.now(timezone.utc)
    row = DashboardSnapshot(
        store_slug=store_slug,
        snapshot_type=snapshot_type,
        payload_json=json.dumps(payload, ensure_ascii=False),
        generated_at=now,
        expires_at=now + timedelta(seconds=120),
        version=1,
        status="active",
    )
    db.session.add(row)
    db.session.commit()


class DashboardSnapshotPhase1BTests(unittest.TestCase):
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
    @patch("main._merchant_dashboard_db_ready")
    def test_widget_panel_does_not_trigger_db_ready(
        self,
        mock_db_ready: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_WIDGET_PANEL,
            payload={
                "merchant_widget_panel": {"widget_name": "Test"},
                "merchant_widget_installed": True,
            },
        )
        resp = self.client.get("/api/dashboard/widget-panel")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("snapshot_mode"))
        mock_db_ready.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._api_json_dashboard_widget_panel")
    def test_widget_panel_does_not_run_live_builder(
        self,
        mock_live: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_WIDGET_PANEL,
            payload={"merchant_widget_panel": {}, "merchant_widget_installed": False},
        )
        resp = self.client.get("/api/dashboard/widget-panel")
        self.assertEqual(resp.status_code, 200)
        mock_live.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("services.merchant_store_connection_v1.build_merchant_store_connection_status")
    def test_store_connection_returns_snapshot(
        self,
        mock_live: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_STORE_CONNECTION,
            payload={
                "store_connection": {
                    "connected": True,
                    "status_label_ar": "تم الربط",
                    "store_name": "Demo Store",
                }
            },
        )
        resp = self.client.get("/api/merchant/store-connection")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("snapshot_mode"))
        self.assertTrue(body.get("store_connection", {}).get("connected"))
        mock_live.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._merchant_dashboard_db_ready")
    @patch("services.db_ready_restart_survival_v1.record_first_dashboard_request")
    def test_refresh_state_does_not_trigger_restart_survival_warm(
        self,
        mock_record: unittest.mock.MagicMock,
        mock_db_ready: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_REFRESH_STATE,
            payload={"merchant_dashboard_refresh_token": "tok-1"},
        )
        resp = self.client.get("/api/dashboard/refresh-state")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("snapshot_mode"))
        mock_db_ready.assert_not_called()
        mock_record.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_missing_snapshot_returns_degraded_not_live(
        self, _bypass: unittest.mock.MagicMock
    ) -> None:
        with patch("main._api_json_dashboard_widget_panel") as mock_live:
            resp = self.client.get("/api/dashboard/widget-panel")
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertTrue(body.get("snapshot_degraded"))
            mock_live.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_dashboard_endpoints_under_200ms_with_snapshot(
        self, _bypass: unittest.mock.MagicMock
    ) -> None:
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_WIDGET_PANEL,
            payload={"merchant_widget_panel": {}, "merchant_widget_installed": False},
        )
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_STORE_CONNECTION,
            payload={"store_connection": {"connected": False, "store_name": ""}},
        )
        _seed_snapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_REFRESH_STATE,
            payload={"merchant_dashboard_refresh_token": ""},
        )
        for path in (
            "/api/dashboard/widget-panel",
            "/api/merchant/store-connection",
            "/api/dashboard/refresh-state",
        ):
            t0 = time.perf_counter()
            resp = self.client.get(path)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertEqual(resp.status_code, 200, msg=path)
            self.assertLess(elapsed_ms, 200.0, msg=f"{path} elapsed_ms={elapsed_ms}")

    def test_snapshot_builder_imports_pool_pressure_module(self) -> None:
        """Regression: missing db_pool_pressure_v1 prevents builder loop startup in prod."""
        from services.db_pool_pressure_v1 import evaluate_db_pool_pressure
        from services.dashboard_snapshot_builder_v1 import (
            builder_should_skip_due_to_pool_pressure,
            run_dashboard_snapshot_builder_tick,
        )

        pressure = evaluate_db_pool_pressure()
        self.assertIn(
            str(pressure.get("pressure_level") or "ok"),
            ("ok", "elevated", "high", "critical"),
        )
        skip, _reason, _pressure = builder_should_skip_due_to_pool_pressure()
        self.assertIsInstance(skip, bool)
        self.assertTrue(callable(run_dashboard_snapshot_builder_tick))

    def test_builder_does_not_skip_on_high_pressure(self) -> None:
        from services.dashboard_snapshot_builder_v1 import (
            builder_should_skip_due_to_pool_pressure,
        )

        pressure = {
            "pressure_level": "high",
            "circuit_breaker_open": True,
            "utilization_pct": 76.0,
            "checked_out": 23,
            "pool_size": 30,
            "overflow": 0,
            "available_slots": 7,
        }
        with patch(
            "services.dashboard_snapshot_builder_v1.evaluate_db_pool_pressure",
            return_value=pressure,
        ):
            skip, reason, out = builder_should_skip_due_to_pool_pressure()
        self.assertFalse(skip)
        self.assertEqual(reason, "")
        self.assertEqual(out["pressure_level"], "high")

    def test_builder_skips_on_critical_high_utilization(self) -> None:
        from services.dashboard_snapshot_builder_v1 import (
            builder_should_skip_due_to_pool_pressure,
        )

        pressure = {
            "pressure_level": "critical",
            "utilization_pct": 92.0,
            "checked_out": 28,
            "pool_size": 30,
            "overflow": 0,
            "available_slots": 2,
        }
        with patch(
            "services.dashboard_snapshot_builder_v1.evaluate_db_pool_pressure",
            return_value=pressure,
        ):
            skip, reason, _out = builder_should_skip_due_to_pool_pressure()
        self.assertTrue(skip)
        self.assertEqual(reason, "pool_pressure_critical")

    def test_builder_does_not_skip_critical_low_utilization(self) -> None:
        from services.dashboard_snapshot_builder_v1 import (
            builder_should_skip_due_to_pool_pressure,
        )

        pressure = {
            "pressure_level": "critical",
            "utilization_pct": 10.0,
            "checked_out": 3,
            "pool_size": 30,
            "overflow": 0,
            "available_slots": 1,
        }
        with patch(
            "services.dashboard_snapshot_builder_v1.evaluate_db_pool_pressure",
            return_value=pressure,
        ):
            skip, reason, _out = builder_should_skip_due_to_pool_pressure()
        self.assertFalse(skip)
        self.assertEqual(reason, "")

    def test_failsafe_when_no_summary_snapshot(self) -> None:
        st = Store(zid_store_id="failsafe-demo", recovery_attempts=1)
        db.session.add(st)
        db.session.commit()
        needs, reason = any_store_needs_failsafe_snapshot_build(
            store_pairs=[(int(st.id), "failsafe-demo")],
        )
        self.assertTrue(needs)
        self.assertIn("no_snapshot", reason)

    def test_failsafe_when_snapshot_older_than_5m(self) -> None:
        st = Store(zid_store_id="failsafe-stale", recovery_attempts=1)
        db.session.add(st)
        db.session.commit()
        old = datetime.now(timezone.utc) - timedelta(minutes=6)
        row = DashboardSnapshot(
            store_slug="failsafe-stale",
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload_json='{"ok": true}',
            generated_at=old,
            expires_at=old + timedelta(seconds=60),
            version=1,
            status="active",
        )
        db.session.add(row)
        db.session.commit()
        needs, reason = any_store_needs_failsafe_snapshot_build(
            store_pairs=[(int(st.id), "failsafe-stale")],
        )
        self.assertTrue(needs)
        self.assertIn("stale_snapshot", reason)


if __name__ == "__main__":
    unittest.main()
