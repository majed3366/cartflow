# -*- coding: utf-8 -*-
"""Admin operational health v1 — read-only page and aggregates."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services import cartflow_admin_http_auth as aauth
from services import cartflow_runtime_health as rh
from services.admin_operational_control import clear_verification_state_for_tests
from services.admin_operational_health import (
    build_admin_operational_health_readonly,
    clear_operational_health_buffers_for_tests,
    record_cart_event_finish_sample,
    record_db_pool_timeout,
)


class AdminOperationalHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        clear_operational_health_buffers_for_tests()
        clear_verification_state_for_tests()

    def tearDown(self) -> None:
        clear_operational_health_buffers_for_tests()
        clear_verification_state_for_tests()
        rh.clear_runtime_anomaly_buffer_for_tests()
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def test_build_readonly_has_cards_and_headlines(self) -> None:
        payload = build_admin_operational_health_readonly()
        self.assertIn("admin_risk_summary", payload)
        self.assertIn("cards", payload)
        cards = payload["cards"]
        self.assertIn("cart_event", cards)
        self.assertIn("db_pool", cards)
        self.assertIn("background_tasks", cards)
        self.assertIn("whatsapp", cards)
        self.assertIn("db_due_scanner", cards)
        scanner = cards["db_due_scanner"]
        self.assertIn("operational", scanner)
        self.assertEqual(scanner["operational"]["title_ar"], "متابعة الاسترجاعات المجدولة")

    def test_cart_event_sample_slow_warning(self) -> None:
        record_cart_event_finish_sample(
            duration_ms=3000.0,
            http_status=200,
            recovery_outcome="scheduled",
            event="cart_abandoned",
        )
        payload = build_admin_operational_health_readonly()
        ce = payload["cards"]["cart_event"]
        self.assertTrue(ce.get("slow_warning"))
        self.assertGreaterEqual(len(payload.get("warnings") or []), 1)

    def test_pool_timeout_warning(self) -> None:
        record_db_pool_timeout(detail="QueuePool limit reached")
        payload = build_admin_operational_health_readonly()
        pool = payload["cards"]["db_pool"]
        self.assertGreater(int(pool.get("timeout_count") or 0), 0)
        codes = {w.get("code") for w in payload.get("warnings") or []}
        self.assertIn("db_pool_timeout", codes)

    def test_page_503_without_password(self) -> None:
        os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get("/admin/operational-health")
        self.assertEqual(r.status_code, 503)

    def test_page_redirects_without_session(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "health-auth-test-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get("/admin/operational-health", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/operations/login", r.headers.get("location", ""))

    def test_page_renders_with_admin_session(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "health-auth-test-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={
                "password": "health-auth-test-pass-1",
                "next": "/admin/operational-health",
            },
        )
        r = client.get("/admin/operational-health")
        self.assertEqual(r.status_code, 200, r.text[:400])
        self.assertIn("مركز عمليات CartFlow", r.text)
        self.assertIn("الملخص التشغيلي", r.text)
        self.assertIn("المشكلة", r.text)
        self.assertIn("هل النظام يعمل طبيعي؟", r.text)
        self.assertIn("متابعة الاسترجاعات المجدولة", r.text)
        self.assertIn("متابعة نشاط العملاء", r.text)
        self.assertIn("عمليات الاسترجاع التلقائي", r.text)
        self.assertIn("تؤثر على العملاء", r.text)
        self.assertIn("هل يؤثر على المتاجر؟", r.text)
        self.assertGreaterEqual(r.text.count("تفاصيل تقنية (للدعم)"), 5)
        scanner = build_admin_operational_health_readonly()["cards"]["db_due_scanner"]
        self.assertEqual(len((scanner.get("operational") or {}).get("rows") or []), 7)
        payload_oc = build_admin_operational_health_readonly().get("operations_center") or {}
        self.assertIn("summary_ar", payload_oc)

    def test_merchant_dashboard_excludes_scanner_diagnostics(self) -> None:
        client = TestClient(app)
        r = client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        t = (r.text or "").lower()
        for needle in (
            "db due scanner",
            "db-due-scanner",
            "db_due_scanner",
            "/api/admin/db-due-scanner-health",
        ):
            self.assertNotIn(needle, t, msg=f"merchant dashboard leaked: {needle}")
