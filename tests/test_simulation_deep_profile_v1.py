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

    def test_build_report_includes_hot_path_query_audit_key(self) -> None:
        acc = DeepProfileAccumulator()
        acc.record_dashboard(
            wall_ms=10.0,
            queries=0,
            perf_snap={},
            span_snap=[],
            hot_path_audit={
                "title": "Where the 0 queries come from",
                "total_queries": 0,
                "hot_path_functions": {},
            },
        )
        report = acc.build_report()
        self.assertIn("hot_path_query_audit", report)

    def test_build_report_includes_next_bottleneck_report(self) -> None:
        from services.dashboard_hot_path_query_audit_v1 import build_next_bottleneck_report

        nbr = build_next_bottleneck_report(
            dashboard_check_ms={
                "avg_queries_per_call": 610.0,
                "avg_wall_ms_per_call": 120.0,
            },
            hot_path_query_audit={
                "top_repeated_queries": [{"fingerprint": "select phone", "count": 220}],
                "n_plus_one_patterns": [
                    {
                        "span": "loop:batch_resolve_customer_phone_per_abandoned",
                        "query_count": 220,
                        "span_calls": 220,
                    }
                ],
                "duplicate_lookups": [],
                "queries_by_span": [],
            },
            top_slowest_functions=[
                {
                    "function": "_merchant_normal_dashboard_batch_reads",
                    "total_wall_ms": 80.0,
                    "total_queries": 400,
                }
            ],
            queued_followup_optimization={
                "n_plus_one_removed": True,
                "after_avg_per_dashboard_check": {
                    "queued_followup_per_group_db_queries": 0.0,
                },
            },
        )
        self.assertTrue(nbr.get("phone_resolution_is_next_bottleneck"))
        acc = DeepProfileAccumulator()
        acc.record_dashboard(
            wall_ms=120.0,
            queries=610,
            perf_snap={},
            span_snap=[],
            hot_path_audit={
                "top_repeated_queries": [],
                "n_plus_one_patterns": [
                    {
                        "span": "loop:batch_resolve_customer_phone_per_abandoned",
                        "query_count": 50,
                    }
                ],
                "duplicate_lookups": [],
                "bulk_load_opportunities": [
                    {
                        "location": "loop:batch_resolve_customer_phone_per_abandoned",
                        "callee_or_table": "_merchant_normal_batch_resolve_customer_phone_raw",
                        "observed_calls": 220,
                        "observed_query_count": 50,
                    }
                ],
                "hot_path_functions": {},
            },
            queued_followup_snap={
                "queued_followup_per_group_db_queries": 0,
                "queued_followup_bulk_prefetch_queries": 1,
            },
        )
        report = acc.build_report()
        self.assertIn("next_bottleneck_report", report)
        self.assertTrue(
            (report.get("next_bottleneck_report") or {}).get(
                "phone_resolution_is_next_bottleneck"
            )
        )

    def test_build_report_phone_resolution_removed_next_bottleneck(self) -> None:
        from services.dashboard_hot_path_query_audit_v1 import build_next_bottleneck_report

        nbr = build_next_bottleneck_report(
            dashboard_check_ms={
                "avg_queries_per_call": 45.0,
                "avg_wall_ms_per_call": 110.0,
            },
            hot_path_query_audit={
                "top_repeated_queries": [],
                "n_plus_one_patterns": [
                    {
                        "span": "sql:batch_cart_recovery_reason_by_session",
                        "query_count": 2,
                    }
                ],
                "duplicate_lookups": [],
                "queries_by_span": [],
            },
            top_slowest_functions=[],
            queued_followup_optimization={
                "n_plus_one_removed": True,
                "after_avg_per_dashboard_check": {
                    "queued_followup_per_group_db_queries": 0.0,
                },
            },
            phone_resolution_optimization={
                "per_row_db_eliminated": True,
                "after_avg_per_dashboard_check": {
                    "phone_resolution_fallback_count": 0.0,
                    "phone_resolution_db_queries": 0.0,
                },
            },
        )
        self.assertTrue(nbr.get("phone_resolution_n1_removed"))
        self.assertFalse(nbr.get("phone_resolution_is_next_bottleneck"))
        self.assertIn("cart_recovery_reason", str(nbr.get("next_bottleneck") or ""))


if __name__ == "__main__":
    unittest.main()
