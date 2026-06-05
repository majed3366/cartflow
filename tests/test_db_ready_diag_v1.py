# -*- coding: utf-8 -*-
"""DB Ready deep trace + operational snapshot (Step 4A)."""
from __future__ import annotations

import io
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from services.db_ready_admin_v1 import (
    build_admin_db_ready_health_section_readonly,
    build_db_ready_admin_alert,
)
from services.db_ready_diag_v1 import (
    clear_db_ready_diag_for_tests,
    db_ready_log_stage,
    db_ready_run,
    db_ready_stage,
)
from services.db_ready_operational_snapshot_v1 import (
    classify_db_ready_status,
    clear_db_ready_operational_snapshot_for_tests,
    load_db_ready_operational_snapshot,
    record_db_ready_run,
    status_emoji,
)


class DbReadyDiagV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        clear_db_ready_diag_for_tests()
        clear_db_ready_operational_snapshot_for_tests()

    def tearDown(self) -> None:
        clear_db_ready_diag_for_tests()
        clear_db_ready_operational_snapshot_for_tests()

    def test_stage_log_format(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            with db_ready_run(source="test"):
                with db_ready_stage("create_all"):
                    time.sleep(0.01)
                db_ready_log_stage("custom_marker")
        text = buf.getvalue()
        self.assertIn("[DB READY STAGE]", text)
        self.assertIn("stage=enter", text)
        self.assertIn("stage=create_all_start", text)
        self.assertIn("stage=create_all_done", text)
        self.assertIn("stage_elapsed_ms=", text)
        self.assertIn("query_count=", text)
        self.assertIn("trace_id=", text)
        self.assertIn("stage=exit", text)

    def test_status_classification(self) -> None:
        self.assertEqual(classify_db_ready_status(500), "healthy")
        self.assertEqual(classify_db_ready_status(3000), "healthy")
        self.assertEqual(classify_db_ready_status(3001), "slow")
        self.assertEqual(classify_db_ready_status(15000), "slow")
        self.assertEqual(classify_db_ready_status(15001), "blocking")
        self.assertEqual(status_emoji("blocking"), "🔴")

    def test_snapshot_record_and_admin_section(self) -> None:
        record_db_ready_run(
            {
                "trace_id": "abc12345",
                "duration_ms": 4200.0,
                "slowest_stage": "identity_backfill",
                "lock_wait_ms": 88.0,
                "query_count": 12,
                "total_sql_ms": 900.0,
                "success": True,
            }
        )
        snap = load_db_ready_operational_snapshot(reload_db=False)
        self.assertEqual(snap["status"], "slow")
        self.assertEqual(snap["last_stage"], "identity_backfill")
        self.assertEqual(int(snap["last_query_count"]), 12)
        section = build_admin_db_ready_health_section_readonly()
        self.assertEqual(section["status"], "slow")
        self.assertIn("Dashboard initialization", section["problem_en"])
        self.assertEqual(section["technical"]["last_trace_id"], "abc12345")
        alert = build_db_ready_admin_alert()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.get("kind"), "dashboard_db_init_slow")

    def test_healthy_run_no_alert(self) -> None:
        record_db_ready_run(
            {
                "trace_id": "fast1111",
                "duration_ms": 120.0,
                "slowest_stage": "schema_verify",
                "lock_wait_ms": 0.0,
                "query_count": 2,
                "total_sql_ms": 40.0,
                "success": True,
            }
        )
        self.assertIsNone(build_db_ready_admin_alert())
        section = build_admin_db_ready_health_section_readonly()
        self.assertEqual(section["status"], "healthy")


class DbReadyMainIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_db_ready_diag_for_tests()
        clear_db_ready_operational_snapshot_for_tests()
        import main

        main._cartflow_api_db_warmed = False

    def tearDown(self) -> None:
        clear_db_ready_diag_for_tests()
        clear_db_ready_operational_snapshot_for_tests()
        import main

        main._cartflow_api_db_warmed = True

    def test_merchant_dashboard_db_ready_emits_stage_logs(self) -> None:
        import main
        from schema_production_store_bootstrap import reset_production_store_schema_bootstrap_for_tests

        reset_production_store_schema_bootstrap_for_tests()
        main._cartflow_api_db_warmed = True
        buf = io.StringIO()
        with patch(
            "schema_production_store_bootstrap.ensure_production_store_schema",
            return_value=True,
        ):
            with redirect_stdout(buf):
                main._merchant_dashboard_db_ready()
        text = buf.getvalue()
        self.assertIn("[DB READY STAGE] stage=enter", text)
        self.assertIn("stage=schema_verify_start", text)
        self.assertIn("stage=schema_verify_done", text)


if __name__ == "__main__":
    unittest.main()
