# -*- coding: utf-8 -*-
"""Startup unowned checkout — QueuePool proof. Does not reopen request ownership."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool

from services.db_lifecycle_v1.request_session_scope import (
    logical_request_scopefunc,
    reset_for_tests as reset_scope,
)
from services.db_session_lifecycle import non_request_db_phase, release_scoped_db_session


def _queue_engine():
    return create_engine(
        "sqlite://",
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
        pool_reset_on_return="rollback",
        connect_args={"check_same_thread": False},
    )


class LegacyStartupLeakTests(unittest.TestCase):
    def test_query_without_remove_leaves_checkout(self) -> None:
        engine = _queue_engine()
        Session = scoped_session(
            sessionmaker(bind=engine, autoflush=False, autocommit=False),
            scopefunc=logical_request_scopefunc,
        )
        Session().execute(text("SELECT 1"))
        leftover = int(engine.pool.checkedout())
        Session.remove()
        engine.dispose()
        self.assertGreaterEqual(leftover, 1)


class NonRequestPhaseTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_scope()
        self.engine = _queue_engine()
        self.Session = scoped_session(
            sessionmaker(bind=self.engine, autoflush=False, autocommit=False),
            scopefunc=logical_request_scopefunc,
        )

    def tearDown(self) -> None:
        reset_scope()
        self.engine.dispose()

    def _patch_db(self):
        return patch.multiple(
            "services.db_session_lifecycle",
            db=type("DB", (), {"session": self.Session})(),
            remove_scoped_session=self.Session.remove,
        )

    def test_phase_returns_to_zero(self) -> None:
        peak = 0
        with self._patch_db():
            with non_request_db_phase(owner="test.startup"):
                self.Session().execute(text("SELECT 1"))
                peak = int(self.engine.pool.checkedout())
        self.assertGreaterEqual(peak, 1)
        self.assertEqual(int(self.engine.pool.checkedout()), 0)

    def test_phase_exception_still_releases(self) -> None:
        with self._patch_db():
            with self.assertRaises(RuntimeError):
                with non_request_db_phase(owner="test.startup.exc"):
                    self.Session().execute(text("SELECT 1"))
                    raise RuntimeError("startup boom")
        self.assertEqual(int(self.engine.pool.checkedout()), 0)

    def test_phase_early_return_releases(self) -> None:
        def _work() -> int:
            with self._patch_db():
                with non_request_db_phase(owner="test.startup.early"):
                    self.Session().execute(text("SELECT 1"))
                    return 0

        self.assertEqual(_work(), 0)
        self.assertEqual(int(self.engine.pool.checkedout()), 0)

    def test_phase_commit_then_close(self) -> None:
        with self._patch_db():
            with non_request_db_phase(owner="test.startup.write"):
                self.Session().execute(text("SELECT 1"))
                self.Session().commit()
        self.assertEqual(int(self.engine.pool.checkedout()), 0)


class SeedFunctionCleanupTests(unittest.TestCase):
    def test_empty_path_does_not_leave_scoped_session(self) -> None:
        from extensions import db
        from services.cartflow_demo_catalog_seed import seed_demo_store_product_catalog_if_empty

        seed_demo_store_product_catalog_if_empty()
        self.assertFalse(db.session.registry.has())

    def test_exception_path_releases(self) -> None:
        from extensions import db
        from services.cartflow_demo_catalog_seed import seed_demo_store_product_catalog_if_empty

        with patch.object(db, "create_all", side_effect=RuntimeError("ddl fail")):
            n = seed_demo_store_product_catalog_if_empty()
        self.assertEqual(n, 0)
        self.assertFalse(db.session.registry.has())

    def test_repeated_seed_does_not_accumulate(self) -> None:
        from extensions import db
        from services.cartflow_demo_catalog_seed import seed_demo_store_product_catalog_if_empty

        for _ in range(5):
            seed_demo_store_product_catalog_if_empty()
            self.assertFalse(db.session.registry.has())

    def test_startup_end_release_is_idempotent(self) -> None:
        release_scoped_db_session()
        release_scoped_db_session()
        from extensions import db

        self.assertFalse(db.session.registry.has())
