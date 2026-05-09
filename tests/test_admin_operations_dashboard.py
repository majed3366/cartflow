# -*- coding: utf-8 -*-
"""Admin operational dashboard (HTML) — auth and rendering."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services import cartflow_admin_http_auth as aauth
from services import cartflow_admin_operational_summary as aos
from services import cartflow_runtime_health as rh


class AdminOperationsDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")

    def tearDown(self) -> None:
        rh.clear_runtime_anomaly_buffer_for_tests()
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

    def test_login_sets_cookie_and_dashboard_renders_summary(self) -> None:
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
        self.assertIn("مركز التشغيل", body)
        self.assertIn("Operational Control Center", body)
        self.assertRegex(body, r"فئة المنصة:")
        self.assertRegex(body, r"جاهزية الإعداد|جاهز إعدادياً")

    def test_trust_chips_render_when_counts_present(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        summary = aos.build_admin_operational_summary_readonly()
        agg = summary.get("aggregate_onboarding") or {}
        if int(agg.get("total_stores_scanned") or 0) < 1:
            self.skipTest("no stores to assert trust chip numerics")
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertRegex(r.text, r"جاهز:|جزئي:|ضعيف:|غير مستقر:")

    def test_warnings_section_renders_hints(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        rh.record_runtime_anomaly(rh.ANOMALY_PROVIDER_SEND_FAILURE, source="t", detail="x")
        rh.record_runtime_anomaly(rh.ANOMALY_PROVIDER_SEND_FAILURE, source="t", detail="y")
        rh.record_runtime_anomaly(rh.ANOMALY_PROVIDER_SEND_FAILURE, source="t", detail="z")
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("تحذيرات تشغيلية", r.text)
        p = aos.build_admin_operational_summary_readonly()
        hints = p.get("admin_operational_hints_ar") or []
        if hints:
            self.assertIn(hints[0][:12], r.text)

    def test_empty_state_or_table_present(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "dashboard-auth-test-pass-9"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "dashboard-auth-test-pass-9"},
        )
        r = client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        has_empty = "لا متاجر لعرضها" in r.text
        has_table = "حالة المتاجر" in r.text and "<table" in r.text
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
