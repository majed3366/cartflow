# -*- coding: utf-8 -*-
"""Customer Movement Visibility v1 — dashboard presentation tests."""
from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from extensions import db
from models import AbandonedCart, MerchantUser, Store
from services.behavioral_recovery.state_store import merge_behavioral_state
from services.customer_movement_visibility_v1 import (
    LINE_PURCHASE_AR,
    LINE_REPLY_AR,
    LINE_RETURN_AFTER_MESSAGE_AR,
    LINE_RETURN_SITE_AR,
    attach_customer_movement_visibility_v1,
    bulk_movement_snapshot_fields_by_recovery_keys,
    enrich_normal_carts_payload_customer_movement_v1,
    resolve_customer_movement_line_ar,
)
from services.recovery_truth_timeline_v1 import STATUS_CUSTOMER_REPLY


def _row(**kwargs: object) -> dict:
    base = {
        "recovery_key": "demo:cf_cart_mv_001",
        "customer_lifecycle_state": "active",
        "merchant_cart_bucket": "waiting",
    }
    base.update(kwargs)
    return base


class CustomerMovementVisibilityResolveTests(unittest.TestCase):
    def test_returned_to_site_shows_site_line(self) -> None:
        line = resolve_customer_movement_line_ar(
            log_statuses=frozenset({"returned_to_site"}),
        )
        self.assertEqual(line, LINE_RETURN_SITE_AR)

    def test_passive_return_shows_site_line(self) -> None:
        line = resolve_customer_movement_line_ar(
            behavioral={"passive_return_visit_count": 2},
        )
        self.assertEqual(line, LINE_RETURN_SITE_AR)

    def test_customer_reply_shows_reply_line(self) -> None:
        line = resolve_customer_movement_line_ar(
            timeline_statuses=frozenset({STATUS_CUSTOMER_REPLY}),
        )
        self.assertEqual(line, LINE_REPLY_AR)

    def test_purchase_truth_shows_purchase_line(self) -> None:
        line = resolve_customer_movement_line_ar(purchase_truth=True)
        self.assertEqual(line, LINE_PURCHASE_AR)

    def test_purchase_priority_over_return_and_reply(self) -> None:
        line = resolve_customer_movement_line_ar(
            purchase_truth=True,
            timeline_statuses=frozenset({STATUS_CUSTOMER_REPLY}),
            log_statuses=frozenset({"returned_to_site"}),
        )
        self.assertEqual(line, LINE_PURCHASE_AR)

    def test_return_after_message_copy(self) -> None:
        line = resolve_customer_movement_line_ar(
            log_statuses=frozenset({"returned_to_site"}),
            sent_count=1,
        )
        self.assertEqual(line, LINE_RETURN_AFTER_MESSAGE_AR)

    def test_no_movement_returns_none(self) -> None:
        self.assertIsNone(resolve_customer_movement_line_ar())


class CustomerMovementVisibilityAttachTests(unittest.TestCase):
    def test_attach_does_not_change_lifecycle_state(self) -> None:
        target = _row(customer_lifecycle_state="waiting_first_send")
        before = dict(target)
        attach_customer_movement_visibility_v1(
            target,
            log_statuses=frozenset({"returned_to_site"}),
            lifecycle_state=target["customer_lifecycle_state"],
        )
        for key in (
            "customer_lifecycle_state",
            "merchant_cart_bucket",
            "recovery_key",
        ):
            self.assertEqual(target.get(key), before.get(key))
        self.assertTrue(target.get("customer_movement_visible"))
        self.assertEqual(target.get("customer_movement_line_ar"), LINE_RETURN_SITE_AR)

    def test_completed_row_lifecycle_unchanged_with_purchase_movement(self) -> None:
        target = _row(
            customer_lifecycle_state="completed",
            merchant_cart_bucket="recovered",
            customer_lifecycle_completed_variant="purchased",
        )
        before_lc = target["customer_lifecycle_state"]
        attach_customer_movement_visibility_v1(
            target,
            purchase_truth=True,
            lifecycle_state=before_lc,
        )
        self.assertEqual(target["customer_lifecycle_state"], before_lc)
        self.assertEqual(target["customer_lifecycle_completed_variant"], "purchased")
        self.assertEqual(target["customer_movement_line_ar"], LINE_PURCHASE_AR)


class CustomerMovementVisibilityBulkTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("SECRET_KEY", "unit-test-movement-visibility-v1")
        self.rk = "demo:cf_cart_bulk_mv"

    def test_bulk_load_is_bounded_by_keys(self) -> None:
        out = bulk_movement_snapshot_fields_by_recovery_keys(
            [self.rk, "demo:missing"]
        )
        self.assertNotIn("demo:missing", out)

    def test_enrich_uses_bulk_reads_not_per_row_history_scan(self) -> None:
        payload = {
            "merchant_carts_page_rows": [
                _row(
                    recovery_key=self.rk,
                    customer_lifecycle_state="waiting_first_send",
                )
            ],
            "merchant_archived_carts_page_rows": [],
        }
        with patch(
            "services.customer_movement_visibility_v1.bulk_movement_snapshot_fields_by_recovery_keys",
            wraps=bulk_movement_snapshot_fields_by_recovery_keys,
        ) as bulk_snap, patch(
            "services.customer_movement_visibility_v1._bulk_behavioral_movement_hints_for_rows",
            return_value={self.rk: {"passive_return_visit_count": 1}},
        ):
            enrich_normal_carts_payload_customer_movement_v1(payload)
            bulk_snap.assert_called_once()
            called_keys = bulk_snap.call_args[0][0]
            self.assertEqual(called_keys, [self.rk])
        row = payload["merchant_carts_page_rows"][0]
        self.assertEqual(row.get("customer_movement_line_ar"), LINE_RETURN_SITE_AR)


class CustomerMovementVisibilityIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("SECRET_KEY", "unit-test-movement-visibility-v1")
        db.create_all()
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == "demo").delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "mv-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

        user = MerchantUser(
            email="mv-demo@example.com",
            password_hash="x",
            merchant_name="MV Demo",
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
        self.cart_id = "cf_cart_mv_hot_001"
        self.recovery_key = f"demo:{self.cart_id}"
        now = datetime.now(timezone.utc)
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=self.cart_id,
            recovery_session_id="mv_sess_001",
            cart_value=120.0,
            status="abandoned",
            last_seen_at=now,
        )
        db.session.add(ac)
        db.session.flush()
        merge_behavioral_state(
            ac,
            passive_return_visit_count=1,
            last_passive_return_visit_at=now.isoformat(),
        )
        db.session.add(ac)
        db.session.commit()
        self.ac = ac

    def tearDown(self) -> None:
        db.session.query(AbandonedCart).delete()
        db.session.query(Store).filter(Store.zid_store_id == "demo").delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "mv-demo@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

    def test_hot_slice_style_row_can_include_movement_line(self) -> None:
        from services.dashboard_hot_slice_v1 import apply_hot_slice_to_normal_carts_payload

        hot_row = _row(
            recovery_key=self.recovery_key,
            cart_id=self.cart_id,
            session_id="mv_sess_001",
            store_slug="demo",
            customer_lifecycle_state="active",
        )
        attach_customer_movement_visibility_v1(
            hot_row,
            recovery_key=self.recovery_key,
            behavioral={"passive_return_visit_count": 1},
        )
        payload = apply_hot_slice_to_normal_carts_payload(
            {
                "ok": True,
                "merchant_carts_page_rows": [],
                "merchant_store_cart_counts": {"active_total": 0},
            },
            store_slug="demo",
        )
        payload["merchant_carts_page_rows"] = [hot_row]
        enriched = enrich_normal_carts_payload_customer_movement_v1(payload)
        row = enriched["merchant_carts_page_rows"][0]
        self.assertEqual(row.get("customer_movement_line_ar"), LINE_RETURN_SITE_AR)

    def test_movement_snapshot_priority_over_behavioral(self) -> None:
        snap = {
            "provider_sent": True,
            "returned_to_site": True,
            "passive_return_visit_count": 0,
        }
        line = resolve_customer_movement_line_ar(
            movement_snapshot=snap,
            sent_count=1,
        )
        self.assertEqual(line, LINE_RETURN_AFTER_MESSAGE_AR)


if __name__ == "__main__":
    unittest.main()
