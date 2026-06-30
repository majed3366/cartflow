# -*- coding: utf-8 -*-
"""Dashboard snapshot enforcement guard — no live computation in snapshot mode."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import app
from services.dashboard_snapshot_enforcement_guard_v1 import (
    DashboardSnapshotHotPathViolation,
    serve_enforced_snapshot_response,
)
from services.dashboard_snapshot_hot_path_guard_v1 import (
    dashboard_api_snapshot_request_scope,
    guard_dashboard_hot_path,
)
from services.dashboard_snapshot_v1 import ENV_SNAPSHOT_MODE


def _enable_enforced_snapshot_mode() -> None:
    os.environ["ENV"] = "development"
    os.environ[ENV_SNAPSHOT_MODE] = "1"
    os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_ENFORCE"] = "1"
    os.environ.setdefault("SECRET_KEY", "unit-test-dashboard-enforcement")


def _clear_env() -> None:
    os.environ.pop(ENV_SNAPSHOT_MODE, None)
    os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_ENFORCE", None)


class DashboardSnapshotEnforcementGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        _enable_enforced_snapshot_mode()
        db.create_all()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        _clear_env()

    def test_guard_raises_on_live_path_during_snapshot_request(self) -> None:
        with dashboard_api_snapshot_request_scope(path="/api/dashboard/summary"):
            with self.assertRaises(DashboardSnapshotHotPathViolation):
                guard_dashboard_hot_path("summary_live", endpoint="summary")

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._api_json_dashboard_summary")
    def test_summary_never_calls_live_builder_in_snapshot_mode(
        self,
        mock_live: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        resp = self.client.get("/api/dashboard/summary")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("snapshot_mode"))
        self.assertTrue(body.get("snapshot_degraded"))
        mock_live.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._api_json_dashboard_normal_carts")
    def test_normal_carts_never_calls_live_builder_in_snapshot_mode(
        self,
        mock_live: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        resp = self.client.get("/api/dashboard/normal-carts")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("snapshot_mode"))
        self.assertTrue(body.get("snapshot_degraded"))
        mock_live.assert_not_called()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    @patch("main._api_json_dashboard_widget_panel")
    def test_widget_panel_never_calls_live_builder_in_snapshot_mode(
        self,
        mock_live: unittest.mock.MagicMock,
        _bypass: unittest.mock.MagicMock,
    ) -> None:
        resp = self.client.get("/api/dashboard/widget-panel")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("snapshot_mode"))
        mock_live.assert_not_called()

    def test_serve_enforced_snapshot_response_returns_degraded_on_error(self) -> None:
        def _boom(**_kwargs: object) -> dict:
            raise RuntimeError("read failed")

        payload = serve_enforced_snapshot_response(
            path="/api/dashboard/summary",
            build_from_snapshot=_boom,
            degraded_builder=lambda reason: {
                "snapshot_mode": True,
                "snapshot_degraded": True,
                "snapshot_reason": reason,
            },
            store_slug="demo",
        )
        self.assertTrue(payload.get("ok"))
        self.assertTrue(payload.get("snapshot_degraded"))
        self.assertEqual(payload.get("snapshot_reason"), "snapshot_read_error")


if __name__ == "__main__":
    unittest.main()
