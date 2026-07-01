# -*- coding: utf-8 -*-
"""Snapshot Truth Diagnostics V1 tests."""
from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT, app
from models import AbandonedCart, DashboardSnapshot, MerchantUser, Store
from services.dashboard_snapshot_v1 import ENV_SNAPSHOT_MODE, SNAPSHOT_TYPE_NORMAL_CARTS


def _enable_snapshot_mode() -> None:
    os.environ["ENV"] = "development"
    os.environ[ENV_SNAPSHOT_MODE] = "1"
    os.environ.setdefault("SECRET_KEY", "unit-test-snapshot-truth-v1")


class SnapshotTruthDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        _enable_snapshot_mode()
        db.create_all()
        db.session.query(DashboardSnapshot).delete()
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == "snap-truth-demo").delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "snap-truth-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()
        self.client = TestClient(app)

        user = MerchantUser(
            email="snap-truth-demo@example.com",
            password_hash="x",
            merchant_name="Snap Truth Demo",
        )
        db.session.add(user)
        db.session.flush()
        st = Store(
            zid_store_id="snap-truth-demo",
            merchant_user_id=int(user.id),
            is_active=True,
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        self.store = st
        self.cart_id = "cf_cart_snap_truth_unit_001"
        self.session_id = "cf-snap-truth-session-001"
        self.recovery_key = f"snap-truth-demo:{self.cart_id}"
        ac = AbandonedCart(
            store_id=int(st.id),
            recovery_session_id=self.session_id,
            zid_cart_id=self.cart_id,
            cart_value=500.0,
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.commit()

    def tearDown(self) -> None:
        os.environ.pop(ENV_SNAPSHOT_MODE, None)
        db.session.query(DashboardSnapshot).delete()
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == "snap-truth-demo").delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "snap-truth-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

    def _seed_snapshot(self, *, include_row: bool) -> None:
        rows = []
        if include_row:
            rows = [
                {
                    "recovery_key": self.recovery_key,
                    "zid_cart_id": self.cart_id,
                    "merchant_cart_bucket": "sent",
                    "merchant_cart_visible_tabs": ["all", "sent"],
                }
            ]
        payload = {
            "merchant_carts_page_rows": rows,
            "merchant_archived_carts_page_rows": [],
            "merchant_cart_filter_counts": {"all": len(rows), "sent": len(rows)},
        }
        now = datetime.now(timezone.utc)
        row = DashboardSnapshot(
            store_slug="snap-truth-demo",
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload_json=json.dumps(payload, ensure_ascii=False),
            generated_at=now,
            expires_at=now + timedelta(seconds=120),
            version=1,
            status="active",
        )
        db.session.add(row)
        db.session.commit()

    def test_route_on_production_allowlist(self) -> None:
        self.assertIn(
            "/dev/snapshot-truth-diagnostics",
            _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT,
        )

    def test_route_requires_identity(self) -> None:
        os.environ.pop("ENV", None)
        r = self.client.get("/dev/snapshot-truth-diagnostics")
        self.assertEqual(r.status_code, 400, r.text[:300])

    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_row_missing_when_live_visible_snapshot_absent(
        self, mock_inclusion: unittest.mock.Mock
    ) -> None:
        mock_inclusion.return_value = {
            "dashboard_visible": True,
            "dashboard_exclusion_reason": None,
        }
        os.environ.pop("ENV", None)
        r = self.client.get(
            "/dev/snapshot-truth-diagnostics",
            params={
                "store_slug": "snap-truth-demo",
                "cart_id": self.cart_id,
            },
        )
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.json()
        self.assertTrue(body["checks"]["db"])
        self.assertTrue(body["checks"]["live_builder"])
        self.assertFalse(body["checks"]["snapshot"])
        self.assertEqual(body["reason"], "snapshot_missing")
        self.assertFalse(body["snapshot_row_present"])

    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_row_present_in_snapshot(self, mock_inclusion: unittest.mock.Mock) -> None:
        mock_inclusion.return_value = {
            "dashboard_visible": True,
            "dashboard_exclusion_reason": None,
        }
        self._seed_snapshot(include_row=True)
        os.environ.pop("ENV", None)
        r = self.client.get(
            "/dev/snapshot-truth-diagnostics",
            params={"recovery_key": self.recovery_key},
        )
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.json()
        self.assertTrue(body["snapshot_exists"])
        self.assertTrue(body["snapshot_row_present"])
        self.assertEqual(body["snapshot_row_recovery_key"], self.recovery_key)
        self.assertEqual(body["snapshot_bucket"], "sent")
        self.assertIn("sent", body["snapshot_filter_tabs"])
        self.assertTrue(body["checks"]["snapshot"])
        self.assertTrue(body["checks"]["dashboard"])
        self.assertEqual(body["reason"], "ok")

    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_frontend_filter_render_when_only_archived(
        self, mock_inclusion: unittest.mock.Mock
    ) -> None:
        mock_inclusion.return_value = {
            "dashboard_visible": True,
            "dashboard_exclusion_reason": None,
        }
        payload = {
            "merchant_carts_page_rows": [],
            "merchant_archived_carts_page_rows": [
                {
                    "recovery_key": self.recovery_key,
                    "zid_cart_id": self.cart_id,
                    "merchant_cart_bucket": "recovered",
                }
            ],
            "merchant_cart_filter_counts": {"all": 1, "recovered": 1},
        }
        now = datetime.now(timezone.utc)
        db.session.add(
            DashboardSnapshot(
                store_slug="snap-truth-demo",
                snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
                payload_json=json.dumps(payload, ensure_ascii=False),
                generated_at=now,
                expires_at=now + timedelta(seconds=120),
                version=1,
                status="active",
            )
        )
        db.session.commit()
        os.environ.pop("ENV", None)
        r = self.client.get(
            "/dev/snapshot-truth-diagnostics",
            params={
                "store_slug": "snap-truth-demo",
                "cart_id": self.cart_id,
            },
        )
        body = r.json()
        self.assertTrue(body["snapshot_row_present"])
        self.assertFalse(body["dashboard_visible"])
        self.assertEqual(body["reason"], "frontend_filter_render")
        self.assertEqual(body["snapshot_row_collection"], "archived")


if __name__ == "__main__":
    unittest.main()
