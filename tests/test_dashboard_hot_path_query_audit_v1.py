# -*- coding: utf-8 -*-
"""Dashboard hot-path SQL audit report structure."""

from __future__ import annotations

import unittest

from services.dashboard_hot_path_query_audit_v1 import (
    build_hot_path_query_report,
    hot_path_query_audit_begin,
    hot_path_query_audit_end,
    hot_path_query_audit_merge_reset,
    hot_path_query_audit_merge_sample,
    hot_path_query_audit_merged_report,
    hot_path_query_audit_record_sql,
    public_hot_path_query_report,
    sql_fingerprint,
)
from services.normal_carts_query_profiler import (
    normal_carts_profile_begin_for_simulation,
    normal_carts_profile_end,
    normal_carts_profile_span,
)


class DashboardHotPathQueryAuditTests(unittest.TestCase):
    def test_sql_fingerprint_normalizes_literals(self) -> None:
        a = sql_fingerprint("SELECT id FROM stores WHERE slug = 'demo' AND id = 42")
        b = sql_fingerprint("SELECT id FROM stores WHERE slug = 'other' AND id = 99")
        self.assertEqual(a, b)
        self.assertIn("stores", a)

    def test_record_sql_attributes_to_active_span(self) -> None:
        normal_carts_profile_begin_for_simulation()
        hot_path_query_audit_begin()
        try:
            with normal_carts_profile_span(
                "_normal_recovery_merchant_lightweight_alert_list_for_api"
            ):
                with normal_carts_profile_span("loop:batch_resolve_customer_phone_per_abandoned"):
                    hot_path_query_audit_record_sql(
                        "SELECT phone FROM message_log WHERE abandoned_cart_id = 1"
                    )
                    hot_path_query_audit_record_sql(
                        "SELECT phone FROM message_log WHERE abandoned_cart_id = 2"
                    )
                    hot_path_query_audit_record_sql(
                        "SELECT phone FROM message_log WHERE abandoned_cart_id = 3"
                    )
        finally:
            report = build_hot_path_query_report(total_queries=3, span_snap=[])
            hot_path_query_audit_end()
            normal_carts_profile_end()

        self.assertEqual(report["total_queries"], 3)
        n1 = report.get("n_plus_one_patterns") or []
        self.assertTrue(any("loop:batch_resolve" in str(p.get("span")) for p in n1))
        top = report.get("top_repeated_queries") or []
        self.assertGreaterEqual(len(top), 1)

    def test_build_report_includes_hot_path_function_blocks(self) -> None:
        span_snap = [
            {
                "fn": "_normal_recovery_merchant_lightweight_alert_list_for_api",
                "queries_inclusive": 658,
                "calls": 1,
            },
            {
                "fn": "_merchant_normal_dashboard_batch_reads",
                "queries_inclusive": 520,
                "calls": 1,
            },
            {
                "fn": "_merchant_normal_recovery_light_payload_merchant_batch",
                "queries_inclusive": 96,
                "calls": 24,
            },
            {
                "fn": "sql:batch_cart_recovery_logs_bulk",
                "queries_inclusive": 2,
                "calls": 1,
            },
        ]
        report = build_hot_path_query_report(total_queries=658, span_snap=span_snap)
        self.assertEqual(report["title"], "Where the 658 queries come from")
        roots = report.get("hot_path_functions") or {}
        self.assertIn("_normal_recovery_merchant_lightweight_alert_list_for_api", roots)
        self.assertEqual(
            roots["_normal_recovery_merchant_lightweight_alert_list_for_api"][
                "query_count_inclusive"
            ],
            658,
        )
        public = public_hot_path_query_report(report)
        self.assertNotIn("_fp_total", public)

    def test_merge_averages_across_dashboard_samples(self) -> None:
        hot_path_query_audit_merge_reset()
        sample = build_hot_path_query_report(
            total_queries=100,
            span_snap=[
                {
                    "fn": "_normal_recovery_merchant_lightweight_alert_list_for_api",
                    "queries_inclusive": 100,
                    "calls": 1,
                }
            ],
        )
        hot_path_query_audit_merge_sample(
            total_queries=100,
            span_snap=[
                {
                    "fn": "_normal_recovery_merchant_lightweight_alert_list_for_api",
                    "queries_inclusive": 100,
                    "calls": 1,
                }
            ],
            audit_report=sample,
        )
        hot_path_query_audit_merge_sample(
            total_queries=200,
            span_snap=[
                {
                    "fn": "_normal_recovery_merchant_lightweight_alert_list_for_api",
                    "queries_inclusive": 200,
                    "calls": 1,
                }
            ],
            audit_report=build_hot_path_query_report(
                total_queries=200,
                span_snap=[
                    {
                        "fn": "_normal_recovery_merchant_lightweight_alert_list_for_api",
                        "queries_inclusive": 200,
                        "calls": 1,
                    }
                ],
            ),
        )
        merged = hot_path_query_audit_merged_report()
        self.assertEqual(merged.get("total_queries_avg_per_check"), 150)
        self.assertIn("avg per dashboard check", merged.get("title") or "")


if __name__ == "__main__":
    unittest.main()
