# -*- coding: utf-8 -*-
"""DB concurrency root closure — invariants, failure injection, QueuePool equilibrium."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from services.db_lifecycle_v1.equilibrium import run_four_phase
from services.db_lifecycle_v1.http_bind import HEAVY_GET_ROUTES, maybe_reject_heavy_before_db
from services.db_lifecycle_v1.pg_reconciliation import classify_backend, reconcile
from services.db_lifecycle_v1.pool_truth import pool_truth_from_pool
from services.db_lifecycle_v1.unit_of_work import (
    close_request_uow_if_clean,
    release_before_response,
    short_db_phase,
)
from services.db_resource_safety_v1.admission_v1 import (
    admit_heavy_route,
    reset_for_tests,
    snapshot as admission_snapshot,
    try_acquire,
)

ROOT = Path(__file__).resolve().parents[1]


def _queue_engine():
    return create_engine(
        "sqlite://",
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
        connect_args={"check_same_thread": False},
    )


class InvariantContractTests(unittest.TestCase):
    def test_invariants_documented(self) -> None:
        text_doc = (ROOT / "docs/architecture/db_concurrency_root_closure_v1/02_INVARIANTS.md").read_text(
            encoding="utf-8"
        )
        for inv in [f"INV-DB-{i:02d}" for i in range(1, 13)]:
            self.assertIn(inv, text_doc)

    def test_pool_bounds_unchanged(self) -> None:
        from services.db_pool_bounds_v1 import API_DEFAULT_OVERFLOW, API_DEFAULT_SIZE, DEFAULT_TIMEOUT

        self.assertEqual(API_DEFAULT_SIZE, 5)
        self.assertEqual(API_DEFAULT_OVERFLOW, 5)
        self.assertEqual(DEFAULT_TIMEOUT, 5)

    def test_heavy_routes_do_not_include_health(self) -> None:
        self.assertNotIn("/health", HEAVY_GET_ROUTES)
        self.assertNotIn("/ping", HEAVY_GET_ROUTES)
        self.assertNotIn("/login", HEAVY_GET_ROUTES)


class AdmissionBeforeDbTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_for_tests()

    def tearDown(self) -> None:
        reset_for_tests()

    def test_unauthenticated_heavy_get_rejects_without_acquire(self) -> None:
        req = MagicMock()
        req.url.path = "/api/dashboard/messages"
        req.method = "GET"
        req.cookies = {}
        resp = maybe_reject_heavy_before_db(req)
        self.assertIsNotNone(resp)
        self.assertEqual(getattr(resp, "status_code", None), 401)
        self.assertEqual(admission_snapshot()["rejected"], 0)
        self.assertEqual(admission_snapshot()["global_in_use"], 0)

    def test_non_heavy_is_n_a(self) -> None:
        req = MagicMock()
        req.url.path = "/ping"
        req.method = "GET"
        req.cookies = {}
        self.assertIsNone(maybe_reject_heavy_before_db(req))
        self.assertEqual(admission_snapshot()["global_in_use"], 0)

    def test_already_admitted_skips_second_acquire(self) -> None:
        from services.db_lifecycle_v1.request_owner import bind_admission, request_owner_begin

        req = MagicMock()
        req.url.path = "/api/dashboard/messages"
        req.method = "GET"
        req.headers = {}
        request_owner_begin(req)
        bind_admission("admitted")
        self.assertTrue(try_acquire("/other"))
        with admit_heavy_route("/api/dashboard/messages") as ok:
            self.assertTrue(ok)
        snap = admission_snapshot()
        self.assertEqual(snap["global_in_use"], 1)


class UnitOfWorkTests(unittest.TestCase):
    def test_short_phase_releases_on_exception(self) -> None:
        released = {"n": 0}

        def _rel(*, reason: str = "") -> None:
            released["n"] += 1

        import services.db_lifecycle_v1.unit_of_work as uow

        orig = uow.release_before_response
        uow.release_before_response = _rel  # type: ignore[method-assign]
        try:
            with self.assertRaises(RuntimeError):
                with uow.short_db_phase(reason="boom"):
                    raise RuntimeError("db query failed")
        finally:
            uow.release_before_response = orig  # type: ignore[method-assign]
        self.assertEqual(released["n"], 1)

    def test_close_clean_returns_bool(self) -> None:
        self.assertTrue(close_request_uow_if_clean(reason="test") in (True, False))
        release_before_response(reason="test")


class QueuePoolEquilibriumTests(unittest.TestCase):
    def test_checkout_returns_to_baseline(self) -> None:
        eng = _queue_engine()
        pool = eng.pool
        conns = []

        def activity() -> None:
            for _ in range(4):
                conns.append(eng.connect())
            for c in conns:
                c.close()
            conns.clear()

        result = run_four_phase(pool=pool, activity=activity, settle_s=0.01)
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["timeout_delta"], 0)
        truth = pool_truth_from_pool(pool)
        self.assertEqual(truth.get("checked_out"), 0)
        eng.dispose()

    def test_numeric_truth_not_status_only(self) -> None:
        eng = _queue_engine()
        snap = pool_truth_from_pool(eng.pool)
        self.assertIn("checked_out", snap)
        self.assertIsInstance(snap["checked_out"], int)
        c = eng.connect()
        mid = pool_truth_from_pool(eng.pool)
        self.assertGreaterEqual(int(mid["checked_out"] or 0), 1)
        c.close()
        eng.dispose()


class FailureInjectionQueuePoolTests(unittest.TestCase):
    def test_exception_after_checkout_checks_in(self) -> None:
        eng = _queue_engine()
        baseline = int(pool_truth_from_pool(eng.pool).get("checked_out") or 0)
        try:
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
                raise RuntimeError("after db read")
        except RuntimeError:
            pass
        self.assertEqual(int(pool_truth_from_pool(eng.pool).get("checked_out") or 0), baseline)
        eng.dispose()

    def test_early_return_checks_in(self) -> None:
        eng = _queue_engine()
        baseline = int(pool_truth_from_pool(eng.pool).get("checked_out") or 0)

        def handler() -> str:
            conn = eng.connect()
            try:
                conn.execute(text("SELECT 1"))
                return "early"
            finally:
                conn.close()

        self.assertEqual(handler(), "early")
        self.assertEqual(int(pool_truth_from_pool(eng.pool).get("checked_out") or 0), baseline)
        eng.dispose()


class PgReconcileTests(unittest.TestCase):
    def test_classify(self) -> None:
        self.assertEqual(classify_backend({"state": "active"}), "ACTIVE_QUERY")
        self.assertEqual(classify_backend({"state": "idle"}), "IDLE")
        self.assertEqual(
            classify_backend({"state": "idle in transaction"}), "IDLE_IN_TRANSACTION"
        )
        self.assertEqual(classify_backend({"wait_event_type": "Lock"}), "LOCK_WAIT")

    def test_does_not_claim_leak_without_both_sides(self) -> None:
        rec = reconcile({"checked_out": 2}, {"available": False})
        self.assertFalse(rec["leak_claimed"])
        rec2 = reconcile({"checked_out": 0}, {"available": True, "idle_in_transaction": 0})
        self.assertEqual(rec2["verdict"], "EQUILIBRIUM")


class StaticChokePointTests(unittest.TestCase):
    def test_release_before_wait_on_vip_and_zid(self) -> None:
        vip = (ROOT / "services/vip_operational_truth_v1.py").read_text(encoding="utf-8")
        zid = (ROOT / "integrations/zid_client.py").read_text(encoding="utf-8")
        wa = (ROOT / "services/whatsapp_provider.py").read_text(encoding="utf-8")
        self.assertIn("release_before_external_wait", vip)
        self.assertIn("release_before_external_wait", zid)
        self.assertIn("release_before_external_wait", wa)

    def test_middleware_admits_before_db(self) -> None:
        main_py = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("maybe_reject_heavy_before_db", main_py)
        self.assertIn("close_request_uow_if_clean", main_py)


class HttpSurfaceTests(unittest.TestCase):
    def test_ping_and_health_have_no_checkout_requirement(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        ping = client.get("/ping")
        self.assertEqual(ping.status_code, 200)
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        body = health.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("pool", body)


if __name__ == "__main__":
    unittest.main()
