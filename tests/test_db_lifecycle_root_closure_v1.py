# -*- coding: utf-8 -*-
"""INV-DB contract tests for lifecycle authority (not NullPool resource proof)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from json_response import j
from main import app
from services.db_lifecycle_v1.pg_reconciliation import (
    CLASS_IDLE_IN_TRANSACTION,
    classify_backend,
    reconcile,
)
from services.db_lifecycle_v1.pool_truth import pool_truth_from_pool, reset_for_tests
from services.db_lifecycle_v1.unit_of_work import close_request_uow_if_clean
from services.db_resource_safety_v1.admission_v1 import (
    admit_heavy_route,
    reset_for_tests as reset_admission,
)


class PoolTruthTests(unittest.TestCase):
    def test_does_not_use_status_string_only(self) -> None:
        pool = MagicMock()
        pool.status = MagicMock(return_value="Pool size: 5  Connections in pool: 5")
        pool.size = MagicMock(return_value=5)
        pool.checkedout = MagicMock(return_value=2)
        pool.checkedin = MagicMock(return_value=3)
        pool.overflow = MagicMock(return_value=-3)
        pool.__class__ = type("QueuePool", (), {})
        snap = pool_truth_from_pool(pool)
        self.assertEqual(snap["checked_out"], 2)
        self.assertEqual(snap["size"], 5)
        self.assertIn("checked_out", snap)
        self.assertNotEqual(snap.get("checked_out"), snap.get("status"))

    def test_max_connections_uses_configured_bounds_not_live_overflow(self) -> None:
        reset_for_tests()
        pool = MagicMock()
        pool.size = MagicMock(return_value=5)
        pool.checkedout = MagicMock(return_value=1)
        pool.checkedin = MagicMock(return_value=4)
        pool.overflow = MagicMock(return_value=-4)
        snap = pool_truth_from_pool(pool)
        self.assertEqual(snap["max_connections"], 10)
        self.assertEqual(snap["available_slots"], 9)


class UowCleanCloseTests(unittest.TestCase):
    def test_skips_when_pending_writes(self) -> None:
        dirty = MagicMock()
        dirty.new = {1}
        dirty.dirty = set()
        dirty.deleted = set()
        with patch("extensions.db") as db:
            db.session = dirty
            self.assertFalse(close_request_uow_if_clean(reason="test_dirty"))

    def test_j_releases_clean_session(self) -> None:
        with patch(
            "services.db_lifecycle_v1.unit_of_work.close_request_uow_if_clean",
            return_value=True,
        ) as close:
            resp = j({"ok": True})
            self.assertEqual(resp.status_code, 200)
            close.assert_called()


class AdmissionNoHiddenDbTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_admission()

    def tearDown(self) -> None:
        reset_admission()

    def test_reject_does_not_require_session(self) -> None:
        with admit_heavy_route("/api/dashboard/messages") as a:
            self.assertTrue(a)
            with admit_heavy_route("/api/dashboard/messages") as b:
                self.assertTrue(b)
                with admit_heavy_route("/api/dashboard/messages") as c:
                    self.assertFalse(c)


class HealthPoolTruthTests(unittest.TestCase):
    def test_health_includes_real_pool_object(self) -> None:
        client = TestClient(app)
        r = client.get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("pool", body)
        self.assertIn("pool_impl", body["pool"])


class PgClassifyTests(unittest.TestCase):
    def test_idle_in_transaction(self) -> None:
        self.assertEqual(
            classify_backend({"state": "idle in transaction"}),
            CLASS_IDLE_IN_TRANSACTION,
        )

    def test_reconcile_does_not_claim_leak_without_both_sides(self) -> None:
        out = reconcile(
            {"checked_out": 2},
            {"available": False, "idle_in_transaction": None},
        )
        self.assertFalse(out["leak_claimed"])
        self.assertEqual(out["verdict"], "PG_UNAVAILABLE")


class WiringNotInMainPolicyTests(unittest.TestCase):
    def test_main_does_not_own_uow_policy(self) -> None:
        from pathlib import Path

        main = (Path(__file__).resolve().parents[1] / "main.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("close_request_uow_if_clean", main)
        self.assertIn("auth_resolve_complete", main)
        self.assertNotIn("pool_size = 20", main)


if __name__ == "__main__":
    unittest.main()
