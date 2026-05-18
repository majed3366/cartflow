# -*- coding: utf-8 -*-
"""Admin operational health must not crash on load-test display edge cases."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_cart_event_load_test import (
    LOAD_TEST_DISPLAY_UNAVAILABLE_AR,
    _MAX_EVENTS,
    clear_load_test_state_for_tests,
    get_latest_load_test_display_ar,
    run_cart_event_load_test,
    stash_latest_load_test_result_for_tests,
)
from services.admin_operational_control import build_admin_operational_control_readonly


class AdminOperationalHealthLoadTestDisplayTests(unittest.TestCase):
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

    def _login(self, client: TestClient) -> None:
        client.post(
            "/admin/operations/login",
            data={"password": "health-loadtest-pass-1", "next": "/admin/operational-health"},
        )

    def _get_health(self, client: TestClient) -> int:
        return client.get("/admin/operational-health").status_code

    def test_no_load_test_result_renders_200(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "health-loadtest-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        self._login(client)
        self.assertIsNone(get_latest_load_test_display_ar())
        self.assertEqual(self._get_health(client), 200)

    def test_display_null_timing_does_not_raise(self) -> None:
        stash_latest_load_test_result_for_tests(
            {
                "total_events": 100,
                "success_count": 100,
                "error_count": 0,
                "avg_duration_ms": None,
                "max_duration_ms": None,
                "event_mode": "cart_abandoned",
            }
        )
        line = get_latest_load_test_display_ar()
        self.assertIsNotNone(line)
        self.assertIn("آخر اختبار ضغط", line or "")
        self.assertIn("0ms", line or "")

    def test_display_missing_pool_and_timings_renders_200(self) -> None:
        stash_latest_load_test_result_for_tests(
            {
                "events_count": 100,
                "success_count": 99,
                "error_count": 1,
                "event_mode": "cart_abandoned",
            }
        )
        control = build_admin_operational_control_readonly()
        self.assertIsNotNone(control.get("latest_load_test_ar"))

        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "health-loadtest-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        self._login(client)
        self.assertEqual(self._get_health(client), 200)

    def test_display_corrupt_payload_shows_unavailable(self) -> None:
        stash_latest_load_test_result_for_tests({"unexpected": True})
        self.assertEqual(
            get_latest_load_test_display_ar(),
            LOAD_TEST_DISPLAY_UNAVAILABLE_AR,
        )

    def test_health_after_250_abandoned_load_test(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "health-loadtest-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        self._login(client)
        r = client.post(
            "/admin/ops/load-test/cart-event",
            json={"events_count": 250, "reason_tag": "price", "dry_run_whatsapp": True},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        data = r.json()
        self.assertEqual(data.get("total_events"), 250)
        self.assertEqual(data.get("success_count"), 250)
        self.assertEqual(data.get("error_count"), 0)
        self.assertEqual(data.get("queuepool_timeout_count"), 0)
        self.assertEqual(self._get_health(client), 200)
        page = client.get("/admin/operational-health")
        self.assertIn("آخر اختبار ضغط", page.text)
        self.assertIn("250/250", page.text)

    def test_health_after_request_capped_at_250(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "health-loadtest-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        self._login(client)
        r = client.post(
            "/admin/ops/load-test/cart-event",
            json={"events_count": 500, "reason_tag": "price", "dry_run_whatsapp": True},
        )
        self.assertEqual(r.status_code, 200, r.text[:300])
        data = r.json()
        self.assertEqual(data.get("total_events"), _MAX_EVENTS)
        self.assertEqual(data.get("max_events_allowed"), _MAX_EVENTS)
        self.assertEqual(self._get_health(client), 200)
