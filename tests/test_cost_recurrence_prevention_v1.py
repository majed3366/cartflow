# -*- coding: utf-8 -*-
"""Cost Recurrence Prevention V1 — process, guard, pool, health, budget."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from services.database_network_guard_v1 import (
    CLASS_MALFORMED,
    CLASS_MISSING,
    CLASS_PRIVATE,
    CLASS_PUBLIC_PROXY,
    DatabaseNetworkGuardError,
    assert_database_url_allowed,
    classify_database_url,
)
from services.db_pool_bounds_v1 import PoolBoundsError, resolve_pool_bounds
from services.process_entry_v1 import (
    ProcessEntryError,
    configure_api_entry,
    configure_scheduler_entry,
    reject_scheduler_via_web_entry,
)
from services.recovery_process_role_v1 import build_scheduler_health_snapshot
from services.scheduler_cycle_guard_v1 import (
    min_sleep_seconds,
    next_sleep_seconds,
    record_cycle_error,
    record_cycle_ok,
    reset_cycle_guard_for_tests,
)
from services.snapshot_cycle_budget_v1 import (
    SnapshotCycleBudget,
    SnapshotCycleBudgetExceeded,
)


class ProcessEntryTests(unittest.TestCase):
    def tearDown(self) -> None:
        for k in ("CARTFLOW_PROCESS_ENTRY", "CARTFLOW_PROCESS_ROLE", "ENV"):
            os.environ.pop(k, None)

    def test_api_entry_rejects_scheduler_role(self) -> None:
        os.environ["CARTFLOW_PROCESS_ENTRY"] = "api"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        with self.assertRaises(ProcessEntryError):
            reject_scheduler_via_web_entry()

    def test_production_web_entry_rejects_scheduler_role(self) -> None:
        os.environ["ENV"] = "production"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        with self.assertRaises(ProcessEntryError):
            reject_scheduler_via_web_entry()

    def test_configure_helpers(self) -> None:
        configure_api_entry()
        self.assertEqual(os.environ["CARTFLOW_PROCESS_ENTRY"], "api")
        configure_scheduler_entry()
        self.assertEqual(os.environ["CARTFLOW_PROCESS_ENTRY"], "scheduler")
        self.assertEqual(os.environ["CARTFLOW_PROCESS_ROLE"], "scheduler")


class DatabaseNetworkGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ENV"] = "production"
        os.environ.pop("CARTFLOW_ALLOW_PUBLIC_DATABASE", None)
        os.environ.pop("DATABASE_URL", None)

    def tearDown(self) -> None:
        for k in ("ENV", "CARTFLOW_ALLOW_PUBLIC_DATABASE", "DATABASE_URL"):
            os.environ.pop(k, None)

    def test_private_railway_accepted(self) -> None:
        d = classify_database_url("postgresql://u:p@postgres.railway.internal:5432/app")
        self.assertEqual(d["class"], CLASS_PRIVATE)
        out = assert_database_url_allowed(
            "postgresql://u:p@postgres.railway.internal:5432/app"
        )
        self.assertTrue(out["allowed"])

    def test_public_proxy_rejected(self) -> None:
        d = classify_database_url("postgresql://u:p@roundhouse.proxy.rlwy.net:1234/app")
        self.assertEqual(d["class"], CLASS_PUBLIC_PROXY)
        with self.assertRaises(DatabaseNetworkGuardError) as ctx:
            assert_database_url_allowed(
                "postgresql://u:p@roundhouse.proxy.rlwy.net:1234/app"
            )
        msg = str(ctx.exception)
        self.assertIn("public_proxy", msg)
        self.assertNotIn("roundhouse", msg)
        self.assertNotIn("u:p", msg)
        self.assertNotIn("1234", msg)

    def test_missing_rejected(self) -> None:
        with self.assertRaises(DatabaseNetworkGuardError) as ctx:
            assert_database_url_allowed("")
        self.assertIn("missing", str(ctx.exception))

    def test_malformed_rejected(self) -> None:
        d = classify_database_url("not-a-url")
        self.assertEqual(d["class"], CLASS_MALFORMED)
        with self.assertRaises(DatabaseNetworkGuardError):
            assert_database_url_allowed("not-a-url")

    def test_emergency_override(self) -> None:
        os.environ["CARTFLOW_ALLOW_PUBLIC_DATABASE"] = "1"
        out = assert_database_url_allowed(
            "postgresql://u:p@roundhouse.proxy.rlwy.net:1234/app"
        )
        self.assertTrue(out["allowed"])
        self.assertEqual(out["reason"], "emergency_override")

    def test_secrets_never_in_error(self) -> None:
        secret = "postgresql://superuser:hunter2@roundhouse.proxy.rlwy.net:5432/secretdb"
        with self.assertRaises(DatabaseNetworkGuardError) as ctx:
            assert_database_url_allowed(secret)
        blob = str(ctx.exception)
        self.assertNotIn("hunter2", blob)
        self.assertNotIn("superuser", blob)
        self.assertNotIn("secretdb", blob)
        self.assertNotIn("roundhouse", blob)
        self.assertNotIn(secret, blob)


class SchedulerIntervalTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_cycle_guard_for_tests()

    def test_never_zero_sleep(self) -> None:
        reset_cycle_guard_for_tests()
        self.assertGreaterEqual(next_sleep_seconds(0), min_sleep_seconds())
        self.assertGreaterEqual(next_sleep_seconds(-1), min_sleep_seconds())
        record_cycle_error()
        record_cycle_error()
        self.assertGreaterEqual(next_sleep_seconds(5), min_sleep_seconds())
        record_cycle_ok()
        self.assertEqual(next_sleep_seconds(30), 30)

    def test_backoff_grows(self) -> None:
        reset_cycle_guard_for_tests()
        record_cycle_error()
        a = next_sleep_seconds(10)
        record_cycle_error()
        b = next_sleep_seconds(10)
        self.assertGreater(b, a)


class SnapshotBudgetTests(unittest.TestCase):
    def test_empty_cycle_not_busy(self) -> None:
        from services.dashboard_snapshot_loop_v1 import dashboard_snapshot_loop_interval_seconds

        os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_INTERVAL_SECONDS", None)
        interval = dashboard_snapshot_loop_interval_seconds()
        self.assertGreaterEqual(interval, 15.0)
        self.assertGreaterEqual(next_sleep_seconds(interval), min_sleep_seconds())

    def test_byte_budget_aborts(self) -> None:
        os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_CYCLE_BYTE_BUDGET"] = "50000"
        b = SnapshotCycleBudget(50_000)
        b.add(40_000)
        with self.assertRaises(SnapshotCycleBudgetExceeded):
            b.add(20_000)
        self.assertTrue(b.aborted)
        self.assertEqual(b.metrics()["cycle_records"], 1)
        os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_CYCLE_BYTE_BUDGET", None)


class HealthNoDbTests(unittest.TestCase):
    def test_health_snapshot_does_not_query_db(self) -> None:
        os.environ["ENV"] = "development"
        with patch("extensions.db.session.query") as mock_q:
            snap = build_scheduler_health_snapshot()
        mock_q.assert_not_called()
        self.assertEqual(snap.get("source"), "in_process_cache")
        os.environ.pop("ENV", None)


class PoolBoundsTests(unittest.TestCase):
    def tearDown(self) -> None:
        for k in (
            "CARTFLOW_PROCESS_ROLE",
            "CARTFLOW_DB_POOL_SIZE",
            "CARTFLOW_DB_POOL_MAX_OVERFLOW",
            "CARTFLOW_DB_POOL_TIMEOUT",
        ):
            os.environ.pop(k, None)

    def test_api_defaults(self) -> None:
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        b = resolve_pool_bounds()
        self.assertEqual(b["pool_size"], 5)
        self.assertEqual(b["max_overflow"], 5)

    def test_scheduler_defaults(self) -> None:
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        b = resolve_pool_bounds()
        self.assertEqual(b["pool_size"], 2)
        self.assertEqual(b["max_overflow"], 2)

    def test_excessive_fails(self) -> None:
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        os.environ["CARTFLOW_DB_POOL_SIZE"] = "99"
        with self.assertRaises(PoolBoundsError):
            resolve_pool_bounds()

    def test_invalid_fails(self) -> None:
        os.environ["CARTFLOW_DB_POOL_SIZE"] = "nope"
        with self.assertRaises(PoolBoundsError):
            resolve_pool_bounds()


class SnapshotBuilderDefaultOffTests(unittest.TestCase):
    def tearDown(self) -> None:
        for k in (
            "CARTFLOW_DASHBOARD_SNAPSHOT_MODE",
            "CARTFLOW_DASHBOARD_SNAPSHOT_BUILDER_ENABLED",
            "CARTFLOW_PROCESS_ROLE",
            "CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED",
        ):
            os.environ.pop(k, None)

    def test_scheduler_role_does_not_auto_enable_builder(self) -> None:
        from services.dashboard_snapshot_builder_v1 import dashboard_snapshot_builder_enabled

        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_MODE"] = "1"
        os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_BUILDER_ENABLED", None)
        self.assertFalse(dashboard_snapshot_builder_enabled())

    def test_archive_defaults_off(self) -> None:
        from services.dashboard_snapshot_archive_v1 import dashboard_snapshot_archive_enabled

        os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_ARCHIVE_ENABLED", None)
        self.assertFalse(dashboard_snapshot_archive_enabled())


class SingleInstanceAndOverlapTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_cycle_guard_for_tests()
        os.environ.pop("CARTFLOW_SCHEDULER_SKIP_INSTANCE_LOCK", None)

    def test_skip_instance_lock_flag(self) -> None:
        from services.scheduler_cycle_guard_v1 import try_acquire_scheduler_instance_lock

        os.environ["CARTFLOW_SCHEDULER_SKIP_INSTANCE_LOCK"] = "1"
        out = try_acquire_scheduler_instance_lock()
        self.assertTrue(out["acquired"])
        self.assertEqual(out["backend"], "skipped")

    def test_postgres_lock_not_acquired_fails_closed(self) -> None:
        from services.scheduler_cycle_guard_v1 import (
            SchedulerInstanceLockError,
            try_acquire_scheduler_instance_lock,
        )

        os.environ.pop("CARTFLOW_SCHEDULER_SKIP_INSTANCE_LOCK", None)
        class _FakeEngine:
            url = "postgresql://u:p@localhost/app"

        class _FakeSession:
            def execute(self, *_a, **_k):
                class _R:
                    def scalar(self):
                        return False

                return _R()

            def commit(self) -> None:
                return None

            def rollback(self) -> None:
                return None

        with patch("extensions.db") as mock_db:
            mock_db.engine = _FakeEngine()
            mock_db.session = _FakeSession()
            with self.assertRaises(SchedulerInstanceLockError):
                try_acquire_scheduler_instance_lock()

    def test_scanner_source_has_no_create_all(self) -> None:
        import inspect

        import services.recovery_db_due_scanner as scanner

        self.assertNotIn("create_all", inspect.getsource(scanner))

    def test_api_startup_does_not_start_scheduler_loops(self) -> None:
        import inspect

        import main as main_mod

        src = inspect.getsource(main_mod._startup_whatsapp_queue)
        self.assertNotIn("run_scheduler_drivers_at_startup", src)
        self.assertNotIn("start_db_due_recovery_scanner_loop", src)
        self.assertNotIn("start_dashboard_snapshot_builder_loop", src)
        self.assertNotIn("start_dashboard_snapshot_archive_loop", src)

    def test_scheduler_entry_does_not_import_fastapi_app(self) -> None:
        from pathlib import Path

        text = Path("cartflow_scheduler.py").read_text(encoding="utf-8")
        self.assertNotIn("from main import app", text)
        self.assertNotIn("import uvicorn", text)
        self.assertNotIn("from fastapi", text)
        self.assertNotIn("FastAPI(", text)


class LargePayloadBudgetTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("CARTFLOW_DASHBOARD_SNAPSHOT_CYCLE_BYTE_BUDGET", None)

    def test_many_records_remain_bounded(self) -> None:
        os.environ["CARTFLOW_DASHBOARD_SNAPSHOT_CYCLE_BYTE_BUDGET"] = "100000"
        b = SnapshotCycleBudget(100_000)
        written = 0
        aborted = False
        try:
            for _ in range(10_000):
                b.add(20_000)
                written += 1
        except SnapshotCycleBudgetExceeded:
            aborted = True
        self.assertTrue(aborted)
        self.assertLessEqual(b.used_bytes, 100_000)
        self.assertLessEqual(written, 5)


if __name__ == "__main__":
    unittest.main()
