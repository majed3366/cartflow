# -*- coding: utf-8 -*-
"""Residual checkout owner — instrumentation + thread-local scoped_session proof."""
from __future__ import annotations

import threading
import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool

from services.db_lifecycle_v1.holder_diag_v1 import emit, engine_inventory, thread_task_identity
from services.db_lifecycle_v1.connection_trace import maybe_install_connection_trace


class ThreadLocalScopedSessionTests(unittest.TestCase):
    def test_remove_on_other_thread_does_not_checkin(self) -> None:
        engine = create_engine(
            "sqlite://",
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=0,
            pool_timeout=2,
        )
        Session = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
        ready = threading.Event()
        released = threading.Event()
        worker_ident = {"v": 0}

        def worker() -> None:
            worker_ident["v"] = threading.get_ident()
            Session().execute(text("SELECT 1"))
            ready.set()
            released.wait(5)

        t = threading.Thread(target=worker, name="dash-worker")
        t.start()
        self.assertTrue(ready.wait(5))
        self.assertGreaterEqual(int(engine.pool.checkedout()), 1)
        # Simulate async middleware finally on a different thread:
        Session.remove()
        still = int(engine.pool.checkedout())
        released.set()
        t.join(5)
        Session.remove()
        engine.dispose()
        self.assertGreaterEqual(still, 1)
        self.assertNotEqual(worker_ident["v"], threading.get_ident())


class InstrumentationSurfaceTests(unittest.TestCase):
    def test_emit_uses_stdout(self) -> None:
        emit("[DB CHECKOUT] test")

    def test_thread_identity_has_ident(self) -> None:
        ident = thread_task_identity()
        self.assertIn("thread_ident", ident)
        self.assertGreater(int(ident["thread_ident"]), 0)

    def test_engine_inventory_single_runtime_engine(self) -> None:
        inv = engine_inventory()
        self.assertEqual(inv.get("engine_count"), 1)
        self.assertTrue(inv.get("same_object"))

    def test_trace_install_is_idempotent(self) -> None:
        maybe_install_connection_trace()
        maybe_install_connection_trace()


class HealthDiagContractTests(unittest.TestCase):
    def test_health_includes_holder_fields(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        r = client.get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("holders", body)
        self.assertIn("engine", body)
        self.assertIn("pool", body)
