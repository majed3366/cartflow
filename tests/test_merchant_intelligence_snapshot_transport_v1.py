# -*- coding: utf-8 -*-
"""Merchant Intelligence snapshot transport contract — normal-carts payload certification."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from services.dashboard_snapshot_normal_carts_parity_v1 import (
    build_canonical_normal_carts_payload,
)
from services.dashboard_snapshot_normal_carts_slim_v1 import (
    slim_normal_carts_payload_for_snapshot,
)
from services.dashboard_snapshot_read_v1 import build_normal_carts_from_snapshot
from services.merchant_decision_layer_v1 import attach_merchant_decisions_v1
from services.merchant_intelligence_v1 import (
    AUTHORITY,
    GROUP_NEEDS_MERCHANT,
    INTELLIGENCE_VERSION,
    attach_merchant_intelligence_v1,
    ensure_normal_carts_merchant_intelligence_store_v1,
)
from services.merchant_proof_surface_v1 import attach_merchant_proof_surface_v1
from services.normal_carts_dashboard_batch_v1 import NormalCartsDashboardPerfMeta


def _needs_merchant_row(*, rk: str = "store:cart:1") -> dict:
    row = {
        "recovery_key": rk,
        "store_slug": "demo",
        "has_phone": True,
        "merchant_cart_primary_bucket": "sent",
        "merchant_cart_bucket": "sent",
        "customer_lifecycle_state": "waiting_customer_reply",
        "customer_lifecycle_merchant_needed_ar": "نعم",
        "merchant_intervention_executable": True,
        "cart_value": 1240.0,
        "reason_tag": "",
    }
    attach_merchant_proof_surface_v1(
        row,
        recovery_key=rk,
        customer_lifecycle_state=str(row.get("customer_lifecycle_state") or ""),
        customer_lifecycle_what_happened_ar="تحتاج تدخل",
        log_statuses=[],
    )
    row["merchant_decision_key"] = "contact_customer"
    attach_merchant_decisions_v1(row)
    attach_merchant_intelligence_v1(row)
    return row


def _assert_store_mi_contract(store_mi: dict) -> None:
    self_required = (
        "version",
        "authority",
        "groups",
        "recommendations",
        "memory",
        "priorities",
        "cart_assignments",
        "observability",
    )
    for key in self_required:
        assert key in store_mi, f"missing {key}"
    assert store_mi["version"] == INTELLIGENCE_VERSION
    assert store_mi["authority"] == AUTHORITY
    assert isinstance(store_mi["groups"], list)
    assert isinstance(store_mi["recommendations"], list)
    assert isinstance(store_mi["memory"], list)
    assert isinstance(store_mi["priorities"], list)
    assert isinstance(store_mi["cart_assignments"], list)
    assert isinstance(store_mi["observability"], dict)


class MerchantIntelligenceSnapshotTransportV1Tests(unittest.TestCase):
    def test_ensure_empty_rows_returns_valid_store_object(self) -> None:
        body: dict = {"merchant_carts_page_rows": []}
        ensure_normal_carts_merchant_intelligence_store_v1(body)
        store_mi = body.get("merchant_intelligence_store_v1")
        self.assertIsInstance(store_mi, dict)
        assert store_mi is not None
        _assert_store_mi_contract(store_mi)
        self.assertEqual(store_mi["groups"], [])

    def test_rows_with_intelligence_group_key_produce_store_groups(self) -> None:
        row = _needs_merchant_row()
        body = {"merchant_carts_page_rows": [row]}
        ensure_normal_carts_merchant_intelligence_store_v1(body)
        store_mi = body["merchant_intelligence_store_v1"]
        group_ids = {g.get("group_id") for g in store_mi.get("groups") or []}
        self.assertIn(GROUP_NEEDS_MERCHANT, group_ids)
        self.assertEqual(row.get("intelligence_group_key"), GROUP_NEEDS_MERCHANT)

    def test_slim_snapshot_preserves_merchant_intelligence_store_v1(self) -> None:
        row = _needs_merchant_row(rk="slim:cart:1")
        body = {"merchant_carts_page_rows": [row], "merchant_archived_carts_page_rows": []}
        ensure_normal_carts_merchant_intelligence_store_v1(body)
        slim = slim_normal_carts_payload_for_snapshot(body)
        self.assertIn("merchant_intelligence_store_v1", slim)
        store_mi = slim["merchant_intelligence_store_v1"]
        _assert_store_mi_contract(store_mi)
        group_ids = {g.get("group_id") for g in store_mi.get("groups") or []}
        self.assertIn(GROUP_NEEDS_MERCHANT, group_ids)

    @patch("services.dashboard_snapshot_read_v1.enforce_route_budget", side_effect=lambda b, **_: b)
    @patch("services.dashboard_snapshot_read_v1.apply_normal_carts_snapshot_client_guards", side_effect=lambda b: b)
    @patch("services.dashboard_snapshot_read_v1.read_dashboard_snapshot_payload")
    def test_snapshot_read_includes_merchant_intelligence_store_v1(
        self,
        mock_read: unittest.mock.Mock,
        _mock_guards: unittest.mock.Mock,
        _mock_budget: unittest.mock.Mock,
    ) -> None:
        row = _needs_merchant_row(rk="snap-read:cart:1")
        mock_read.return_value = {
            "snapshot_mode": True,
            "merchant_carts_page_rows": [row],
            "merchant_archived_carts_page_rows": [],
            "merchant_cart_filter_counts": {"all": 1},
        }
        out = build_normal_carts_from_snapshot(store_slug="transport-read-store")
        self.assertIn("merchant_intelligence_store_v1", out)
        store_mi = out["merchant_intelligence_store_v1"]
        _assert_store_mi_contract(store_mi)
        group_ids = {g.get("group_id") for g in store_mi.get("groups") or []}
        self.assertIn(GROUP_NEEDS_MERCHANT, group_ids)

    @patch("services.dashboard_snapshot_read_v1.enforce_route_budget", side_effect=lambda b, **_: b)
    @patch("services.dashboard_snapshot_read_v1.apply_normal_carts_snapshot_client_guards", side_effect=lambda b: b)
    @patch("services.dashboard_snapshot_read_v1.read_dashboard_snapshot_payload")
    def test_snapshot_read_empty_rows_still_includes_store_object(
        self,
        mock_read: unittest.mock.Mock,
        _mock_guards: unittest.mock.Mock,
        _mock_budget: unittest.mock.Mock,
    ) -> None:
        mock_read.return_value = {
            "snapshot_mode": True,
            "merchant_carts_page_rows": [],
            "merchant_archived_carts_page_rows": [],
            "merchant_cart_filter_counts": {},
        }
        out = build_normal_carts_from_snapshot(store_slug="transport-empty-store")
        store_mi = out.get("merchant_intelligence_store_v1")
        self.assertIsInstance(store_mi, dict)
        assert store_mi is not None
        _assert_store_mi_contract(store_mi)
        self.assertEqual(store_mi["groups"], [])

    @patch(
        "services.normal_carts_dashboard_batch_v1.build_normal_carts_dashboard_api_payload"
    )
    def test_canonical_payload_includes_merchant_intelligence_store_v1(
        self,
        mock_build: unittest.mock.Mock,
    ) -> None:
        row = _needs_merchant_row(rk="canonical:cart:1")
        mock_build.return_value = (
            {
                "merchant_carts_page_rows": [row],
                "merchant_archived_carts_page_rows": [],
                "merchant_cart_filter_counts": {"all": 1},
            },
            {},
            NormalCartsDashboardPerfMeta(rows_built=1, partial=False, degraded=False),
        )
        body, _prof, _perf = build_canonical_normal_carts_payload(MagicMock())
        self.assertIn("merchant_intelligence_store_v1", body)
        store_mi = body["merchant_intelligence_store_v1"]
        _assert_store_mi_contract(store_mi)
        group_ids = {g.get("group_id") for g in store_mi.get("groups") or []}
        self.assertIn(GROUP_NEEDS_MERCHANT, group_ids)


if __name__ == "__main__":
    unittest.main()
