# -*- coding: utf-8 -*-
"""DB due scanner admin observability (read-only metrics)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import main  # noqa: F401
from fastapi.testclient import TestClient
from main import app
from services.cartflow_admin_http_auth import issue_admin_session_cookie_value
from services.db_due_scanner_health import (
    build_db_due_scanner_health,
    clear_db_due_scanner_health_for_tests,
    record_db_due_scanner_loop_started,
    record_db_due_scanner_tick_result,
)


class DbDueScannerHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_db_due_scanner_health_for_tests()
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)

    def test_disabled_by_default(self) -> None:
        snap = build_db_due_scanner_health()
        self.assertFalse(snap["enabled"])
        self.assertEqual(snap["status"], "disabled")

    def test_tick_updates_metrics(self) -> None:
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        record_db_due_scanner_loop_started()
        with patch(
            "services.db_due_scanner_health._resolve_loop_running",
            return_value=True,
        ):
            record_db_due_scanner_tick_result(
                {"found": 2, "dispatched": 1, "skipped": 0}
            )
            snap = build_db_due_scanner_health()
        self.assertTrue(snap["enabled"])
        self.assertEqual(snap["last_found"], 2)
        self.assertEqual(snap["last_dispatched"], 1)
        self.assertEqual(snap["total_ticks"], 1)
        self.assertEqual(snap["total_dispatches"], 1)
        self.assertIsNotNone(snap["last_tick_at"])
        self.assertIsNotNone(snap["last_dispatch_at"])
        self.assertEqual(snap["status"], "healthy")

    def test_error_status(self) -> None:
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        record_db_due_scanner_tick_result({"found": 0, "dispatched": 0, "skipped": 0, "error": "db fail"})
        snap = build_db_due_scanner_health()
        self.assertEqual(snap["status"], "error")
        self.assertEqual(snap["last_error"], "db fail")

    def test_admin_api_requires_auth(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "scanner-health-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        r = client.get("/api/admin/db-due-scanner-health")
        self.assertEqual(r.status_code, 401)
        client.cookies.set("cartflow_admin_session", issue_admin_session_cookie_value())
        r2 = client.get("/api/admin/db-due-scanner-health")
        self.assertEqual(r2.status_code, 200)
        body = r2.json()
        self.assertIn("enabled", body)
        self.assertIn("status", body)
        self.assertIn("interval_seconds", body)


if __name__ == "__main__":
    unittest.main()
