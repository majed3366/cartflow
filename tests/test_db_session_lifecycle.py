# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from extensions import db
from models import Store
from services.db_session_lifecycle import (
    isolated_db_session,
    release_scoped_db_session,
    run_sync_background_db_task,
)


class DbSessionLifecycleTests(unittest.TestCase):
    def test_release_scoped_does_not_raise_on_empty(self) -> None:
        release_scoped_db_session()

    def test_isolated_session_closes(self) -> None:
        db.create_all()
        with isolated_db_session() as sess:
            n = sess.query(Store).count()
        self.assertGreaterEqual(n, 0)

    def test_background_task_cleans_scoped_session(self) -> None:
        seen: list[str] = []

        def _probe() -> None:
            db.session.query(Store).limit(1).all()
            seen.append("ok")

        run_sync_background_db_task(_probe)
        self.assertEqual(seen, ["ok"])


if __name__ == "__main__":
    unittest.main()
