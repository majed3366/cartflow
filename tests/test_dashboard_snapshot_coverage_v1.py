# -*- coding: utf-8 -*-
"""Dashboard Snapshot Coverage V1 — Living Store demo eligibility."""
from __future__ import annotations

import unittest

from services.dashboard_snapshot_v1 import is_snapshot_build_eligible_store


class DashboardSnapshotCoverageV1Tests(unittest.TestCase):
    def test_unowned_demo_still_excluded(self) -> None:
        ok, reason = is_snapshot_build_eligible_store(
            zid_store_id="demo",
            merchant_user_id=None,
            is_active=True,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_merchant_user")

    def test_merchant_bound_demo_is_eligible(self) -> None:
        """Living Store review binds merchant_user_id → must receive snapshots."""
        ok, reason = is_snapshot_build_eligible_store(
            zid_store_id="demo",
            merchant_user_id=429,
            is_active=True,
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "active_merchant")

    def test_inactive_demo_excluded(self) -> None:
        ok, reason = is_snapshot_build_eligible_store(
            zid_store_id="demo",
            merchant_user_id=429,
            is_active=False,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "inactive")

    def test_audit_prefix_still_excluded(self) -> None:
        ok, reason = is_snapshot_build_eligible_store(
            zid_store_id="stuckaudit-abcdef",
            merchant_user_id=1,
            is_active=True,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "test_audit_prefix")


if __name__ == "__main__":
    unittest.main()
