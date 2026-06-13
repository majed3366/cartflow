# -*- coding: utf-8 -*-
"""DB pool health visibility v1 tests."""
from __future__ import annotations

import unittest

from services.db_pool_diagnostics import build_db_pool_health_snapshot
from services.production_deployment_gate_v1 import evaluate_pool_health_gate


class DbPoolHealthVisibilityTests(unittest.TestCase):
    def test_snapshot_has_core_fields(self) -> None:
        snap = build_db_pool_health_snapshot()
        for key in (
            "available",
            "size",
            "checked_out",
            "overflow",
            "timeout_count",
            "exhausted",
        ):
            self.assertIn(key, snap)

    def test_gate_fails_when_exhausted(self) -> None:
        out = evaluate_pool_health_gate(
            {
                "exhausted": True,
                "timeout_count": 2,
                "checked_out": 30,
                "max_connections": 30,
            }
        )
        self.assertFalse(out["passed"])
        self.assertTrue(any("exhausted" in e for e in out["errors"]))

    def test_gate_passes_when_healthy(self) -> None:
        out = evaluate_pool_health_gate(
            {
                "exhausted": False,
                "timeout_count": 0,
                "checked_out": 2,
                "max_connections": 30,
            }
        )
        self.assertTrue(out["passed"])


if __name__ == "__main__":
    unittest.main()
