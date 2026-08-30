# -*- coding: utf-8 -*-
"""QueuePool equilibrium harness — NullPool is forbidden for this proof."""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy.pool import QueuePool

from services.db_lifecycle_v1.connection_trace import install_on_pool, reset_for_tests as reset_holders
from services.db_lifecycle_v1.equilibrium import run_four_phase
from services.db_lifecycle_v1.pool_truth import pool_truth_from_pool, reset_for_tests


def _queue_engine():
    return create_engine(
        "sqlite://",
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=5,
        pool_timeout=1,
        pool_reset_on_return="rollback",
    )


class QueuePoolEquilibriumTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_for_tests()
        reset_holders()
        self.engine = _queue_engine()
        install_on_pool(self.engine.pool)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_pool_is_queuepool_not_nullpool(self) -> None:
        self.assertEqual(type(self.engine.pool).__name__, "QueuePool")

    def test_baseline_activity_quiescence_equilibrium(self) -> None:
        held: list = []

        def activity() -> None:
            for _ in range(3):
                held.append(self.engine.connect())
            snap = pool_truth_from_pool(self.engine.pool)
            self.assertGreaterEqual(int(snap["checked_out"] or 0), 3)
            for c in held:
                c.close()
            held.clear()

        result = run_four_phase(pool=self.engine.pool, activity=activity, settle_s=0.02)
        self.assertTrue(result["pass"], result)
        self.assertEqual(int(result["equilibrium"]["checked_out"] or 0), 0)
        self.assertEqual(result["timeout_delta"], 0)

    def test_timeout_then_return_to_idle(self) -> None:
        conns = [self.engine.connect() for _ in range(10)]
        timed_out = False
        try:
            self.engine.connect()
        except SATimeoutError:
            timed_out = True
        except Exception as exc:  # noqa: BLE001
            timed_out = "timeout" in str(exc).lower() or "QueuePool" in type(exc).__name__
        self.assertTrue(timed_out)
        for c in conns:
            c.close()
        snap = pool_truth_from_pool(self.engine.pool)
        self.assertEqual(int(snap["checked_out"] or 0), 0)

    def test_single_checkout_checkin_timeline(self) -> None:
        snap0 = pool_truth_from_pool(self.engine.pool)
        conn = self.engine.connect()
        conn.execute(text("SELECT 1"))
        snap1 = pool_truth_from_pool(self.engine.pool)
        self.assertEqual(int(snap1["checked_out"] or 0), int(snap0["checked_out"] or 0) + 1)
        conn.close()
        snap2 = pool_truth_from_pool(self.engine.pool)
        self.assertEqual(int(snap2["checked_out"] or 0), int(snap0["checked_out"] or 0))


if __name__ == "__main__":
    unittest.main()
