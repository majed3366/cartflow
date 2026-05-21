# -*- coding: utf-8 -*-
"""Admin dashboard sidebar — navigation presentation only."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app


class AdminSidebarTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "admin-sidebar-test-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        self.client = TestClient(app)
        self.client.post(
            "/admin/operations/login",
            data={
                "password": "admin-sidebar-test-pass",
                "next": "/admin/operational-health",
            },
        )

    def test_operational_health_has_sidebar_and_active_ops_center(self) -> None:
        r = self.client.get("/admin/operational-health")
        self.assertEqual(r.status_code, 200)
        t = r.text
        self.assertIn("CartFlow Admin", t)
        self.assertIn('id="admin-sidebar-panel"', t)
        self.assertIn("مركز التشغيل", t)
        self.assertIn('id="operational-verdict"', t)
        self.assertIn("bg-indigo-50 font-semibold text-indigo-900", t)
        self.assertIn("/admin/operational-health", t)

    def test_operations_overview_active(self) -> None:
        r = self.client.get("/admin/operations")
        self.assertEqual(r.status_code, 200)
        self.assertIn("لوحة عامة", r.text)
        self.assertIn('href="/admin/operations"', r.text)

    def test_placeholder_control(self) -> None:
        r = self.client.get("/admin/control")
        self.assertEqual(r.status_code, 200)
        self.assertIn("قيد التطوير", r.text)
        self.assertIn("التحكم التشغيلي", r.text)
        self.assertNotIn('id="operational-verdict"', r.text)

    def test_placeholder_stores(self) -> None:
        r = self.client.get("/admin/stores")
        self.assertEqual(r.status_code, 200)
        self.assertIn("جميع المتاجر", r.text)
        self.assertIn("قيد التطوير", r.text)

    def test_placeholder_subscriptions(self) -> None:
        r = self.client.get("/admin/subscriptions/plans")
        self.assertEqual(r.status_code, 200)
        self.assertIn("الباقات", r.text)

    def test_placeholder_reports(self) -> None:
        r = self.client.get("/admin/reports/recovery")
        self.assertEqual(r.status_code, 200)
        self.assertIn("تقارير الاسترجاع", r.text)

    def test_placeholder_system(self) -> None:
        r = self.client.get("/admin/system/logs")
        self.assertEqual(r.status_code, 200)
        self.assertIn("السجلات", r.text)

    def test_admin_root_redirects(self) -> None:
        r = self.client.get("/admin", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/operations", r.headers.get("location", ""))

    def test_merchant_dashboard_unchanged(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("CartFlow Admin", r.text)
        self.assertNotIn('id="admin-sidebar-panel"', r.text)


if __name__ == "__main__":
    unittest.main()
