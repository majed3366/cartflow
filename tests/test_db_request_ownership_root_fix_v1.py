# -*- coding: utf-8 -*-
"""
Request-scoped DB ownership root fix — QueuePool evidence.

NullPool is forbidden here. Thread-boundary test is mandatory.
"""
from __future__ import annotations

import asyncio
import os
import threading
import unittest
from typing import Any

from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool

from services.db_lifecycle_v1.request_session_scope import (
    begin_logical_session_scope,
    current_logical_scope_id,
    end_logical_session_scope,
    logical_request_scopefunc,
    reset_for_tests as reset_scope,
)
from services.db_lifecycle_v1.unit_of_work import close_request_uow_if_clean


def _queue_engine(**kw: Any):
    opts = dict(
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
        pool_reset_on_return="rollback",
        connect_args={"check_same_thread": False},
    )
    opts.update(kw)
    return create_engine("sqlite://", **opts)


class ContextVarAnyioTests(unittest.TestCase):
    def test_contextvar_copies_into_anyio_worker(self) -> None:
        import anyio

        token = begin_logical_session_scope(request_id="req-cvar")
        main_scope = current_logical_scope_id()
        main_thread = threading.current_thread().name

        def worker() -> tuple[str, str]:
            return current_logical_scope_id() or "", threading.current_thread().name

        worker_scope, worker_thread = asyncio.run(anyio.to_thread.run_sync(worker))
        end_logical_session_scope(token)
        self.assertEqual(main_scope, "req-cvar")
        self.assertEqual(worker_scope, "req-cvar")
        self.assertNotEqual(worker_thread, main_thread)
        self.assertIn("worker", worker_thread.lower())


class LogicalScopefuncTests(unittest.TestCase):
    def tearDown(self) -> None:
        reset_scope()

    def test_scopefunc_is_request_id_not_thread(self) -> None:
        token = begin_logical_session_scope(request_id="req-own")
        key = logical_request_scopefunc()
        ident = threading.get_ident()
        end_logical_session_scope(token)
        self.assertEqual(key, ("req", "req-own"))
        self.assertNotEqual(key[1], ident)

    def test_fallback_is_thread_when_no_request(self) -> None:
        reset_scope()
        key = logical_request_scopefunc()
        self.assertEqual(key[0], "thr")
        self.assertEqual(key[1], int(threading.get_ident() or 0))


class ThreadBoundaryOwnershipTests(unittest.TestCase):
    """Exact proven defect: MainThread auth + AnyIO worker handler + MainThread finally."""

    def setUp(self) -> None:
        reset_scope()
        self.engine = _queue_engine()
        self.Session = scoped_session(
            sessionmaker(bind=self.engine, autoflush=False, autocommit=False),
            scopefunc=logical_request_scopefunc,
        )
        self.peaks: list[int] = []

    def tearDown(self) -> None:
        try:
            self.Session.remove()
        except Exception:  # noqa: BLE001
            pass
        reset_scope()
        self.engine.dispose()

    def _checked_out(self) -> int:
        return int(self.engine.pool.checkedout())

    def test_mainthread_auth_worker_handler_mainthread_remove_returns_to_zero(self) -> None:
        import anyio

        baseline = self._checked_out()
        self.assertEqual(baseline, 0)
        token = begin_logical_session_scope(request_id="req-boundary")
        main_name = threading.current_thread().name
        worker_name = {"v": ""}

        self.Session().execute(text("SELECT 1"))
        self.peaks.append(self._checked_out())
        self.Session.remove()
        self.assertEqual(self._checked_out(), 0)

        def handler() -> None:
            worker_name["v"] = threading.current_thread().name
            self.Session().execute(text("SELECT 1"))
            self.peaks.append(self._checked_out())

        asyncio.run(anyio.to_thread.run_sync(handler))
        self.assertGreaterEqual(max(self.peaks), 1)
        self.assertGreaterEqual(self._checked_out(), 1)
        self.assertNotEqual(worker_name["v"], main_name)
        self.assertIn("worker", worker_name["v"].lower())

        self.Session.remove()
        end_logical_session_scope(token)
        self.assertEqual(self._checked_out(), 0)

    def test_thread_local_scope_still_fails_without_logical_scope(self) -> None:
        engine = _queue_engine()
        Session = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
        ready = threading.Event()
        done = threading.Event()

        def worker() -> None:
            Session().execute(text("SELECT 1"))
            ready.set()
            done.wait(5)

        t = threading.Thread(target=worker, name="legacy-worker")
        t.start()
        self.assertTrue(ready.wait(5))
        Session.remove()
        leftover = int(engine.pool.checkedout())
        done.set()
        t.join(5)
        Session.remove()
        engine.dispose()
        self.assertGreaterEqual(leftover, 1)


class WriteCorrectnessTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_scope()
        self.engine = _queue_engine()
        Base = declarative_base()

        class Item(Base):
            __tablename__ = "own_items"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        self.Item = Item
        Base.metadata.create_all(self.engine)
        self.Session = scoped_session(
            sessionmaker(bind=self.engine, autoflush=False, autocommit=False),
            scopefunc=logical_request_scopefunc,
        )
        self.token = begin_logical_session_scope(request_id="req-write")

    def tearDown(self) -> None:
        try:
            self.Session.remove()
        except Exception:  # noqa: BLE001
            pass
        end_logical_session_scope(self.token)
        reset_scope()
        self.engine.dispose()

    def test_readonly_success(self) -> None:
        rows = list(self.Session().execute(text("SELECT 1")).fetchall())
        self.Session.remove()
        self.assertEqual(rows[0][0], 1)
        self.assertEqual(int(self.engine.pool.checkedout()), 0)

    def test_write_commit(self) -> None:
        sess = self.Session()
        sess.add(self.Item(name="ok"))
        sess.commit()
        self.Session.remove()
        self.assertEqual(int(self.engine.pool.checkedout()), 0)
        token = begin_logical_session_scope(request_id="req-write-read")
        n = self.Session().query(self.Item).count()
        self.Session.remove()
        end_logical_session_scope(token)
        self.assertEqual(n, 1)

    def test_write_rollback(self) -> None:
        sess = self.Session()
        sess.add(self.Item(name="nope"))
        sess.rollback()
        self.Session.remove()
        token = begin_logical_session_scope(request_id="req-write-rb")
        n = self.Session().query(self.Item).count()
        self.Session.remove()
        end_logical_session_scope(token)
        self.assertEqual(n, 0)
        self.assertEqual(int(self.engine.pool.checkedout()), 0)

    def test_write_exception(self) -> None:
        sess = self.Session()
        sess.add(self.Item(name="boom"))
        try:
            sess.execute(text("SELECT broken"))
        except Exception:
            sess.rollback()
        self.Session.remove()
        token = begin_logical_session_scope(request_id="req-write-ex")
        n = self.Session().query(self.Item).count()
        self.Session.remove()
        end_logical_session_scope(token)
        self.assertEqual(n, 0)

    def test_dirty_session_not_auto_released(self) -> None:
        from unittest.mock import patch

        sess = self.Session()
        sess.add(self.Item(name="dirty"))
        self.assertTrue(bool(sess.new or sess.dirty))
        with patch("extensions.db") as db:
            db.session = sess
            released = close_request_uow_if_clean(reason="test_dirty")
        self.assertFalse(released)
        sess.rollback()
        self.Session.remove()
        self.assertEqual(int(self.engine.pool.checkedout()), 0)

    def test_clean_session_may_release(self) -> None:
        from unittest.mock import patch

        sess = self.Session()
        sess.execute(text("SELECT 1"))
        with patch("extensions.db") as db:
            db.session = sess
            with patch(
                "services.db_lifecycle_v1.unit_of_work.release_before_response"
            ) as rel:
                released = close_request_uow_if_clean(reason="test_clean")
        self.assertTrue(released)
        rel.assert_called()
        self.Session.remove()
        self.assertEqual(int(self.engine.pool.checkedout()), 0)


class ExitPathMiniAppTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_scope()
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse, JSONResponse
        from fastapi.testclient import TestClient

        self.engine = _queue_engine()
        Session = scoped_session(
            sessionmaker(bind=self.engine, autoflush=False, autocommit=False),
            scopefunc=logical_request_scopefunc,
        )
        self.Session = Session
        app = FastAPI()

        @app.middleware("http")
        async def _own(request: Any, call_next: Any) -> Any:
            rid = request.headers.get("x-cartflow-request-id") or "mini"
            token = begin_logical_session_scope(request_id=rid)
            try:
                try:
                    return await call_next(request)
                finally:
                    Session.remove()
                    self.assertEqual(int(self.engine.pool.checkedout()), 0)
            finally:
                end_logical_session_scope(token)

        @app.get("/ok")
        def ok() -> dict[str, bool]:
            Session().execute(text("SELECT 1"))
            return {"ok": True}

        @app.get("/http-exc")
        def http_exc() -> None:
            Session().execute(text("SELECT 1"))
            raise HTTPException(status_code=418, detail="teapot")

        @app.get("/app-exc")
        def app_exc() -> None:
            Session().execute(text("SELECT 1"))
            raise RuntimeError("handler boom")

        @app.get("/early")
        def early() -> JSONResponse:
            Session().execute(text("SELECT 1"))
            return JSONResponse({"early": True}, status_code=204)

        @app.get("/db-exc")
        def db_exc() -> None:
            Session().execute(text("SELECT this_is_not_sql"))

        @app.get("/html")
        def html() -> HTMLResponse:
            Session().execute(text("SELECT 1"))
            return HTMLResponse("<p>ok</p>")

        @app.get("/after-db-wait")
        def after_db_wait() -> dict[str, bool]:
            Session().execute(text("SELECT 1"))
            Session.remove()
            return {"released": True}

        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        reset_scope()
        self.engine.dispose()

    def _assert_idle(self) -> None:
        self.assertEqual(int(self.engine.pool.checkedout()), 0)
        self.assertIsNone(current_logical_scope_id())

    def test_success_200(self) -> None:
        r = self.client.get("/ok")
        self.assertEqual(r.status_code, 200)
        self._assert_idle()

    def test_http_exception(self) -> None:
        r = self.client.get("/http-exc")
        self.assertEqual(r.status_code, 418)
        self._assert_idle()

    def test_application_exception(self) -> None:
        r = self.client.get("/app-exc")
        self.assertEqual(r.status_code, 500)
        self._assert_idle()

    def test_early_return(self) -> None:
        r = self.client.get("/early")
        self.assertEqual(r.status_code, 204)
        self._assert_idle()

    def test_db_exception(self) -> None:
        r = self.client.get("/db-exc")
        self.assertEqual(r.status_code, 500)
        self._assert_idle()

    def test_html_response(self) -> None:
        r = self.client.get("/html")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"<p>", r.content)
        self._assert_idle()

    def test_external_wait_after_db_phase(self) -> None:
        r = self.client.get("/after-db-wait")
        self.assertEqual(r.status_code, 200)
        self._assert_idle()


class QueuePoolRequestEquilibriumTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_scope()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        self.engine = _queue_engine()
        Session = scoped_session(
            sessionmaker(bind=self.engine, autoflush=False, autocommit=False),
            scopefunc=logical_request_scopefunc,
        )
        app = FastAPI()

        @app.middleware("http")
        async def _own(request: Any, call_next: Any) -> Any:
            token = begin_logical_session_scope(request_id=request.headers.get("x-id") or "eq")
            try:
                try:
                    return await call_next(request)
                finally:
                    Session.remove()
            finally:
                end_logical_session_scope(token)

        self.peaks: list[int] = []

        @app.get("/dashboard")
        def dashboard() -> dict[str, str]:
            Session().execute(text("SELECT 1"))
            self.peaks.append(int(self.engine.pool.checkedout()))
            return {"page": "dashboard"}

        self.client = TestClient(app)
        self.Session = Session

    def tearDown(self) -> None:
        reset_scope()
        self.engine.dispose()

    def test_idle_dashboard_idle_twenty_times(self) -> None:
        baseline = int(self.engine.pool.checkedout())
        self.assertEqual(baseline, 0)
        for i in range(20):
            r = self.client.get("/dashboard", headers={"x-id": f"eq-{i}"})
            self.assertEqual(r.status_code, 200)
            after = int(self.engine.pool.checkedout())
            self.assertEqual(after, 0, f"retained after request {i}")
        self.assertGreaterEqual(max(self.peaks or [0]), 1)
        self.assertEqual(int(self.engine.pool.checkedout()), 0)
        self.assertEqual(type(self.engine.pool).__name__, "QueuePool")


class RepresentativeSyncRouteTests(unittest.TestCase):
    """Same middleware/ownership — do not patch these routes."""

    @classmethod
    def setUpClass(cls) -> None:
        from fastapi.testclient import TestClient

        from main import app

        cls.client = TestClient(app, raise_server_exceptions=False)

    def _hit(self, path: str) -> int:
        r = self.client.get(path, follow_redirects=False)
        self.assertIsNone(current_logical_scope_id())
        self.assertIn(r.status_code, {200, 204, 302, 303, 401, 403, 404, 418, 503})
        return r.status_code

    def test_dashboard(self) -> None:
        self._hit("/dashboard")

    def test_carts(self) -> None:
        self._hit("/dashboard/normal-carts")

    def test_communication(self) -> None:
        self._hit("/dashboard/cartflow-messages")

    def test_settings(self) -> None:
        self._hit("/dashboard/general-settings")

    def test_auth_adjacent_login(self) -> None:
        code = self._hit("/login")
        self.assertEqual(code, 200)

    def test_auth_adjacent_messages_unauthenticated(self) -> None:
        self._hit("/api/dashboard/messages")


class PostgresIdleInTransactionTests(unittest.TestCase):
    def test_no_open_transaction_after_logical_remove(self) -> None:
        engine = _queue_engine()
        Session = scoped_session(
            sessionmaker(bind=engine, autoflush=False, autocommit=False),
            scopefunc=logical_request_scopefunc,
        )
        token = begin_logical_session_scope(request_id="req-iit")
        sess = Session()
        sess.execute(text("SELECT 1"))
        self.assertTrue(sess.in_transaction())
        Session.remove()
        end_logical_session_scope(token)
        self.assertEqual(int(engine.pool.checkedout()), 0)
        engine.dispose()

    def test_postgres_iit_when_url_available(self) -> None:
        url = (os.getenv("TEST_DATABASE_URL") or "").strip()
        if not url.startswith("postgres"):
            self.skipTest("TEST_DATABASE_URL postgres not configured")
        from sqlalchemy import create_engine as ce

        engine = ce(
            url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=5,
            pool_timeout=5,
            pool_pre_ping=True,
        )
        Session = scoped_session(
            sessionmaker(bind=engine, autoflush=False, autocommit=False),
            scopefunc=logical_request_scopefunc,
        )
        token = begin_logical_session_scope(request_id="req-pg-iit")
        Session().execute(text("SELECT 1"))
        Session.remove()
        end_logical_session_scope(token)
        with engine.connect() as conn:
            n = conn.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE state = 'idle in transaction' "
                    "AND pid <> pg_backend_pid()"
                )
            ).scalar()
        engine.dispose()
        self.assertEqual(int(n or 0), 0)


class NoRouteSpecificPatchTests(unittest.TestCase):
    def test_dashboard_handler_has_no_session_remove(self) -> None:
        from pathlib import Path

        text_src = Path("routes/merchant_pages.py").read_text(encoding="utf-8")
        self.assertNotIn("remove_scoped_session", text_src)
        self.assertNotIn("db.session.remove", text_src)
