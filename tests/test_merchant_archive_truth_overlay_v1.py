# -*- coding: utf-8 -*-
"""Merchant archive truth overlay — snapshot/hot-slice must not revive archived carts."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from services.merchant_cart_lifecycle_archive_v1 import (
    apply_merchant_archive_truth_to_normal_carts_payload,
)


class MerchantArchiveTruthOverlayV1Tests(unittest.TestCase):
    def test_moves_stale_active_snapshot_row_to_archived(self) -> None:
        payload = {
            "merchant_carts_page_rows": [
                {
                    "recovery_key": "demo:cart-a",
                    "customer_lifecycle_state": "waiting_customer_reply",
                    "customer_lifecycle_dashboard_action": "archive",
                    "merchant_cart_bucket": "sent",
                }
            ],
            "merchant_archived_carts_page_rows": [],
        }
        with patch(
            "services.merchant_cart_lifecycle_archive_v1.bulk_merchant_archived",
            return_value={"demo:cart-a": True},
        ), patch(
            "services.merchant_cart_lifecycle_archive_v1.bulk_merchant_reopened_keys",
            return_value=set(),
        ):
            out = apply_merchant_archive_truth_to_normal_carts_payload(payload)
        self.assertEqual(out["merchant_carts_page_rows"], [])
        self.assertEqual(len(out["merchant_archived_carts_page_rows"]), 1)
        row = out["merchant_archived_carts_page_rows"][0]
        self.assertTrue(row["customer_lifecycle_is_archived_visual"])
        self.assertEqual(row["customer_lifecycle_dashboard_action"], "reopen")
        self.assertTrue(out.get("merchant_archive_truth_overlay"))

    def test_restores_reopened_row_from_stale_archived_snapshot(self) -> None:
        payload = {
            "merchant_carts_page_rows": [],
            "merchant_archived_carts_page_rows": [
                {
                    "recovery_key": "demo:cart-b",
                    "customer_lifecycle_is_archived_visual": True,
                    "customer_lifecycle_state": "archived",
                    "customer_lifecycle_dashboard_action": "reopen",
                    "merchant_cart_bucket": "archived",
                }
            ],
        }
        with patch(
            "services.merchant_cart_lifecycle_archive_v1.bulk_merchant_archived",
            return_value={},
        ), patch(
            "services.merchant_cart_lifecycle_archive_v1.bulk_merchant_reopened_keys",
            return_value={"demo:cart-b"},
        ), patch(
            "services.customer_lifecycle_states_v1.lifecycle_payload_for_reopen",
            return_value={
                "customer_lifecycle_is_archived_visual": False,
                "customer_lifecycle_state": "waiting_customer_reply",
                "customer_lifecycle_dashboard_action": "archive",
                "customer_lifecycle_label_ar": "بانتظار رد العميل",
                "merchant_cart_bucket": "sent",
            },
        ):
            out = apply_merchant_archive_truth_to_normal_carts_payload(payload)
        self.assertEqual(len(out["merchant_carts_page_rows"]), 1)
        self.assertEqual(out["merchant_archived_carts_page_rows"], [])
        row = out["merchant_carts_page_rows"][0]
        self.assertFalse(row["customer_lifecycle_is_archived_visual"])
        self.assertEqual(row["customer_lifecycle_dashboard_action"], "archive")

    def test_leaves_terminal_archived_without_merchant_row(self) -> None:
        payload = {
            "merchant_carts_page_rows": [],
            "merchant_archived_carts_page_rows": [
                {
                    "recovery_key": "demo:cart-c",
                    "customer_lifecycle_is_archived_visual": True,
                    "customer_lifecycle_state": "archived",
                    "customer_lifecycle_dashboard_action": "reopen",
                    "merchant_cart_bucket": "archived",
                }
            ],
        }
        with patch(
            "services.merchant_cart_lifecycle_archive_v1.bulk_merchant_archived",
            return_value={},
        ), patch(
            "services.merchant_cart_lifecycle_archive_v1.bulk_merchant_reopened_keys",
            return_value=set(),
        ):
            out = apply_merchant_archive_truth_to_normal_carts_payload(payload)
        self.assertEqual(out["merchant_carts_page_rows"], [])
        self.assertEqual(len(out["merchant_archived_carts_page_rows"]), 1)


if __name__ == "__main__":
    unittest.main()
