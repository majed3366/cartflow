# -*- coding: utf-8 -*-
"""Admin cart-event load test — safe, no real WhatsApp."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services import cartflow_admin_http_auth as aauth
from services.admin_cart_event_load_test import (
    clear_load_test_state_for_tests,
    get_latest_load_test_display_ar,
    run_cart_event_load_test,
)
from services.admin_cart_event_load_test import _MAX_EVENTS


class AdminCartEventLoadTestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        clear_load_test_state_for_tests()

    def tearDown(self) -> None:
        clear_load_test_state_for_tests()
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def test_run_load_test_summary_metrics(self) -> None:
        summary = run_cart_event_load_test(
            store_slug="demo",
            events_count=5,
            dry_run_whatsapp=True,
            phone_present=True,
        )
        self.assertEqual(summary["total_events"], 5)
        self.assertEqual(summary["success_count"], 5)
        self.assertEqual(summary["error_count"], 0)
        self.assertIn("avg_duration_ms", summary)
        self.assertIn("max_duration_ms", summary)
        self.assertEqual(summary["queuepool_timeout_count"], 0)
        self.assertTrue(summary["dry_run_whatsapp"])
        line = get_latest_load_test_display_ar()
        self.assertIsNotNone(line)
        self.assertIn("آخر اختبار ضغط", line or "")

    def test_events_count_capped_at_100(self) -> None:
        summary = run_cart_event_load_test(
            store_slug="demo",
            events_count=250,
            dry_run_whatsapp=True,
            reason_tag="price",
            phone_present=True,
        )
        self.assertEqual(summary["total_events"], _MAX_EVENTS)
        self.assertEqual(summary["max_events_allowed"], _MAX_EVENTS)
        self.assertEqual(summary["event_mode"], "cart_abandoned")

    def test_endpoint_requires_admin(self) -> None:
        os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.post("/admin/ops/load-test/cart-event", json={"events_count": 1})
        self.assertEqual(r.status_code, 503)

    def test_endpoint_with_session(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "load-test-admin-pass-xy"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "load-test-admin-pass-xy"},
        )
        r = client.post(
            "/admin/ops/load-test/cart-event",
            json={"events_count": 10, "dry_run_whatsapp": True},
        )
        self.assertEqual(r.status_code, 200, r.text[:400])
        data = r.json()
        self.assertEqual(data.get("total_events"), 10)
        self.assertEqual(data.get("success_count"), 10)
        self.assertEqual(data.get("error_count"), 0)
        self.assertGreaterEqual(float(data.get("max_duration_ms") or 0), 0)

    def test_health_page_after_load_test(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "load-test-admin-pass-xy"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "load-test-admin-pass-xy"},
        )
        client.post(
            "/admin/ops/load-test/cart-event",
            json={"events_count": 5},
        )
        r = client.get("/admin/operational-health")
        self.assertEqual(r.status_code, 200)
        self.assertIn("التحكم التشغيلي", r.text)
        self.assertIn("آخر اختبار ضغط", r.text)
