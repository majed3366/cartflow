# -*- coding: utf-8 -*-
"""Dashboard hot slice Phase 1 tests."""
from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import AbandonedCart, DashboardSnapshot, MerchantUser, Store
from services.dashboard_hot_slice_v1 import (
    HOT_SLICE_HOURS,
    HOT_SLICE_MAX_ROWS,
    apply_hot_slice_to_normal_carts_payload,
    hot_slice_last_seen_cutoff,
    merge_hot_slice_active_rows,
)
from services.dashboard_snapshot_v1 import ENV_SNAPSHOT_MODE, SNAPSHOT_TYPE_NORMAL_CARTS


def _enable_snapshot_mode() -> None:
    os.environ["ENV"] = "development"
    os.environ[ENV_SNAPSHOT_MODE] = "1"
    os.environ.setdefault("SECRET_KEY", "unit-test-hot-slice-v1")


class DashboardHotSliceMergeTests(unittest.TestCase):
    def test_merge_hot_wins_and_dedupes(self) -> None:
        snap = [
            {"recovery_key": "store:a", "merchant_cart_bucket": "waiting", "zid_cart_id": "a"},
            {"recovery_key": "store:b", "merchant_cart_bucket": "waiting", "zid_cart_id": "b"},
        ]
        hot = [
            {"recovery_key": "store:a", "merchant_cart_bucket": "sent", "zid_cart_id": "a"},
            {"recovery_key": "store:c", "merchant_cart_bucket": "waiting", "zid_cart_id": "c"},
        ]
        merged = merge_hot_slice_active_rows(snap, hot)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[0]["recovery_key"], "store:a")
        self.assertEqual(merged[0]["merchant_cart_bucket"], "sent")
        self.assertEqual(merged[1]["recovery_key"], "store:c")
        self.assertEqual(merged[2]["recovery_key"], "store:b")

    def test_merge_respects_page_limit(self) -> None:
        snap = [{"recovery_key": f"store:r{i}"} for i in range(10)]
        hot = [{"recovery_key": f"store:h{i}"} for i in range(10)]
        merged = merge_hot_slice_active_rows(snap, hot, page_limit=5)
        self.assertEqual(len(merged), 5)

    def test_hot_cutoff_is_36_hours(self) -> None:
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
        cutoff = hot_slice_last_seen_cutoff(now=now)
        self.assertEqual(HOT_SLICE_HOURS, 36)
        self.assertEqual(cutoff, now - timedelta(hours=36))


class DashboardHotSliceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        _enable_snapshot_mode()
        db.create_all()
        db.session.query(DashboardSnapshot).delete()
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == "demo").delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "hot-slice-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

        user = MerchantUser(
            email="hot-slice-demo@example.com",
            password_hash="x",
            merchant_name="Hot Slice Demo",
        )
        db.session.add(user)
        db.session.flush()
        st = Store(
            zid_store_id="demo",
            merchant_user_id=int(user.id),
            is_active=True,
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        self.store = st
        self.cart_id = "cf_cart_hot_slice_new_001"
        self.recovery_key = f"demo:{self.cart_id}"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        db.session.query(DashboardSnapshot).delete()
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == "demo").delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "hot-slice-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

    def _seed_stale_snapshot_without_new_cart(self) -> None:
        payload = {
            "merchant_carts_page_rows": [
                {
                    "recovery_key": "demo:cf_cart_old_001",
                    "zid_cart_id": "cf_cart_old_001",
                    "merchant_cart_bucket": "waiting",
                }
            ],
            "merchant_archived_carts_page_rows": [],
            "merchant_store_cart_counts": {
                "active_total": 1,
                "waiting_total": 1,
                "sent_total": 0,
                "engaged_total": 0,
                "completed_total": 0,
                "archived_total": 0,
                "no_phone_total": 0,
            },
            "merchant_cart_filter_counts": {"all": 1, "waiting": 1},
        }
        now = datetime.now(timezone.utc)
        row = DashboardSnapshot(
            store_slug="demo",
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload_json=json.dumps(payload, ensure_ascii=False),
            generated_at=now - timedelta(minutes=10),
            expires_at=now - timedelta(minutes=1),
            version=1,
            status="stale",
        )
        db.session.add(row)
        db.session.commit()

    def _seed_fresh_abandoned_cart(self) -> None:
        ac = AbandonedCart(
            store_id=int(self.store.id),
            recovery_session_id="hot-slice-session-new",
            zid_cart_id=self.cart_id,
            cart_value=100.0,
            vip_mode=False,
            status="abandoned",
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac)
        db.session.commit()

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_new_cart_visible_via_hot_merge(self, _bypass: MagicMock) -> None:
        self._seed_stale_snapshot_without_new_cart()
        self._seed_fresh_abandoned_cart()
        hot_row = {
            "recovery_key": self.recovery_key,
            "zid_cart_id": self.cart_id,
            "merchant_cart_bucket": "waiting",
            "customer_lifecycle_state": "active",
        }
        with patch(
            "services.dashboard_hot_slice_v1.build_hot_slice_active_rows",
            return_value=([hot_row], {"hot_slice_rows": 1, "hot_slice_ms": 1.0, "hot_slice_queries": 3, "hot_slice_degraded": False, "hot_slice_reason": ""}),
        ):
            resp = self.client.get("/api/dashboard/normal-carts")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get("ok"))
        rks = [r.get("recovery_key") for r in body.get("merchant_carts_page_rows") or []]
        self.assertIn(self.recovery_key, rks)
        self.assertEqual(body.get("data_freshness"), "hot_merged")

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_store_counters_bump_when_hot_slice_adds_new_cart(self, _bypass: MagicMock) -> None:
        """Sprint 2.3: new hot keys advance store counters (were frozen at snapshot)."""
        self._seed_stale_snapshot_without_new_cart()
        hot_row = {
            "recovery_key": self.recovery_key,
            "zid_cart_id": self.cart_id,
            "merchant_cart_visible_tabs": ["all", "waiting"],
            "merchant_cart_primary_bucket": "waiting",
        }
        with patch(
            "services.dashboard_hot_slice_v1.build_hot_slice_active_rows",
            return_value=([hot_row], {"hot_slice_rows": 1, "hot_slice_ms": 1.0, "hot_slice_queries": 2, "hot_slice_degraded": False, "hot_slice_reason": ""}),
        ):
            resp = self.client.get("/api/dashboard/normal-carts")
        body = resp.json()
        store_counts = body.get("merchant_store_cart_counts") or {}
        self.assertEqual(store_counts.get("active_total"), 2)
        self.assertEqual(store_counts.get("waiting_total"), 2)
        health = body.get("merchant_counter_health") or {}
        self.assertTrue(health.get("counter_hot_slice_bumped"))
        self.assertEqual(health.get("counter_hot_slice_new_rows"), 1)

    def test_apply_hot_slice_payload_metadata(self) -> None:
        payload = {
            "merchant_carts_page_rows": [],
            "merchant_store_cart_counts": {"active_total": 0},
        }
        with patch(
            "services.dashboard_hot_slice_v1.build_hot_slice_active_rows",
            return_value=([], {"hot_slice_rows": 0, "hot_slice_ms": 0.5, "hot_slice_queries": 0, "hot_slice_degraded": False, "hot_slice_reason": ""}),
        ):
            out = apply_hot_slice_to_normal_carts_payload(
                dict(payload),
                store_slug="demo",
                dash_store=self.store,
            )
        self.assertEqual(out.get("data_freshness"), "snapshot_only")

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_no_hot_path_violation_in_snapshot_mode(self, _bypass: MagicMock) -> None:
        from services.dashboard_snapshot_enforcement_guard_v1 import (
            DashboardSnapshotHotPathViolation,
        )

        self._seed_stale_snapshot_without_new_cart()
        with patch(
            "services.dashboard_hot_slice_v1.build_hot_slice_active_rows",
            return_value=([], {"hot_slice_rows": 0, "hot_slice_ms": 0.1, "hot_slice_queries": 0, "hot_slice_degraded": False, "hot_slice_reason": ""}),
        ):
            try:
                resp = self.client.get("/api/dashboard/normal-carts")
            except DashboardSnapshotHotPathViolation as exc:
                self.fail(f"hot slice triggered violation: {exc}")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
