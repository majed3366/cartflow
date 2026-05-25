# -*- coding: utf-8 -*-
"""Cart visibility debug payload shape."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.merchant_cart_visibility_debug_v1 import (
    build_merchant_cart_visibility_debug_payload,
    log_cf_abandoned_cart_persist,
)


class TestMerchantCartVisibilityDebug(unittest.TestCase):
    def test_log_cf_abandoned_cart_persist_does_not_raise(self) -> None:
        row = SimpleNamespace(
            zid_cart_id="cf_cart_test",
            recovery_session_id="sess_1",
            status="abandoned",
            raw_payload='{"reason_tag":"price"}',
        )
        with patch("services.merchant_cart_visibility_debug_v1.log") as mock_log:
            log_cf_abandoned_cart_persist(
                row, store_slug="demo", created=True, event_path="cart_state_sync"
            )
            self.assertTrue(mock_log.info.called)

    @patch("extensions.db")
    def test_build_payload_shape(self, mock_db: MagicMock) -> None:
        mock_db.session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.session.query.return_value.filter.return_value.all.return_value = []
        out = build_merchant_cart_visibility_debug_payload(
            dash_store=SimpleNamespace(id=1, zid_store_id="shop1", vip_cart_threshold=500),
            auth_store_slug="shop1",
            scope_filter=None,
            normal_carts_row_count=0,
        )
        self.assertIn("latest_carts", out)
        self.assertIn("dashboard_store", out)
        self.assertEqual(out["normal_carts_query"]["status_filter"], "abandoned")
        self.assertEqual(out["dashboard_store"]["resolved_store_slug"], "shop1")


if __name__ == "__main__":
    unittest.main()
