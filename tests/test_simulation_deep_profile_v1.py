# -*- coding: utf-8 -*-
"""Simulation deep profile report structure."""

from __future__ import annotations

import unittest

from services.simulation_deep_profile_v1 import DeepProfileAccumulator


class SimulationDeepProfileTests(unittest.TestCase):
    def test_build_report_includes_breakdown_and_top_functions(self) -> None:
        acc = DeepProfileAccumulator()
        acc.record_dashboard(
            wall_ms=120.0,
            queries=45,
            perf_snap={
                "lifecycle_attach_ms": 30.0,
                "row_lifecycle_ms_sum": 10.0,
                "stage_ms": {"batch_reads": 40.0, "abandoned_candidates": 20.0},
            },
            span_snap=[
                {
                    "fn": "sql:batch_recovery_logs_bulk",
                    "wall_ms_exclusive": 25.0,
                    "queries_exclusive": 12,
                },
                {
                    "fn": "loop:batch_build_per_abandoned_log_projection",
                    "wall_ms_exclusive": 15.0,
                    "queries_exclusive": 5,
                },
            ],
        )
        acc.record_purchase(
            total_ms=80.0,
            ingest_ms=50.0,
            record_truth_ms=20.0,
            lifecycle_ms=15.0,
            reconcile_ms=15.0,
            dashboard_ms=30.0,
            ingest_queries=8,
            reconcile_queries=3,
            dashboard_queries=20,
            span_snap=[],
        )
        report = acc.build_report()
        self.assertEqual(report["dashboard_check_ms"]["calls"], 1)
        self.assertIn("db_ms", report["dashboard_check_ms"]["breakdown_ms"])
        self.assertIn("lifecycle_ms", report["dashboard_check_ms"]["breakdown_ms"])
        self.assertIn("grouping_ms", report["dashboard_check_ms"]["breakdown_ms"])
        self.assertIn("merge_ms", report["dashboard_check_ms"]["breakdown_ms"])
        self.assertEqual(report["purchase_check_ms"]["calls"], 1)
        self.assertIn(
            "reconcile_active_carts_ms",
            report["purchase_check_ms"]["breakdown_ms"],
        )
        top = report.get("top_slowest_functions") or []
        self.assertGreaterEqual(len(top), 1)
        self.assertLessEqual(len(top), 5)
        self.assertIn("function", top[0])
        self.assertIn("total_wall_ms", top[0])


if __name__ == "__main__":
    unittest.main()
