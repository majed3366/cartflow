# -*- coding: utf-8 -*-
"""Admin multi-store mixed-behavior load test."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_multi_store_mixed_behavior_load_test import (
    MIXED_BEHAVIOR_LOAD_TEST_DISPLAY_UNAVAILABLE_AR,
    _MAX_EVENTS_PER_STORE,
    _MAX_STORES,
    clear_mixed_behavior_load_test_state_for_tests,
    clamp_multi_store_counts,
    get_latest_mixed_behavior_load_test_display_ar,
    run_multi_store_mixed_behavior_load_test,
    stash_latest_mixed_behavior_load_test_result_for_tests,
)


class AdminMultiStoreMixedBehaviorLoadTestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        clear_mixed_behavior_load_test_state_for_tests()

    def tearDown(self) -> None:
        clear_mixed_behavior_load_test_state_for_tests()
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def test_clamp_20x50(self) -> None:
        stores, per, total = clamp_multi_store_counts(20, 50)
        self.assertEqual(stores, 20)
        self.assertEqual(per, 50)
        self.assertEqual(total, 1000)

    def test_clamp_above_limits(self) -> None:
        stores, per, total = clamp_multi_store_counts(25, 80)
        self.assertEqual(stores, _MAX_STORES)
        self.assertEqual(per, _MAX_EVENTS_PER_STORE)
        self.assertEqual(total, 1000)

    def test_small_mixed_clean_run(self) -> None:
        summary = run_multi_store_mixed_behavior_load_test(
            stores_count=2,
            events_per_store=4,
            dry_run_whatsapp=True,
        )
        self.assertEqual(summary["total_events"], 8)
        self.assertEqual(summary["success_count"], 8)
        self.assertEqual(summary["error_count"], 0)
        self.assertEqual(summary["contamination_errors"], 0)
        self.assertEqual(summary["lifecycle_errors"], 0)
        kinds = summary.get("event_kind_counts") or {}
        self.assertGreater(kinds.get("sync", 0), 0)
        self.assertGreater(kinds.get("abandon", 0), 0)

    def test_endpoint_requires_admin(self) -> None:
        os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.post(
            "/admin/ops/load-test/multi-store-mixed-behavior",
            json={"stores_count": 1, "events_per_store": 1},
        )
        self.assertEqual(r.status_code, 503)

    def test_health_renders_mixed_line(self) -> None:
        stash_latest_mixed_behavior_load_test_result_for_tests(
            {
                "total_events": 1000,
                "success_count": 1000,
                "stores_count": 20,
                "contamination_errors": 0,
                "lifecycle_errors": 0,
                "error_count": 0,
                "avg_duration_ms": 95.0,
            }
        )
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "mixed-behavior-admin-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "mixed-behavior-admin-pass"},
        )
        r = client.get("/admin/operational-health")
        self.assertEqual(r.status_code, 200)
        self.assertIn("آخر اختبار سلوك مختلط", r.text)
        self.assertIn("1000/1000", r.text)

    def test_health_survives_corrupt_mixed_result(self) -> None:
        stash_latest_mixed_behavior_load_test_result_for_tests(
            {"total_events": None, "success_count": "bad"}
        )
        line = get_latest_mixed_behavior_load_test_display_ar()
        self.assertEqual(line, MIXED_BEHAVIOR_LOAD_TEST_DISPLAY_UNAVAILABLE_AR)
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "mixed-behavior-admin-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={"password": "mixed-behavior-admin-pass"},
        )
        self.assertEqual(client.get("/admin/operational-health").status_code, 200)
