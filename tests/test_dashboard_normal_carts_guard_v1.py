# -*- coding: utf-8 -*-
"""Wall-clock guard for merchant normal-carts API."""
from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import app
from services.cartflow_simulation_report_v1 import cleanup_simulation_data
from services.dashboard_normal_carts_guard_v1 import (
    dashboard_nc_deadline_exceeded,
    dashboard_nc_guard_begin,
    dashboard_nc_guard_payload,
    dashboard_nc_mark_partial,
    dashboard_nc_partial_active,
)


class DashboardNormalCartsGuardTests(unittest.TestCase):
    def test_deadline_marks_partial(self) -> None:
        import services.dashboard_normal_carts_guard_v1 as guard_mod

        with patch.object(guard_mod, "_WALL_BUDGET_S", 0.001):
            guard_mod.dashboard_nc_guard_begin()
            time.sleep(0.01)
            self.assertTrue(guard_mod.dashboard_nc_deadline_exceeded())
            guard_mod.dashboard_nc_mark_partial("test_stage")
            payload = guard_mod.dashboard_nc_guard_payload()
            self.assertTrue(payload.get("dashboard_partial"))
            self.assertEqual(payload.get("dashboard_timeout_stage"), "test_stage")
            guard_mod.dashboard_nc_guard_begin()

    def test_api_returns_within_budget_with_perf(self) -> None:
        db.create_all()
        cleanup_simulation_data()
        client = TestClient(app)
        with patch("main.send_whatsapp"):
            with patch("main.recovery_uses_real_whatsapp", return_value=False):
                t0 = time.perf_counter()
                res = client.get(
                    "/api/dashboard/normal-carts",
                    params={"limit": 8},
                )
                elapsed = time.perf_counter() - t0
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body.get("ok"))
        self.assertLess(elapsed, 15.0)
        self.assertIn("merchant_carts_page_rows", body)
        if body.get("dashboard_partial"):
            self.assertTrue(body.get("dashboard_timeout_stage"))

    def test_guard_begin_resets_partial(self) -> None:
        import services.dashboard_normal_carts_guard_v1 as guard_mod

        guard_mod.dashboard_nc_guard_begin()
        self.assertFalse(guard_mod.dashboard_nc_partial_active())
        guard_mod.dashboard_nc_mark_partial("x")
        self.assertTrue(guard_mod.dashboard_nc_partial_active())
        guard_mod.dashboard_nc_guard_begin()
        self.assertFalse(guard_mod.dashboard_nc_partial_active())
