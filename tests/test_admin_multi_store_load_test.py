# -*- coding: utf-8 -*-
"""Admin multi-store cart-event load test — isolation and limits."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_multi_store_load_test import (
    MULTI_STORE_LOAD_TEST_DISPLAY_UNAVAILABLE_AR,
    _MAX_EVENTS_PER_STORE,
    _MAX_STORES,
    _MAX_TOTAL_EVENTS,
    clear_multi_store_load_test_state_for_tests,
    clamp_multi_store_counts,
    get_latest_multi_store_load_test_display_ar,
    is_loadtest_store_slug,
    run_multi_store_cart_event_load_test,
    stash_latest_multi_store_load_test_result_for_tests,
)


class AdminMultiStoreLoadTestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        clear_multi_store_load_test_state_for_tests()

    def tearDown(self) -> None:
        clear_multi_store_load_test_state_for_tests()
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def test_clamp_limits(self) -> None:
        stores, per, total = clamp_multi_store_counts(25, 60)
        self.assertEqual(stores, _MAX_STORES)
        self.assertEqual(per, _MAX_EVENTS_PER_STORE)
        self.assertEqual(total, _MAX_STORES * _MAX_EVENTS_PER_STORE)
        self.assertLessEqual(total, _MAX_TOTAL_EVENTS)

        stores2, per2, total2 = clamp_multi_store_counts(20, 50)
        self.assertEqual(stores2, 20)
        self.assertEqual(per2, 50)
        self.assertEqual(total2, 1000)

        stores3, per3, total3 = clamp_multi_store_counts(20, 100)
        self.assertEqual(stores3, 20)
        self.assertEqual(per3, 50)
        self.assertEqual(total3, 1000)

    def test_loadtest_slug_guard(self) -> None:
        self.assertTrue(is_loadtest_store_slug("loadtest-store-001"))
        self.assertFalse(is_loadtest_store_slug("demo"))

    def test_small_multi_store_clean_run(self) -> None:
        summary = run_multi_store_cart_event_load_test(
            stores_count=2,
            events_per_store=2,
            dry_run_whatsapp=True,
        )
        self.assertEqual(summary["stores_count"], 2)
        self.assertEqual(summary["events_per_store"], 2)
        self.assertEqual(summary["total_events"], 4)
        self.assertEqual(summary["success_count"], 4)
        self.assertEqual(summary["error_count"], 0)
        self.assertEqual(summary["contamination_errors"], 0)
        self.assertEqual(summary["contamination_samples"], [])
        self.assertEqual(summary["queuepool_timeout_count"], 0)
        line = get_latest_multi_store_load_test_display_ar()
        self.assertIsNotNone(line)
        self.assertIn("آخر اختبار تعدد متاجر", line or "")
        self.assertIn("تلوث 0", line or "")

    def test_capped_above_max_stores(self) -> None:
        summary = run_multi_store_cart_event_load_test(
            stores_count=30,
            events_per_store=1,
            dry_run_whatsapp=True,
        )
        self.assertEqual(summary["stores_count"], _MAX_STORES)
        self.assertEqual(summary["total_events"], _MAX_STORES)

    def test_endpoint_requires_admin(self) -> None:
        os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.post(
            "/admin/ops/load-test/multi-store-cart-event",
            json={"stores_count": 1, "events_per_store": 1},
        )
        self.assertEqual(r.status_code, 503)

    def test_endpoint_with_session_small(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "ms-loadtest-admin-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "ms-loadtest-admin-pass-1"},
        )
        r = client.post(
            "/admin/ops/load-test/multi-store-cart-event",
            json={"stores_count": 2, "events_per_store": 1, "dry_run_whatsapp": True},
        )
        self.assertEqual(r.status_code, 200, r.text[:400])
        data = r.json()
        self.assertEqual(data.get("total_events"), 2)
        self.assertEqual(data.get("contamination_errors"), 0)

    def test_health_renders_multi_store_line(self) -> None:
        stash_latest_multi_store_load_test_result_for_tests(
            {
                "total_events": 1000,
                "success_count": 1000,
                "stores_count": 20,
                "contamination_errors": 0,
                "error_count": 0,
                "avg_duration_ms": 88.0,
            }
        )
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "ms-loadtest-admin-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "ms-loadtest-admin-pass-1"},
        )
        r = client.get("/admin/operational-health")
        self.assertEqual(r.status_code, 200)
        self.assertIn("آخر اختبار تعدد متاجر", r.text)
        self.assertIn("1000/1000", r.text)

    def test_health_survives_corrupt_multi_store_result(self) -> None:
        stash_latest_multi_store_load_test_result_for_tests(
            {"total_events": None, "success_count": "x"}
        )
        line = get_latest_multi_store_load_test_display_ar()
        self.assertEqual(line, MULTI_STORE_LOAD_TEST_DISPLAY_UNAVAILABLE_AR)
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "ms-loadtest-admin-pass-1"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "ms-loadtest-admin-pass-1"},
        )
        self.assertEqual(client.get("/admin/operational-health").status_code, 200)
