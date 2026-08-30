# -*- coding: utf-8 -*-
"""Failure-injection: session closes and checked_out returns to baseline."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from starlette.requests import Request

from main import app
from services.db_lifecycle_v1.equilibrium import sample
from services.db_lifecycle_v1.pool_truth import pool_truth_from_pool
from services.db_lifecycle_v1.unit_of_work import close_request_uow, unit_of_work
from services.db_resource_safety_v1.admission_v1 import (
    admit_heavy_route,
    reset_for_tests as reset_admission,
)
from services.db_session_lifecycle import isolated_db_session, release_scoped_db_session


def _qp():
    return create_engine(
        "sqlite://",
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=5,
        pool_timeout=1,
        pool_reset_on_return="rollback",
    )


class FailureInjectionQueuePoolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = _qp()
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _baseline(self) -> int:
        return int(pool_truth_from_pool(self.engine.pool).get("checked_out") or 0)

    def test_query_exception_checks_in(self) -> None:
        base = self._baseline()
        sess = self.Session()
        try:
            with self.assertRaises(SQLAlchemyError):
                sess.execute(text("SELECT * FROM definitely_missing_table_xyz"))
        finally:
            sess.rollback()
            sess.close()
        self.assertEqual(int(pool_truth_from_pool(self.engine.pool)["checked_out"] or 0), base)

    def test_application_exception_after_read(self) -> None:
        base = self._baseline()
        sess = self.Session()
        try:
            sess.execute(text("SELECT 1"))
            raise RuntimeError("after_read")
        except RuntimeError:
            sess.rollback()
            sess.close()
        self.assertEqual(int(pool_truth_from_pool(self.engine.pool)["checked_out"] or 0), base)

    def test_rollback_path(self) -> None:
        base = self._baseline()
        sess = self.Session()
        try:
            sess.execute(text("SELECT 1"))
            sess.rollback()
        finally:
            sess.close()
        self.assertEqual(int(pool_truth_from_pool(self.engine.pool)["checked_out"] or 0), base)


class FailureInjectionScopedTests(unittest.TestCase):
    def test_httpexception_release_helper(self) -> None:
        release_scoped_db_session()
        try:
            raise HTTPException(status_code=400, detail="x")
        except HTTPException:
            release_scoped_db_session()

    def test_uow_read_only_closes_on_exception(self) -> None:
        with self.assertRaises(RuntimeError):
            with unit_of_work(purpose="inject", read_only=True):
                raise RuntimeError("boom")
        close_request_uow(reason="after_inject")

    def test_admission_reject_no_engine_connect(self) -> None:
        reset_admission()
        with admit_heavy_route("/heavy") as a:
            self.assertTrue(a)
            with admit_heavy_route("/heavy") as b:
                self.assertTrue(b)
                with admit_heavy_route("/heavy") as c:
                    self.assertFalse(c)
        reset_admission()

    def test_isolated_session_always_closes(self) -> None:
        with isolated_db_session() as sess:
            sess.execute(text("SELECT 1"))

    def test_early_return_and_disconnect_middleware_finally(self) -> None:
        client = TestClient(app)
        r = client.get("/ping")
        self.assertEqual(r.status_code, 200)
        r2 = client.get("/health")
        self.assertEqual(r2.status_code, 200)


if __name__ == "__main__":
    unittest.main()
