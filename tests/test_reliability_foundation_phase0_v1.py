# -*- coding: utf-8 -*-
"""Reliability Foundation V1 — Phase 0 tests."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from extensions import db, get_database_url, init_database
from services.runtime_role_verification_v1 import (
    ENV_ENFORCE_API_ONLY,
    RuntimeRoleVerificationError,
    verify_runtime_role_at_startup,
)
from services.schema_runtime_guard_v1 import request_schema_middleware_enabled


def _prod_api_env() -> None:
    os.environ["ENV"] = "production"
    os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
    os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "false"
    os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "0"
    os.environ[ENV_ENFORCE_API_ONLY] = "1"


def _clear_role_env() -> None:
    for key in (
        "ENV",
        "CARTFLOW_PROCESS_ROLE",
        "CARTFLOW_DB_DUE_SCANNER_ENABLED",
        "CARTFLOW_RECOVERY_RESUME_ON_STARTUP",
        ENV_ENFORCE_API_ONLY,
        "CARTFLOW_REQUEST_TIMING_AUDIT",
    ):
        os.environ.pop(key, None)


class RuntimeRoleVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        _clear_role_env()

    def tearDown(self) -> None:
        _clear_role_env()

    def test_api_role_valid_passes(self) -> None:
        _prod_api_env()
        out = verify_runtime_role_at_startup()
        self.assertTrue(out.get("verified"))
        self.assertEqual(out.get("role"), "api")

    def test_api_role_misconfiguration_scanner_fails(self) -> None:
        _prod_api_env()
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        with self.assertRaises(RuntimeRoleVerificationError):
            verify_runtime_role_at_startup()

    def test_api_role_misconfiguration_resume_fails(self) -> None:
        _prod_api_env()
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        with self.assertRaises(RuntimeRoleVerificationError):
            verify_runtime_role_at_startup()

    def test_enforce_api_only_rejects_scheduler_role(self) -> None:
        os.environ["ENV"] = "production"
        os.environ[ENV_ENFORCE_API_ONLY] = "1"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        with self.assertRaises(RuntimeRoleVerificationError):
            verify_runtime_role_at_startup()

    def test_scheduler_role_valid_passes(self) -> None:
        os.environ["ENV"] = "production"
        os.environ.pop(ENV_ENFORCE_API_ONLY, None)
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"
        out = verify_runtime_role_at_startup()
        self.assertTrue(out.get("verified"))
        self.assertEqual(out.get("role"), "scheduler")

    def test_development_skips_verification(self) -> None:
        os.environ["ENV"] = "development"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        out = verify_runtime_role_at_startup()
        self.assertTrue(out.get("skipped"))


class SchemaMiddlewareGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_role_env()

    def tearDown(self) -> None:
        _clear_role_env()

    def test_production_request_schema_middleware_disabled(self) -> None:
        os.environ["ENV"] = "production"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        self.assertFalse(request_schema_middleware_enabled())

    def test_api_role_schema_middleware_disabled_in_dev(self) -> None:
        os.environ["ENV"] = "development"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        self.assertFalse(request_schema_middleware_enabled())


class PoolConfigTests(unittest.TestCase):
    def test_postgres_pool_timeout_is_5s(self) -> None:
        from extensions import POSTGRES_POOL_MAX_OVERFLOW, POSTGRES_POOL_SIZE, POSTGRES_POOL_TIMEOUT

        self.assertEqual(POSTGRES_POOL_SIZE, 30)
        self.assertEqual(POSTGRES_POOL_MAX_OVERFLOW, 30)
        self.assertEqual(POSTGRES_POOL_TIMEOUT, 5)

    def test_postgres_engine_uses_pool_settings(self) -> None:
        init_database("postgresql://user:pass@localhost:5432/testdb")
        pool = db.engine.pool
        self.assertEqual(getattr(pool, "_pool", pool).maxsize, 30)  # type: ignore[attr-defined]
        self.assertEqual(pool.timeout(), 5)


class PingNoDbTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        _clear_role_env()
        os.environ["ENV"] = "development"

    def tearDown(self) -> None:
        _clear_role_env()

    def test_ping_does_not_touch_db(self) -> None:
        from fastapi.testclient import TestClient

        import main

        queries: list[str] = []

        def _before_cursor(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
            queries.append(str(statement or ""))

        from sqlalchemy import event

        event.listen(db.engine, "before_cursor_execute", _before_cursor)
        try:
            with TestClient(main.app) as client:
                resp = client.get("/ping")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"ok": True})
            self.assertEqual(queries, [])
        finally:
            event.remove(db.engine, "before_cursor_execute", _before_cursor)


class ProductionSchemaMiddlewareIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        _clear_role_env()
        os.environ["ENV"] = "production"
        os.environ["CARTFLOW_PROCESS_ROLE"] = "api"
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "false"
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "0"

    def tearDown(self) -> None:
        _clear_role_env()

    def test_production_ping_skips_schema_middleware(self) -> None:
        from fastapi.testclient import TestClient

        import main

        with patch(
            "schema_production_store_bootstrap.ensure_production_store_schema_before_request"
        ) as mock_ensure:
            with TestClient(main.app) as client:
                resp = client.get("/ping")
            self.assertEqual(resp.status_code, 200)
            mock_ensure.assert_not_called()


class RequestTimingPermanentTests(unittest.TestCase):
    def test_enabled_in_production_like_by_default(self) -> None:
        from services.request_timing_audit_v1 import request_timing_audit_enabled

        os.environ["ENV"] = "production"
        os.environ.pop("CARTFLOW_REQUEST_TIMING_AUDIT", None)
        self.assertTrue(request_timing_audit_enabled())

    def test_can_disable_explicitly(self) -> None:
        from services.request_timing_audit_v1 import request_timing_audit_enabled

        os.environ["ENV"] = "production"
        os.environ["CARTFLOW_REQUEST_TIMING_AUDIT"] = "0"
        self.assertFalse(request_timing_audit_enabled())


if __name__ == "__main__":
    unittest.main()
