# -*- coding: utf-8 -*-
"""Tests for Admin Operations production vs dev/test classification."""
from __future__ import annotations

import unittest

from services.admin_operations_production_truth_v1 import (
    classify_dev_test_bucket,
    classify_store_environment,
    count_dev_test_buckets,
    is_production_store,
)


class ProductionTruthClassificationTests(unittest.TestCase):
    def test_production_merchants(self) -> None:
        for slug in ("merchant-vip", "acme-shop", "real-store-01"):
            self.assertTrue(is_production_store(slug))
            self.assertEqual(classify_store_environment(slug), "production")

    def test_excluded_dev_test_patterns(self) -> None:
        excluded = (
            "demo",
            "demo2",
            "loadtest-store-013",
            "sandbox-shop",
            "test-merchant",
            "e2e-checkout",
            "staging-preview",
            "cartflow-default-recovery",
        )
        for slug in excluded:
            self.assertFalse(is_production_store(slug))
            self.assertEqual(classify_store_environment(slug), "demo_test")

    def test_dev_test_buckets(self) -> None:
        self.assertEqual(classify_dev_test_bucket("demo"), "demo")
        self.assertEqual(classify_dev_test_bucket("demo2"), "demo")
        self.assertEqual(classify_dev_test_bucket("loadtest-99"), "loadtest")
        self.assertEqual(classify_dev_test_bucket("sandbox-x"), "sandbox")
        self.assertEqual(classify_dev_test_bucket("test-only"), "other_test")

    def test_count_dev_test_buckets(self) -> None:
        rows = [
            {"store_slug": "demo"},
            {"store_slug": "demo2"},
            {"store_slug": "loadtest-1"},
            {"store_slug": "sandbox-a"},
            {"store_slug": "merchant-real"},
            {"store_slug": "demo"},  # duplicate slug ignored
        ]
        counts = count_dev_test_buckets(rows)
        self.assertEqual(counts["demo"], 2)
        self.assertEqual(counts["loadtest"], 1)
        self.assertEqual(counts["sandbox"], 1)
        self.assertEqual(counts["other_test"], 0)


if __name__ == "__main__":
    unittest.main()
