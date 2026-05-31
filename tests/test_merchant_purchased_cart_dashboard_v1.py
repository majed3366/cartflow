# -*- coding: utf-8 -*-
"""Purchased recovery carts stay visible in merchant dashboard completed bucket."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from extensions import db
from fastapi.testclient import TestClient
from models import AbandonedCart, CartRecoveryLog, Store
from services.cartflow_purchase_truth import (
    record_purchase,
    reset_purchase_truth_foundation_for_tests,
)
from services.purchase_truth import ingest_purchase_truth_payload

import main


class MerchantPurchasedCartDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_purchase_truth_foundation_for_tests()
        self._client = TestClient(main.app)
        self._store = db.session.query(Store).filter(
            Store.zid_store_id == "m-purch-dash"
        ).first()
        if self._store is None:
            self._store = Store(
                zid_store_id="m-purch-dash",
                recovery_delay=1,
                recovery_delay_unit="minutes",
            )
            db.session.add(self._store)
            db.session.commit()

    def tearDown(self) -> None:
        reset_purchase_truth_foundation_for_tests()

    def _seed_sent_cart(self) -> tuple[Store, AbandonedCart, str]:
        st = self._store
        sid = "s-purch-dash-1"
        cid = "c-purch-dash-1"
        slug = st.zid_store_id or "m-purch-dash"
        db.session.query(AbandonedCart).filter(
            AbandonedCart.recovery_session_id == sid
        ).delete(synchronize_session=False)
        db.session.commit()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=cid,
            recovery_session_id=sid,
            customer_phone="+966501234567",
            status="abandoned",
            cart_value=65.0,
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.commit()
        rk = f"{slug}:{sid}"
        now = datetime.now(timezone.utc)
        db.session.add(
            CartRecoveryLog(
                store_slug=slug,
                session_id=sid,
                cart_id=cid,
                recovery_key=rk,
                phone="966501234567",
                message="test",
                status="sent_real",
                step=1,
                created_at=now,
            )
        )
        db.session.commit()
        return st, ac, rk

    def test_purchased_cart_visible_in_active_api_completed_bucket(self) -> None:
        st, ac, rk = self._seed_sent_cart()
        ingest_purchase_truth_payload(
            {
                "store_slug": st.zid_store_id,
                "session_id": ac.recovery_session_id,
                "cart_id": ac.zid_cart_id,
                "purchase_completed": True,
            }
        )
        db.session.expire_all()
        refreshed = db.session.get(AbandonedCart, int(ac.id))
        self.assertEqual(str(refreshed.status or "").strip().lower(), "recovered")

        with patch("main._dashboard_recovery_store_row", return_value=st):
            r = self._client.get("/api/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.json()
        self.assertTrue(body.get("ok"))
        rows = body.get("merchant_carts_page_rows") or []
        match = next(
            (
                row
                for row in rows
                if int(row.get("merchant_case_row_id") or 0) == int(ac.id)
            ),
            None,
        )
        self.assertIsNotNone(match, msg=f"cart missing from active API rows; rk={rk}")
        assert match is not None
        self.assertEqual(
            str(match.get("customer_lifecycle_state") or "").strip().lower(),
            "completed",
        )
        self.assertIn("تم الشراء", str(match.get("customer_lifecycle_label_ar") or ""))
        tabs = match.get("merchant_cart_visible_tabs") or []
        self.assertIn("recovered", tabs)
        fc = body.get("merchant_cart_filter_counts") or {}
        self.assertGreaterEqual(int(fc.get("recovered") or 0), 1)
        tabs = match.get("merchant_cart_visible_tabs") or []
        self.assertIn("recovered", tabs)
        self.assertTrue(
            match.get("merchant_cart_bucket") == "recovered"
            or str(match.get("customer_lifecycle_state") or "").strip().lower() == "completed"
        )

    def test_recovered_cart_augmented_without_purchase_truth_row(self) -> None:
        """Sent log + status recovered still surfaces when purchase truth is in-memory only."""
        st, ac, rk = self._seed_sent_cart()
        record_purchase(
            recovery_key=rk,
            purchase_source="test",
            store_slug=st.zid_store_id or "",
            session_id=ac.recovery_session_id or "",
            cart_id=ac.zid_cart_id,
            apply_lifecycle=True,
        )
        ac.status = "recovered"
        ac.recovered_at = datetime.now(timezone.utc)
        db.session.commit()

        with patch("main._dashboard_recovery_store_row", return_value=st):
            r = self._client.get("/api/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200)
        rows = (r.json() or {}).get("merchant_carts_page_rows") or []
        self.assertTrue(
            any(int(row.get("merchant_case_row_id") or 0) == int(ac.id) for row in rows)
        )


if __name__ == "__main__":
    unittest.main()
