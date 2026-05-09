# -*- coding: utf-8 -*-
"""Tests for queue/worker readiness metadata (no recovery execution)."""
from __future__ import annotations

import unittest

from services.cartflow_queue_readiness import (
    BOUND_INLINE_SAFE,
    BOUND_RETRY_CANDIDATE,
    BOUND_SCHEDULED_JOB,
    BOUND_WORKER_CANDIDATE,
    SAFETY_IDEMPOTENT_SAFE,
    SAFETY_LIFECYCLE_SENSITIVE,
    SAFETY_PROVIDER_SIDE_EFFECT,
    SAFETY_REQUIRES_LOCKING,
    SAFETY_REQUIRES_ORDERING,
    SAFETY_RETRY_SENSITIVE,
    emit_queue_readiness_diagnostic,
    get_queue_candidate_registry,
    get_readiness_summary,
    get_runtime_async_boundaries,
    get_worker_safety_classifications,
)


class CartflowQueueReadinessTests(unittest.TestCase):
    _BOUND_VALUES = frozenset(
        {
            BOUND_INLINE_SAFE,
            BOUND_WORKER_CANDIDATE,
            BOUND_SCHEDULED_JOB,
            BOUND_RETRY_CANDIDATE,
        }
    )
    _SAFETY_VALUES = frozenset(
        {
            SAFETY_IDEMPOTENT_SAFE,
            SAFETY_REQUIRES_LOCKING,
            SAFETY_REQUIRES_ORDERING,
            SAFETY_PROVIDER_SIDE_EFFECT,
            SAFETY_RETRY_SENSITIVE,
            SAFETY_LIFECYCLE_SENSITIVE,
        }
    )

    def test_registry_shape_and_non_empty(self) -> None:
        reg = get_queue_candidate_registry()
        self.assertIsInstance(reg, list)
        self.assertGreaterEqual(len(reg), 8)
        required = (
            "id",
            "title",
            "async_boundary",
            "worker_safety",
            "current_runtime_owner",
            "summary",
        )
        ids: list[str] = []
        for row in reg:
            self.assertIsInstance(row, dict)
            for k in required:
                self.assertIn(k, row, msg=f"missing {k!r} in {row.get('id')}")
            bid = str(row["id"])
            self.assertTrue(bid)
            ids.append(bid)
            self.assertIn(row["async_boundary"], self._BOUND_VALUES)
            ws = row["worker_safety"]
            self.assertIsInstance(ws, list)
            for tag in ws:
                self.assertIn(tag, self._SAFETY_VALUES)
        self.assertEqual(len(ids), len(set(ids)), "duplicate registry ids")

    def test_async_boundary_visibility(self) -> None:
        by_bound = get_runtime_async_boundaries()
        self.assertEqual(set(by_bound.keys()), self._BOUND_VALUES)
        total = sum(len(v) for v in by_bound.values())
        self.assertEqual(total, len(get_queue_candidate_registry()))

    def test_classification_consistency(self) -> None:
        reg = get_queue_candidate_registry()
        classes = get_worker_safety_classifications()
        self.assertEqual(set(classes.keys()), self._SAFETY_VALUES)
        tagged = {op for vals in classes.values() for op in vals}
        for row in reg:
            op_id = str(row["id"])
            ws = row.get("worker_safety") or []
            if not ws:
                continue
            self.assertIn(op_id, tagged)

    def test_readiness_summary_payload(self) -> None:
        s = get_readiness_summary()
        self.assertIsInstance(s, dict)
        self.assertIn("registry_version", s)
        self.assertIn("registry_entry_count", s)
        self.assertIn("queue_ready_operations", s)
        self.assertIn("operations_requiring_locking", s)
        self.assertIn("operations_requiring_persistence", s)
        self.assertIn("operations_with_single_runtime_assumptions", s)
        for key in (
            "queue_ready_operations",
            "operations_requiring_locking",
            "operations_requiring_persistence",
            "operations_with_single_runtime_assumptions",
        ):
            self.assertIsInstance(s[key], list)
        self.assertEqual(s["registry_entry_count"], len(get_queue_candidate_registry()))

    def test_emit_diagnostic_no_raise(self) -> None:
        emit_queue_readiness_diagnostic(
            "unit_test_op",
            SAFETY_IDEMPOTENT_SAFE,
            note="test",
        )

    def test_module_import_does_not_import_main(self) -> None:
        import services.cartflow_queue_readiness as m

        self.assertIsNone(getattr(m, "main", None))


if __name__ == "__main__":
    unittest.main()
