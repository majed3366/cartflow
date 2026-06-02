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
        self.assertIn("نظرة عامة", body)
        self.assertIn('id="admin-sidebar-panel"', body)
        # Executive summary metrics replace technical operational sections.
        self.assertIn("حالة المنصة", body)
        self.assertIn("المتاجر النشطة", body)
        self.assertIn("المتاجر المتأثرة", body)
        self.assertIn("التنبيهات المفتوحة", body)
        self.assertIn("الاسترجاعات اليوم", body)
        self.assertIn("أكبر مشكلة الآن", body)
        # Technical sections must NOT be on the executive overview.
        self.assertNotIn("صحة المجدول", body)
        self.assertNotIn("جاهزية المتاجر", body)
        self.assertNotIn("Recovery Resume Health", body)

    def test_technical_sections_live_under_support_diagnostics(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/diagnostics")
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.text
        self.assertIn("Recovery Resume Health", body)
        self.assertIn("Resume Eligible", body)
        self.assertIn("Scheduled Due Now", body)
        self.assertIn("Running Count", body)
        self.assertIn("تفاصيل تقنية (للدعم فقط)", body)
        self.assertIn("/health/scheduler", body)
        # Lazy technical panels reuse the existing section endpoints.
        self.assertIn("ops-investigation-panel", body)
        self.assertIn("ops-analytics-panel", body)
        # Investigation endpoint (relocated, still functional).
        inv = client.get("/admin/operations/section/investigation")
        self.assertEqual(inv.status_code, 200)
        for label in ("scheduled", "running", "completed", "صحة المجدول"):
            self.assertIn(label, inv.text)

    def test_overview_shows_active_stores_metric(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("المتاجر النشطة", r.text)
        self.assertIn("حالة المتاجر", r.text)

    def test_current_issues_page_business_language(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/operations/issues")
        self.assertEqual(r.status_code, 200, r.text[:500])
        self.assertIn("المشاكل الحالية", r.text)

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
