# -*- coding: utf-8 -*-
"""Tests for completed-page row semantics (counter/page parity)."""
from __future__ import annotations

import unittest

from services.dashboard_completed_row_semantics_v1 import (
    is_archived_destination_dashboard_row,
    is_completed_dashboard_row,
)


class TestDashboardCompletedRowSemanticsV1(unittest.TestCase):
    def test_completed_lifecycle_state(self) -> None:
        self.assertTrue(
            is_completed_dashboard_row({"customer_lifecycle_state": "completed"})
        )

    def test_archived_visual_counts_as_completed(self) -> None:
        self.assertTrue(
            is_completed_dashboard_row(
                {"customer_lifecycle_is_archived_visual": True}
            )
        )

    def test_archived_state_is_destination(self) -> None:
        self.assertTrue(
            is_archived_destination_dashboard_row(
                {"customer_lifecycle_state": "archived"}
            )
        )

    def test_active_waiting_not_completed(self) -> None:
        self.assertFalse(
            is_completed_dashboard_row(
                {
                    "customer_lifecycle_state": "waiting_first_send",
                    "merchant_cart_bucket": "waiting",
                }
            )
        )

    def test_recovered_bucket_completed(self) -> None:
        self.assertTrue(
            is_completed_dashboard_row({"merchant_cart_bucket": "recovered"})
        )

    def test_purchased_label_completed(self) -> None:
        self.assertTrue(
            is_completed_dashboard_row(
                {"customer_lifecycle_label_ar": "تم الشراء — اختبار"}
            )
        )


if __name__ == "__main__":
    unittest.main()
