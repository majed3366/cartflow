# -*- coding: utf-8 -*-
"""BASELINE → ACTIVITY → QUIESCENCE → EQUILIBRIUM measurements (INV-DB-10)."""
from __future__ import annotations

import time
from typing import Any, Callable

from services.db_lifecycle_v1.pool_truth import pool_truth_from_pool, pool_truth_snapshot


def sample(*, pool: Any = None) -> dict[str, Any]:
    snap = pool_truth_from_pool(pool) if pool is not None else pool_truth_snapshot()
    snap["sampled_at"] = time.time()
    return snap


def run_four_phase(
    *,
    pool: Any,
    activity: Callable[[], None],
    settle_s: float = 0.05,
) -> dict[str, Any]:
    baseline = sample(pool=pool)
    activity()
    peak = sample(pool=pool)
    time.sleep(max(0.0, float(settle_s)))
    quiescence = sample(pool=pool)
    equilibrium = sample(pool=pool)
    base_co = int(baseline.get("checked_out") or 0)
    eq_co = int(equilibrium.get("checked_out") or 0)
    peak_co = int(peak.get("checked_out") or 0)
    timeouts = int(equilibrium.get("timeout_count") or 0) - int(baseline.get("timeout_count") or 0)
    passed = eq_co <= base_co and timeouts == 0
    return {
        "baseline": baseline,
        "peak": peak,
        "quiescence": quiescence,
        "equilibrium": equilibrium,
        "peak_checked_out": peak_co,
        "post_activity_checked_out": eq_co,
        "timeout_delta": timeouts,
        "returned_to_baseline": passed,
        "pass": passed,
    }
