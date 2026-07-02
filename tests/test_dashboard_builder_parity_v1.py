# -*- coding: utf-8 -*-
"""Dashboard builder parity governance tests."""
from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

from extensions import db
from models import AbandonedCart, CartRecoveryLog, DashboardSnapshot, MerchantUser, Store
from services.dashboard_builder_parity_v1 import (
    _payload_truncation_drops_row,
    build_dashboard_builder_parity,
)
from services.dashboard_snapshot_v1 import (
    ENV_SNAPSHOT_MODE,
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_SUMMARY,
    fetch_latest_snapshot_row,
    list_store_slugs_for_snapshot_build,
    upsert_dashboard_snapshot,
)
from services.snapshot_truth_diagnostics_v1 import _aggregate_alias_results


def _enable_env() -> None:
    os.environ["ENV"] = "development"
    os.environ.setdefault("SECRET_KEY", "unit-test-builder-parity-v1")
    os.environ[ENV_SNAPSHOT_MODE] = "1"


class DashboardBuilderParityTests(unittest.TestCase):
    store_slug = "parity-demo-store"
    cart_id = "cf_cart_parity_demo_001"
    session_id = "cf-sess-parity-001"
    cart_key = f"{store_slug}:{cart_id}"

    def setUp(self) -> None:
        _enable_env()
        db.create_all()
        db.session.query(DashboardSnapshot).delete()
        db.session.query(CartRecoveryLog).delete()
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == self.store_slug).delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "parity-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

        user = MerchantUser(
            email="parity-demo@example.com",
            password_hash="x",
            merchant_name="Parity Demo",
        )
        db.session.add(user)
        db.session.flush()
        st = Store(
            zid_store_id=self.store_slug,
            merchant_user_id=int(user.id),
            is_active=True,
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        self.store_id = int(st.id)
        ac = AbandonedCart(
            store_id=self.store_id,
            zid_cart_id=self.cart_id,
            recovery_session_id=self.session_id,
            status="abandoned",
            cart_value=10000,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac)
        db.session.flush()
        self.abandoned_cart_id = int(ac.id)
        db.session.add(
            CartRecoveryLog(
                store_slug=self.store_slug,
                session_id=self.session_id,
                cart_id=self.cart_id,
                recovery_key=self.cart_key,
                status="sent_real",
            )
        )
        db.session.commit()

    def _row_payload(self) -> dict[str, Any]:
        return {
            "recovery_key": self.cart_key,
            "zid_cart_id": self.cart_id,
            "merchant_cart_bucket": "sent",
            "merchant_cart_visible_tabs": ["all", "sent"],
        }

    @patch("services.dashboard_builder_parity_v1._build_fresh_normal_carts_payload")
    @patch("services.merchant_cart_presence_trace_v1.trace_merchant_cart_presence")
    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_live_and_snapshot_builder_rows_match(
        self,
        mock_inclusion: unittest.mock.Mock,
        mock_trace: unittest.mock.Mock,
        mock_build: unittest.mock.Mock,
    ) -> None:
        payload = {
            "merchant_carts_page_rows": [self._row_payload()],
            "merchant_archived_carts_page_rows": [],
            "merchant_cart_filter_counts": {"sent": 1},
            "candidate_rows": 1,
            "visible_rows": 1,
        }
        mock_build.return_value = payload
        mock_trace.return_value = {
            "exclusion_stage": "included",
            "returned_in_api": True,
            "log_id": 1,
        }
        mock_inclusion.return_value = {
            "dashboard_visible": True,
            "dashboard_exclusion_reason": "included",
        }

        body = build_dashboard_builder_parity(
            store_slug=self.store_slug,
            cart_id=self.cart_id,
        )
        self.assertTrue(body["live_builder_truth"]["live_builder_row_present"])
        self.assertTrue(body["snapshot_builder_truth"]["snapshot_builder_row_present"])
        self.assertTrue(body["snapshot_builder_truth"]["builders_match"])

    @patch("services.dashboard_builder_parity_v1._build_fresh_normal_carts_payload")
    @patch("services.merchant_cart_presence_trace_v1.trace_merchant_cart_presence")
    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_persisted_snapshot_includes_builder_row(
        self,
        mock_inclusion: unittest.mock.Mock,
        mock_trace: unittest.mock.Mock,
        mock_build: unittest.mock.Mock,
    ) -> None:
        payload = {
            "merchant_carts_page_rows": [self._row_payload()],
            "merchant_archived_carts_page_rows": [],
            "merchant_cart_filter_counts": {"sent": 1},
        }
        mock_build.return_value = payload
        mock_trace.return_value = {
            "exclusion_stage": "included",
            "returned_in_api": True,
            "log_id": 1,
        }
        mock_inclusion.return_value = {
            "dashboard_visible": True,
            "dashboard_exclusion_reason": "included",
        }
        upsert_dashboard_snapshot(
            store_id=self.store_id,
            store_slug=self.store_slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload=payload,
        )

        body = build_dashboard_builder_parity(
            store_slug=self.store_slug,
            cart_id=self.cart_id,
        )
        self.assertTrue(body["snapshot_payload_truth"]["snapshot_row_present"])
        self.assertEqual(body["drop_stage"], "included")
        self.assertEqual(body["parity_status"], "pass")

    @patch("services.dashboard_builder_parity_v1._build_fresh_normal_carts_payload")
    @patch("services.merchant_cart_presence_trace_v1.trace_merchant_cart_presence")
    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_stale_snapshot_reports_snapshot_read_drop_stage(
        self,
        mock_inclusion: unittest.mock.Mock,
        mock_trace: unittest.mock.Mock,
        mock_build: unittest.mock.Mock,
    ) -> None:
        payload = {
            "merchant_carts_page_rows": [self._row_payload()],
            "merchant_archived_carts_page_rows": [],
        }
        mock_build.return_value = payload
        mock_trace.return_value = {
            "exclusion_stage": "included",
            "returned_in_api": True,
            "log_id": 1,
        }
        mock_inclusion.return_value = {
            "dashboard_visible": True,
            "dashboard_exclusion_reason": "included",
        }
        old = datetime.now(timezone.utc) - timedelta(minutes=10)
        row = DashboardSnapshot(
            store_slug=self.store_slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload_json=json.dumps({"merchant_carts_page_rows": [], "merchant_archived_carts_page_rows": []}),
            generated_at=old,
            expires_at=old + timedelta(seconds=30),
            version=1,
            status="active",
        )
        db.session.add(row)
        db.session.commit()

        body = build_dashboard_builder_parity(
            store_slug=self.store_slug,
            cart_id=self.cart_id,
        )
        self.assertEqual(body["drop_stage"], "snapshot_read")
        self.assertIn(body["reason"], ("snapshot_stale", "row_missing"))
        self.assertEqual(body["parity_status"], "fail")

    def test_alias_aggregate_prefers_cart_key_over_session_no_sent_log(self) -> None:
        cart_alias = {
            "recovery_key": self.cart_key,
            "key_type": "cart",
            "sent_log_found": True,
            "returned_in_api": True,
            "dashboard_visible": True,
            "exclusion_reason": "included",
            "exclusion_stage": "included",
        }
        session_alias = {
            "recovery_key": f"{self.store_slug}:{self.session_id}",
            "key_type": "session",
            "sent_log_found": False,
            "returned_in_api": False,
            "dashboard_visible": False,
            "exclusion_reason": "no_sent_log",
            "exclusion_stage": "no_sent_log",
        }
        included, matched_key, _matched_by, live_exclusion = _aggregate_alias_results(
            [cart_alias, session_alias]
        )
        self.assertTrue(included)
        self.assertEqual(matched_key, self.cart_key)
        self.assertNotEqual(live_exclusion, "no_sent_log")

    def test_payload_truncation_detection(self) -> None:
        big_row = dict(self._row_payload())
        big_row["debug_blob"] = "x" * 70000
        payload = {
            "merchant_carts_page_rows": [big_row],
            "merchant_archived_carts_page_rows": [],
        }
        dropped = _payload_truncation_drops_row(
            payload,
            recovery_keys={self.cart_key},
            cart_id=self.cart_id,
        )
        self.assertTrue(dropped)

    def test_stale_normal_carts_prioritized_for_snapshot_build(self) -> None:
        now = datetime.now(timezone.utc)
        fresh_summary = DashboardSnapshot(
            store_slug=self.store_slug,
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload_json='{"ok": true}',
            generated_at=now,
            expires_at=now + timedelta(seconds=120),
            version=1,
            status="active",
        )
        stale_nc = DashboardSnapshot(
            store_slug=self.store_slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload_json='{"merchant_carts_page_rows": []}',
            generated_at=now - timedelta(minutes=5),
            expires_at=now - timedelta(minutes=4),
            version=1,
            status="active",
        )
        db.session.add_all([fresh_summary, stale_nc])
        db.session.commit()
        slugs = [s for _sid, s in list_store_slugs_for_snapshot_build(limit=5)]
        self.assertIn(self.store_slug, slugs)


if __name__ == "__main__":
    unittest.main()
