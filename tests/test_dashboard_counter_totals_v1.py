# -*- coding: utf-8 -*-
"""Canonical store-level dashboard counter totals."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from services.dashboard_counter_totals_v1 import (
    COUNTER_PARITY_VERSION,
    COUNTER_QUERY_SCOPE,
    MerchantCartCounterTotals,
    apply_counter_health_from_snapshot_meta,
    build_merchant_cart_counter_totals,
    visible_page_counts_from_rows,
)


class TestMerchantCartCounterTotals(unittest.TestCase):
    def test_to_legacy_filter_counts_maps_store_totals(self) -> None:
        totals = MerchantCartCounterTotals(
            active_total=10,
            waiting_total=3,
            sent_total=4,
            engaged_total=2,
            completed_total=5,
            archived_total=6,
            no_phone_total=1,
        )
        legacy = totals.to_legacy_filter_counts()
        self.assertEqual(legacy["all"], 10)
        self.assertEqual(legacy["waiting"], 3)
        self.assertEqual(legacy["sent"], 4)
        self.assertEqual(legacy["attention"], 2)
        self.assertEqual(legacy["recovered"], 5)
        self.assertEqual(legacy["nophone"], 1)

    def test_payload_includes_health_metadata(self) -> None:
        from services.dashboard_counter_totals_v1 import MerchantCartCounterPayload

        payload = MerchantCartCounterPayload(
            counts=MerchantCartCounterTotals(active_total=1),
            generated_at="2026-07-02T00:00:00+00:00",
        )
        api = payload.to_api_payload()
        health = api["merchant_counter_health"]
        self.assertEqual(health["counter_query_scope"], COUNTER_QUERY_SCOPE)
        self.assertEqual(health["counter_parity_version"], COUNTER_PARITY_VERSION)
        self.assertIn("merchant_store_cart_counts", api)
        self.assertEqual(api["merchant_store_cart_counts"]["active_total"], 1)

    def test_apply_counter_health_from_snapshot_meta_marks_stale(self) -> None:
        body = {
            "merchant_counter_health": {
                "counter_generated_at": "2026-07-02T00:00:00+00:00",
            }
        }
        out = apply_counter_health_from_snapshot_meta(
            body,
            snapshot_meta={"stale": True},
        )
        self.assertTrue(out["merchant_counter_health"]["counter_snapshot_stale"])
        self.assertEqual(out["merchant_counter_source"], "snapshot")

    def test_visible_page_counts_differs_from_store_slice(self) -> None:
        rows = [
            {
                "customer_lifecycle_state": "waiting_first_send",
                "merchant_cart_visible_tabs": ["all", "waiting"],
            }
            for _ in range(50)
        ]
        page = visible_page_counts_from_rows(rows)
        self.assertEqual(page["all"], 50)
        self.assertEqual(page["waiting"], 50)

    @patch("services.dashboard_counter_totals_v1.db")
    def test_build_returns_zeros_without_store(self, _mock_db: MagicMock) -> None:
        with patch(
            "main._dashboard_recovery_store_row",
            return_value=None,
        ):
            payload = build_merchant_cart_counter_totals(None)
        self.assertEqual(payload.counts.active_total, 0)
        self.assertEqual(payload.counter_query_scope, COUNTER_QUERY_SCOPE)


class TestNormalCartsPayloadUsesCanonicalTotals(unittest.TestCase):
    @patch(
        "services.normal_carts_dashboard_batch_v1.build_normal_carts_unified_rows",
        return_value=(
            [{"customer_lifecycle_state": "waiting_first_send"}] * 50,
            [],
            {"logs_loaded": 0, "reasons_loaded": 0, "phones_loaded": 0},
            MagicMock(),
        ),
    )
    @patch("services.dashboard_counter_totals_v1.build_merchant_cart_counter_totals")
    @patch("main._merchant_dashboard_refresh_state_payload", return_value={})
    @patch("main._merchant_dashboard_db_ready")
    def test_api_payload_uses_store_counts_not_page_window(
        self,
        _db_ready: MagicMock,
        _refresh: MagicMock,
        mock_totals: MagicMock,
        _rows: MagicMock,
    ) -> None:
        from services.dashboard_counter_totals_v1 import (
            MerchantCartCounterPayload,
            MerchantCartCounterTotals,
        )
        from services.normal_carts_dashboard_batch_v1 import (
            build_normal_carts_dashboard_api_payload,
        )

        mock_totals.return_value = MerchantCartCounterPayload(
            counts=MerchantCartCounterTotals(
                active_total=120,
                waiting_total=40,
                sent_total=30,
                engaged_total=20,
                completed_total=15,
                archived_total=8,
                no_phone_total=2,
            )
        )
        body, _prof, _perf = build_normal_carts_dashboard_api_payload(MagicMock())
        self.assertEqual(body["merchant_store_cart_counts"]["active_total"], 120)
        self.assertEqual(body["merchant_cart_filter_counts"]["all"], 120)
        self.assertEqual(body["merchant_nav_badge_abandoned"], 40)
        self.assertEqual(body["merchant_visible_page_counts"]["all"], 50)


if __name__ == "__main__":
    unittest.main()
