# -*- coding: utf-8 -*-
"""Admin Operations Center v1 — read-only /admin/operations."""
from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_operations_center_v1 import build_admin_operations_center_v1_readonly
from services.cartflow_admin_http_auth import admin_cookie_name
from services.recovery_process_role_v1 import build_scheduler_health_snapshot


class AdminOperationsCenterV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "ops-center-v1-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def _login(self) -> None:
        r = self.client.post(
            "/admin/operations/login",
            data={"password": "ops-center-v1-pass", "next": "/admin/operations"},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303, r.text[:300])

    def test_build_payload_has_required_sections(self) -> None:
        payload = build_admin_operations_center_v1_readonly()
        self.assertEqual(payload.get("version"), "admin_operations_center_v1")
        sch = payload.get("scheduler") or {}
        for key in ("role", "overdue_scheduled_count", "running_stale_count"):
            self.assertIn(key, sch)
        rec = payload.get("recovery") or {}
        for key in ("scheduled", "running", "completed", "failed", "expired"):
            self.assertIn(key, rec)
        st = payload.get("store_readiness") or {}
        for key in (
            "total_stores",
            "ready_stores",
            "stores_missing_whatsapp",
            "stores_no_recent_cart_events",
            "stores_needing_setup",
        ):
            self.assertIn(key, st)
        self.assertIsInstance(payload.get("alerts"), list)

    def test_scheduler_card_matches_health_endpoint(self) -> None:
        health = build_scheduler_health_snapshot()
        payload = build_admin_operations_center_v1_readonly()
        sch = payload.get("scheduler") or {}
        self.assertEqual(sch.get("role"), health.get("role"))
        self.assertEqual(
            sch.get("overdue_scheduled_count"), health.get("overdue_scheduled_count")
        )
        self.assertEqual(
            sch.get("running_stale_count"), health.get("running_stale_count")
        )

    def test_page_loads_authenticated(self) -> None:
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.text
        self.assertIn("مركز العمليات", body)
        self.assertIn("صحة المجدول", body)
        self.assertIn("حالات الاسترجاع", body)
        self.assertIn("جاهزية المتاجر", body)
        self.assertIn("تنبيهات أساسية", body)
        self.assertIn('id="admin-sidebar-panel"', body)

    def test_page_redirects_without_session(self) -> None:
        r = self.client.get("/admin/operations", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/operations/login", r.headers.get("location", ""))

    def test_alerts_table_or_empty_state(self) -> None:
        self._login()
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            "لا تنبيهات تشغيلية بارزة" in r.text or "<table" in r.text,
            msg="expected alerts table or empty state",
        )


if __name__ == "__main__":
    unittest.main()
