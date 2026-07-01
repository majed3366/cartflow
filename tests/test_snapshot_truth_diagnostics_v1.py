# -*- coding: utf-8 -*-
"""Snapshot Truth Diagnostics V1 tests."""
from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT, app
from models import AbandonedCart, CartRecoveryLog, DashboardSnapshot, MerchantUser, Store
from services.dashboard_snapshot_v1 import ENV_SNAPSHOT_MODE, SNAPSHOT_TYPE_NORMAL_CARTS
from services.snapshot_truth_diagnostics_v1 import (
    _aggregate_alias_results,
    _diagnostic_dash_store,
    _find_sent_log_diagnostic,
    _resolve_key_identity,
    build_snapshot_truth_diagnostics,
)


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


class SnapshotTruthAliasDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        import main  # noqa: F401

        _enable_snapshot_mode()
        db.create_all()
        db.session.query(CartRecoveryLog).delete()
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == "snap-alias-demo").delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "snap-alias-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

        user = MerchantUser(
            email="snap-alias-demo@example.com",
            password_hash="x",
            merchant_name="Snap Alias Demo",
        )
        db.session.add(user)
        db.session.flush()
        st = Store(
            zid_store_id="snap-alias-demo",
            merchant_user_id=int(user.id),
            is_active=True,
            recovery_attempts=3,
        )
        db.session.add(st)
        db.session.flush()
        self.store = st
        self.cart_id = "cf_cart_snap_alias_unit_4233"
        self.session_id = "cf-snap-alias-session-4233"
        self.cart_key = f"snap-alias-demo:{self.cart_id}"
        self.session_key = f"snap-alias-demo:{self.session_id}"
        ac = AbandonedCart(
            store_id=int(st.id),
            recovery_session_id=self.session_id,
            zid_cart_id=self.cart_id,
            cart_value=10000.0,
            vip_mode=False,
            status="abandoned",
        )
        db.session.add(ac)
        db.session.flush()
        self.ac = ac
        db.session.add(
            CartRecoveryLog(
                store_slug="snap-alias-demo",
                session_id=self.session_id,
                cart_id=self.cart_id,
                recovery_key=self.cart_key,
                status="sent_real",
                message="alias test send",
                step=1,
            )
        )
        db.session.commit()

    def tearDown(self) -> None:
        os.environ.pop(ENV_SNAPSHOT_MODE, None)
        db.session.rollback()
        db.session.query(CartRecoveryLog).delete()
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == "snap-alias-demo").delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "snap-alias-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

    def test_cf_cart_suffix_not_parsed_as_session_id(self) -> None:
        key_type, cart_id, session_id, ac_row = _resolve_key_identity(
            self.cart_key,
            store_slug="snap-alias-demo",
            ac_row=None,
        )
        self.assertEqual(key_type, "cart")
        self.assertEqual(cart_id, self.cart_id)
        self.assertEqual(session_id, self.session_id)
        self.assertIsNotNone(ac_row)
        self.assertEqual(int(ac_row.id), int(self.ac.id))

    def test_provided_store_slug_used_when_dash_store_unavailable(self) -> None:
        proxy = _diagnostic_dash_store("snap-alias-demo", None)
        self.assertEqual(getattr(proxy, "zid_store_id", None), "snap-alias-demo")
        lg = _find_sent_log_diagnostic(
            store_slug="snap-alias-demo",
            recovery_key=self.session_key,
            cart_id=self.cart_id,
            session_id=self.session_id,
            abandoned_cart_id=int(self.ac.id),
        )
        self.assertIsNotNone(lg)
        self.assertEqual(lg.recovery_key, self.cart_key)

    def test_aggregate_reason_prefers_included_over_no_sent_log(self) -> None:
        visible, matched_key, matched_by, reason = _aggregate_alias_results(
            [
                {
                    "recovery_key": self.cart_key,
                    "key_type": "cart",
                    "sent_log_found": True,
                    "returned_in_api": True,
                    "exclusion_stage": "included",
                    "exclusion_reason": "included",
                    "dashboard_visible": True,
                },
                {
                    "recovery_key": self.session_key,
                    "key_type": "session",
                    "sent_log_found": False,
                    "returned_in_api": False,
                    "exclusion_stage": "no_sent_log",
                    "exclusion_reason": "no_sent_log",
                    "dashboard_visible": False,
                },
            ]
        )
        self.assertTrue(visible)
        self.assertEqual(matched_key, self.cart_key)
        self.assertEqual(reason, "included")
        self.assertIn("cart", matched_by)

    @patch("services.merchant_cart_presence_trace_v1.trace_merchant_cart_presence")
    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_session_alias_failure_does_not_override_cart_key_success(
        self,
        mock_inclusion: unittest.mock.Mock,
        mock_trace: unittest.mock.Mock,
    ) -> None:
        def _inclusion_side_effect(*, recovery_key: str, dash_store: Any, lifecycle: str = "active"):
            _ = dash_store, lifecycle
            if recovery_key == self.cart_key:
                return {
                    "dashboard_visible": False,
                    "dashboard_exclusion_reason": "included",
                }
            return {
                "dashboard_visible": False,
                "dashboard_exclusion_reason": "no_sent_log",
            }

        def _trace_side_effect(recovery_key: str, *, dash_store: Any, **kwargs: Any):
            _ = dash_store, kwargs
            if recovery_key == self.cart_key:
                return {
                    "exclusion_stage": "included",
                    "returned_in_api": True,
                    "log_id": 1,
                }
            return {
                "exclusion_stage": "no_sent_log",
                "returned_in_api": False,
                "log_id": None,
            }

        mock_inclusion.side_effect = _inclusion_side_effect
        mock_trace.side_effect = _trace_side_effect

        body = build_snapshot_truth_diagnostics(
            store_slug="snap-alias-demo",
            cart_id=self.cart_id,
            lifecycle="active",
        )
        self.assertTrue(body["live_builder_visible"])
        self.assertEqual(body["live_builder_status"], "included")
        self.assertNotEqual(body["reason"], "no_sent_log")
        self.assertEqual(body["matched_key"], self.cart_key)
        self.assertTrue(body["checks"]["live_builder"])
        cart_alias = body["alias_key_results"][0]
        self.assertEqual(cart_alias["key_type"], "cart")
        self.assertTrue(cart_alias["sent_log_found"])
        session_alias = body["alias_key_results"][1]
        self.assertEqual(session_alias["key_type"], "session")
        self.assertEqual(session_alias["exclusion_reason"], "no_sent_log")

    @patch("services.merchant_cart_presence_trace_v1.trace_merchant_cart_presence")
    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_cart_scoped_key_with_sent_log_succeeds(
        self,
        mock_inclusion: unittest.mock.Mock,
        mock_trace: unittest.mock.Mock,
    ) -> None:
        mock_inclusion.return_value = {
            "dashboard_visible": True,
            "dashboard_exclusion_reason": None,
        }
        mock_trace.return_value = {
            "exclusion_stage": "included",
            "returned_in_api": True,
            "log_id": 99,
        }

        body = build_snapshot_truth_diagnostics(
            store_slug="snap-alias-demo",
            cart_id=self.cart_id,
        )
        self.assertTrue(body["live_builder_visible"])
        self.assertEqual(body["recovery_key"], self.cart_key)
        self.assertEqual(body["recovery_keys_checked"][0], self.cart_key)
        self.assertTrue(body["alias_key_results"][0]["sent_log_found"])

    @patch("services.merchant_cart_presence_trace_v1.trace_merchant_cart_presence")
    @patch(
        "services.recovery_dashboard_inclusion_truth.build_recovery_dashboard_inclusion_truth"
    )
    def test_cart_4233_alias_scenario(
        self,
        mock_inclusion: unittest.mock.Mock,
        mock_trace: unittest.mock.Mock,
    ) -> None:
        """Regression: cart 4233 — cart-key included must not lose to session-key no_sent_log."""
        store = "cartflow-42b491"
        cart_id = "cf_cart_1af5812b-3a0b-483e-9fdb-85bc891e67b9"
        session_id = "cf-mr27v1kx-kolbfubr"
        cart_key = f"{store}:{cart_id}"
        session_key = f"{store}:{session_id}"

        def _inclusion_side_effect(*, recovery_key: str, dash_store: Any, lifecycle: str = "active"):
            _ = dash_store, lifecycle
            if recovery_key == cart_key:
                return {
                    "dashboard_visible": False,
                    "dashboard_exclusion_reason": "included",
                    "cart_recovery_log_sent_count": 1,
                }
            return {
                "dashboard_visible": False,
                "dashboard_exclusion_reason": "no_sent_log",
                "cart_recovery_log_sent_count": 0,
            }

        def _trace_side_effect(recovery_key: str, *, dash_store: Any, **kwargs: Any):
            _ = dash_store, kwargs
            if recovery_key == cart_key:
                return {
                    "exclusion_stage": "included",
                    "returned_in_api": True,
                    "log_id": 1188,
                    "cart_id": cart_id,
                    "session_id": session_id,
                }
            return {
                "exclusion_stage": "no_sent_log",
                "returned_in_api": False,
                "log_id": None,
            }

        mock_inclusion.side_effect = _inclusion_side_effect
        mock_trace.side_effect = _trace_side_effect

        prod_store = (
            db.session.query(Store)
            .filter(Store.zid_store_id == store)
            .order_by(Store.id.desc())
            .first()
        )
        if prod_store is None:
            prod_store = Store(
                zid_store_id=store,
                merchant_user_id=int(self.store.merchant_user_id),
                is_active=True,
                recovery_attempts=3,
            )
            db.session.add(prod_store)
            db.session.flush()
        ac_row = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == cart_id)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
        if ac_row is None:
            db.session.add(
                AbandonedCart(
                    store_id=int(prod_store.id),
                    recovery_session_id=session_id,
                    zid_cart_id=cart_id,
                    cart_value=10000.0,
                    vip_mode=False,
                    status="abandoned",
                )
            )
        if (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.recovery_key == cart_key)
            .first()
            is None
        ):
            db.session.add(
                CartRecoveryLog(
                    store_slug=store,
                    session_id=session_id,
                    cart_id=cart_id,
                    recovery_key=cart_key,
                    status="sent_real",
                    message="cart 4233 send",
                    step=1,
                )
            )
        db.session.commit()

        body = build_snapshot_truth_diagnostics(
            store_slug=store,
            cart_id=cart_id,
        )
        self.assertTrue(body["checks"]["db"])
        self.assertTrue(body["checks"]["live_builder"])
        self.assertNotEqual(body["reason"], "no_sent_log")
        self.assertIn(body["reason"], ("snapshot_missing", "snapshot_stale", "row_missing", "ok"))
        self.assertEqual(body["matched_key"], cart_key)
        self.assertEqual(body["live_builder_status"], "included")
        self.assertEqual(body["recovery_keys_checked"][0], cart_key)
        self.assertEqual(body["recovery_keys_checked"][1], session_key)


if __name__ == "__main__":
    unittest.main()
