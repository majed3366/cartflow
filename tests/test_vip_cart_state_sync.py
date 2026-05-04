# -*- coding: utf-8 -*-
"""VIP abandoned cart state stays consistent after live cart updates / clear / conversion."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
import main
from models import AbandonedCart, Store
from tests.test_recovery_isolation import _reset_recovery_memory


class VipCartStateSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)

    def test_below_threshold_sync_via_session_only_no_cart_id(self) -> None:
        """نفس سلوك الويدجت الحقيقي (‎add_to_cart‎ بدون ‎cart_id‎) — المطابقة بـ ‎recovery_session_id‎."""
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_sess_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_only_{uuid.uuid4().hex[:8]}"
        cid = f"c_only_{uuid.uuid4().hex[:10]}"
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=cid,
            cart_value=900.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid,
        )
        db.session.add(ac)
        db.session.commit()

        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "add_to_cart",
                "store": slug,
                "session_id": sid,
                "cart": [{"price": 100.0, "quantity": 1}],
                "cart_total": 100.0,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        db.session.refresh(ac)
        self.assertFalse(bool(ac.vip_mode))
        self.assertAlmostEqual(float(ac.cart_value or 0.0), 100.0)

    def test_below_threshold_clears_vip_via_cart_event(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_bt_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=900,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_below_{uuid.uuid4().hex[:8]}"
        cid = f"c_below_{uuid.uuid4().hex[:10]}"
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=cid,
            cart_value=1200.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid,
        )
        db.session.add(ac)
        db.session.commit()

        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "add_to_cart",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart": [{"price": 100.0, "quantity": 1}],
                "cart_total": 100.0,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        db.session.refresh(ac)
        self.assertFalse(bool(ac.vip_mode))
        self.assertEqual((ac.status or "").strip(), "abandoned")
        self.assertAlmostEqual(float(ac.cart_value or 0.0), 100.0)

    def test_empty_cart_recovered_and_removed_from_priority(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_cl_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=900,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_clr_{uuid.uuid4().hex[:8]}"
        cid = f"c_clr_{uuid.uuid4().hex[:10]}"
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=cid,
            cart_value=1200.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid,
        )
        db.session.add(ac)
        db.session.commit()

        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "add_to_cart",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart": [],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        db.session.refresh(ac)
        self.assertFalse(bool(ac.vip_mode))
        self.assertEqual((ac.status or "").strip(), "recovered")
        ids = [x["id"] for x in main._vip_priority_cart_alert_list()]
        self.assertNotIn(ac.id, ids)

    def test_api_conversion_closes_vip_row(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_cv_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=900,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_buy_{uuid.uuid4().hex[:8]}"
        cid = f"c_buy_{uuid.uuid4().hex[:10]}"
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=cid,
            cart_value=1200.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid,
        )
        db.session.add(ac)
        db.session.commit()

        r = self.client.post(
            "/api/conversion",
            json={
                "store_slug": slug,
                "session_id": sid,
                "purchase_completed": True,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        db.session.refresh(ac)
        self.assertFalse(bool(ac.vip_mode))
        self.assertEqual((ac.status or "").strip(), "recovered")


if __name__ == "__main__":
    unittest.main()
