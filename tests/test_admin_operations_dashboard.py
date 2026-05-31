# -*- coding: utf-8 -*-
"""Admin operational dashboard (HTML) — auth and rendering."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services import cartflow_admin_http_auth as aauth
from services.admin_operations_center_v1 import build_admin_operations_center_v1_readonly


class AdminOperationsDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")

    def tearDown(self) -> None:
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def test_dashboard_503_when_password_not_configured(self) -> None:
        os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 503)

    def test_dashboard_redirects_to_login_without_session(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get("/admin/operations", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/operations/login", r.headers.get("location", ""))

    def test_login_sets_cookie_and_dashboard_renders_v1(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9", "next": "/admin/operations"},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303, r.text[:300])
        self.assertIn(aauth.admin_cookie_name(), r.cookies)
        r2 = client.get("/admin/operations")
        self.assertEqual(r2.status_code, 200, r2.text[:500])
        body = r2.text
        self.assertIn("CartFlow Admin", body)
        self.assertIn("مركز العمليات", body)
        self.assertIn('id="admin-sidebar-panel"', body)
        self.assertIn("صحة المجدول", body)
        self.assertIn("حالات الاسترجاع", body)
        self.assertIn("جاهزية المتاجر", body)
        self.assertIn("تنبيهات أساسية", body)

    def test_v1_sections_render(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        body = r.text
        self.assertIn("/health/scheduler", body)
        self.assertIn("scheduled", body)
        self.assertIn("running", body)
        self.assertIn("completed", body)

    def test_store_readiness_counts_when_stores_present(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        payload = build_admin_operations_center_v1_readonly()
        st = payload.get("store_readiness") or {}
        if int(st.get("total_stores") or 0) < 1:
            self.skipTest("no stores to assert readiness numerics")
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("إجمالي المتاجر", r.text)
        self.assertIn("جاهز", r.text)

    def test_alerts_table_or_empty_state(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        has_empty = "لا تنبيهات تشغيلية بارزة" in r.text
        has_table = "<table" in r.text
        self.assertTrue(has_empty or has_table)

    def test_no_secrets_in_html(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "super-secret-dashboard-pass-xyz-99"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "super-secret-dashboard-pass-xyz-99"},
        )
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("super-secret-dashboard-pass", r.text)
        self.assertNotIn("unit-test-secret-key", r.text)


if __name__ == "__main__":
    unittest.main()
