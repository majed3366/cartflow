# -*- coding: utf-8 -*-
"""Dashboard snapshot normal-carts parity regression tests."""
from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from extensions import db
from models import CartRecoveryLog, DashboardSnapshot, MerchantUser, Store
from services.dashboard_snapshot_normal_carts_parity_v1 import (
    build_and_guard_normal_carts_snapshot_write,
    compare_normal_carts_payload_parity,
    evaluate_normal_carts_snapshot_write,
    extract_row_parity_records,
)
from services.dashboard_snapshot_v1 import (
    ENV_SNAPSHOT_MODE,
    SNAPSHOT_TYPE_NORMAL_CARTS,
    fetch_latest_snapshot_row,
    upsert_dashboard_snapshot,
)
from services.normal_carts_dashboard_batch_v1 import NormalCartsDashboardPerfMeta


def _row(
    *,
    rk: str,
    cart_id: str = "",
    aid: int = 0,
    bucket: str = "sent",
) -> dict:
    return {
        "recovery_key": rk,
        "zid_cart_id": cart_id,
        "merchant_case_row_id": aid,
        "merchant_cart_bucket": bucket,
        "merchant_cart_visible_tabs": ["all", "sent"],
    }


def _payload(*rows: dict) -> dict:
    active = list(rows)
    return {
        "merchant_carts_page_rows": active,
        "merchant_archived_carts_page_rows": [],
        "merchant_cart_filter_counts": {"sent": len(active)},
    }


class DashboardSnapshotNormalCartsParityTests(unittest.TestCase):
    store_slug = "parity-regression-store"

    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        os.environ.setdefault("SECRET_KEY", "unit-test-snapshot-regression-v1")
        os.environ[ENV_SNAPSHOT_MODE] = "1"
        db.create_all()
        db.session.query(DashboardSnapshot).delete()
        db.session.query(CartRecoveryLog).delete()
        db.session.query(Store).filter(Store.zid_store_id == self.store_slug).delete(
            synchronize_session=False
        )
        db.session.query(MerchantUser).filter(
            MerchantUser.email == "parity-reg@example.com"
        ).delete(synchronize_session=False)
        db.session.commit()

    def test_live_and_snapshot_payload_identities_match(self) -> None:
        p = _payload(_row(rk=f"{self.store_slug}:cf_cart_a", cart_id="cf_cart_a", aid=1))
        parity = compare_normal_carts_payload_parity(p, p)
        self.assertTrue(parity["equivalent"])
        self.assertEqual(parity["live_row_count"], 1)

    def test_cart_scoped_recovery_key_signature(self) -> None:
        cart_id = "cf_cart_1af5812b-3a0b-483e-9fdb-85bc891e67b9"
        rk = f"cartflow-42b491:{cart_id}"
        records = extract_row_parity_records(
            _payload(_row(rk=rk, cart_id=cart_id, aid=4233))
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["recovery_key"], rk)
        self.assertEqual(records[0]["abandoned_cart_id"], 4233)

    def test_blocks_empty_regression_over_valid_snapshot(self) -> None:
        good = _payload(_row(rk=f"{self.store_slug}:cf_cart_keep", cart_id="cf_cart_keep", aid=9))
        upsert_dashboard_snapshot(
            store_slug=self.store_slug,
            store_id=None,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload=good,
        )
        empty = {
            "merchant_carts_page_rows": [],
            "merchant_archived_carts_page_rows": [],
            "merchant_cart_filter_counts": {},
        }
        perf = NormalCartsDashboardPerfMeta(partial=True, degraded=True)
        decision = evaluate_normal_carts_snapshot_write(
            store_slug=self.store_slug,
            live_payload=empty,
            candidate_payload=empty,
            perf=perf,
        )
        self.assertFalse(decision.allow_write)
        self.assertTrue(decision.keep_previous)
        self.assertIn(decision.drop_stage, ("row_build", "snapshot_write"))

    def test_blocks_truncated_payload(self) -> None:
        big = _row(rk=f"{self.store_slug}:cf_cart_big", cart_id="cf_cart_big", aid=2)
        big["blob"] = "x" * 80000
        payload = _payload(big)
        decision = evaluate_normal_carts_snapshot_write(
            store_slug=self.store_slug,
            live_payload=payload,
            candidate_payload=payload,
        )
        self.assertFalse(decision.allow_write)
        self.assertEqual(decision.drop_stage, "snapshot_write")

    @patch("services.dashboard_snapshot_normal_carts_parity_v1.build_canonical_normal_carts_payload")
    def test_dual_build_guard_allows_matching_payloads(
        self,
        mock_build: unittest.mock.Mock,
    ) -> None:
        payload = _payload(_row(rk=f"{self.store_slug}:cf_cart_x", cart_id="cf_cart_x", aid=3))
        perf = NormalCartsDashboardPerfMeta()
        mock_build.return_value = (payload, {}, perf)
        decision = build_and_guard_normal_carts_snapshot_write(
            store_slug=self.store_slug,
            dash_store=type("S", (), {"zid_store_id": self.store_slug})(),
        )
        self.assertTrue(decision.allow_write)
        self.assertEqual(decision.drop_stage, "included")
        self.assertEqual(mock_build.call_count, 2)

    @patch(
        "services.dashboard_snapshot_normal_carts_parity_v1._missing_sent_log_identities",
        return_value=["cartflow-42b491:cf_cart_missing"],
    )
    def test_blocks_when_sent_log_rows_missing(
        self,
        _mock_missing: unittest.mock.Mock,
    ) -> None:
        payload = _payload(_row(rk=f"{self.store_slug}:cf_cart_y", cart_id="cf_cart_y", aid=4))
        decision = evaluate_normal_carts_snapshot_write(
            store_slug=self.store_slug,
            live_payload=payload,
            candidate_payload=payload,
        )
        self.assertFalse(decision.allow_write)
        self.assertEqual(decision.drop_stage, "row_build")
        self.assertEqual(decision.reason, "sent_log_rows_missing")

    def test_store_identity_resolution_matches_canonical_slug(self) -> None:
        user = MerchantUser(email="parity-reg@example.com", password_hash="x", merchant_name="P")
        db.session.add(user)
        db.session.flush()
        st = Store(
            zid_store_id=self.store_slug,
            merchant_user_id=int(user.id),
            is_active=True,
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.commit()
        from services.dashboard_snapshot_builder_v1 import _resolve_store_row  # noqa: PLC0415
        from services.dashboard_snapshot_v1 import canonical_snapshot_store_slug  # noqa: PLC0415

        row = _resolve_store_row(int(st.id), self.store_slug)
        self.assertIsNotNone(row)
        self.assertEqual(canonical_snapshot_store_slug(row), self.store_slug)


if __name__ == "__main__":
    unittest.main()
