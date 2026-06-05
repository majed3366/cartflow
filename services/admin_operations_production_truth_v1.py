# -*- coding: utf-8 -*-
"""
Admin Operations — production vs development/test classification (presentation-only).

Single operational truth for merchant-facing counts. Does not change detection.
"""
from __future__ import annotations

from typing import Any

# Substrings / slugs excluded from production operational metrics.
_DEMO_TEST_TOKENS = (
    "sim-store",
    "loadtest",
    "cartflow-default",
    "cartflow-default-recovery",
    "test",
    "e2e",
    "demo",
    "staging",
    "sandbox",
)


def is_production_store(slug: str) -> bool:
    """True when store counts toward production operational metrics."""
    return classify_store_environment(slug) == "production"


def classify_store_environment(slug: str) -> str:
    """production | demo_test"""
    s = (slug or "").strip().lower()
    if not s:
        return "production"
    for tok in _DEMO_TEST_TOKENS:
        if tok in s:
            return "demo_test"
    return "production"


def classify_dev_test_bucket(slug: str) -> str:
    """demo | loadtest | sandbox | other_test — presentation-only."""
    s = (slug or "").strip().lower()
    if "sandbox" in s:
        return "sandbox"
    if "loadtest" in s:
        return "loadtest"
    if s in ("demo", "demo2") or "demo" in s:
        return "demo"
    return "other_test"


def count_dev_test_buckets(store_rows: list[dict[str, Any]]) -> dict[str, int]:
    """Count scanned stores by dev/test bucket."""
    counts = {"demo": 0, "loadtest": 0, "sandbox": 0, "other_test": 0}
    seen: set[str] = set()
    for row in store_rows or []:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("store_slug") or "").strip()
        if not slug or slug in seen:
            continue
        if is_production_store(slug):
            continue
        seen.add(slug)
        bucket = classify_dev_test_bucket(slug)
        counts[bucket] = counts.get(bucket, 0) + 1
    return counts


__all__ = [
    "classify_dev_test_bucket",
    "classify_store_environment",
    "count_dev_test_buckets",
    "is_production_store",
]
