# -*- coding: utf-8 -*-
"""VIP abandoned cart state stays consistent after live cart updates / clear / conversion."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
import main
from models import AbandonedCart, CartRecoveryReason, Store
from tests.test_recovery_isolation import _reset_recovery_memory


class VipCartStateSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)

    def test_dashboard_dedupes_two_vip_rows_same_session(self) -> None:
        """صفّان ‎VIP‎ لنفس الجلسة: التنظيف + الاستعلام يعرض صفاً واحداً."""
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_dedup_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()

        sid = f"s_dedup_{uuid.uuid4().hex[:8]}"
        cid_a = f"c_dedup_a_{uuid.uuid4().hex[:10]}"
        cid_b = f"c_dedup_b_{uuid.uuid4().hex[:10]}"

        older = datetime.now(timezone.utc) - timedelta(hours=2)
        ac_old = AbandonedCart(
            store_id=store.id,
            zid_cart_id=cid_a,
            cart_value=900.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid,
            last_seen_at=older,
        )
        ac_new = AbandonedCart(
            store_id=store.id,
            zid_cart_id=cid_b,
            cart_value=950.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac_old)
        db.session.add(ac_new)
        db.session.commit()

        dash = main._dashboard_recovery_store_row()
        self.assertIsNotNone(dash)
        self.assertEqual(int(dash.id), int(store.id))

        lst = main._vip_priority_cart_alert_list()
        matching_cart = [
            x for x in lst if abs(float(x.get("cart_value") or 0.0) - 950.0) < 0.01
        ]
        self.assertEqual(len(matching_cart), 1)

        ac_db = db.session.query(AbandonedCart).filter_by(recovery_session_id=sid).all()
        self.assertEqual(len(ac_db), 1)
        self.assertAlmostEqual(float(ac_db[0].cart_value or 0.0), 950.0)

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
                "event": "cart_state_sync",
                "reason": "remove",
                "store": slug,
                "session_id": sid,
                "cart_total": 100.0,
                "items_count": 1,
                "cart": [{"price": 100.0, "quantity": 1}],
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
                "event": "cart_state_sync",
                "reason": "remove",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 100.0,
                "items_count": 1,
                "cart": [{"price": 100.0, "quantity": 1}],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        db.session.refresh(ac)
        self.assertFalse(bool(ac.vip_mode))
        self.assertEqual((ac.status or "").strip(), "abandoned")
        self.assertAlmostEqual(float(ac.cart_value or 0.0), 100.0)
        jb = r.json() or {}
        self.assertTrue(jb.get("ok"))
        self.assertTrue(jb.get("vip_from_cart_total"))
        self.assertFalse(jb.get("is_vip"))
        self.assertAlmostEqual(float(jb.get("cart_total") or 0.0), 100.0)
        self.assertEqual(jb.get("vip_cart_threshold"), 900)

    def test_cart_updated_creates_vip_abandoned_row_when_none(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_cre_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()
        dash = main._dashboard_recovery_store_row()
        self.assertIsNotNone(dash)
        self.assertEqual(int(dash.id), int(store.id))

        sid = f"s_cre_{uuid.uuid4().hex[:8]}"
        cid = f"c_cre_{uuid.uuid4().hex[:10]}"
        db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).delete(
            synchronize_session=False
        )
        db.session.commit()

        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "page_load",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 637.0,
                "items_count": 1,
                "cart": [{"price": 637.0, "quantity": 1}],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        ac = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac)
        self.assertTrue(bool(ac.vip_mode))
        self.assertEqual((ac.status or "").strip(), "abandoned")
        self.assertAlmostEqual(float(ac.cart_value or 0.0), 637.0)
        jb = r.json() or {}
        self.assertTrue(jb.get("ok"))
        self.assertTrue(jb.get("vip_from_cart_total"))
        self.assertTrue(jb.get("is_vip"))
        self.assertAlmostEqual(float(jb.get("cart_total") or 0.0), 637.0)
        self.assertEqual(jb.get("vip_cart_threshold"), 500)
        self.assertEqual(int(ac.store_id or 0), int(store.id))
        self.assertEqual((ac.recovery_session_id or "").strip(), sid.strip())
        prios = main._vip_priority_cart_alert_list()
        self.assertTrue(any(int(x["id"]) == int(ac.id) for x in prios))

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_first_vip_cart_state_sync_triggers_merchant_auto_alert(self, mock_send) -> None:
        mock_send.return_value = {"ok": True}
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_auto_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            store_whatsapp_number="+966501112233",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_auto_{uuid.uuid4().hex[:8]}"
        cid = f"c_auto_{uuid.uuid4().hex[:10]}"
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "page_load",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 637.0,
                "items_count": 1,
                "cart": [{"price": 637.0, "quantity": 1}],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        mock_send.assert_called_once()

    @patch("main.try_send_vip_merchant_whatsapp_alert")
    def test_second_vip_cart_state_sync_does_not_repeat_merchant_alert(self, mock_send) -> None:
        mock_send.return_value = {"ok": True}
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_auto2_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            store_whatsapp_number="+966501112233",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()
        sid = f"s_auto2_{uuid.uuid4().hex[:8]}"
        cid = f"c_auto2_{uuid.uuid4().hex[:10]}"
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=cid,
            cart_value=637.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid,
        )
        db.session.add(ac)
        db.session.commit()
        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 640.0,
                "items_count": 1,
                "cart": [{"price": 640.0, "quantity": 1}],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        mock_send.assert_not_called()

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
                "event": "cart_state_sync",
                "reason": "clear",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 0,
                "items_count": 0,
                "cart": [],
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        db.session.refresh(ac)
        self.assertFalse(bool(ac.vip_mode))
        self.assertEqual((ac.status or "").strip(), "cleared")
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

    def test_vip_priority_customer_phone_from_cart_recovery_reason(self) -> None:
        """رقم العميل في لوحة VIP يُحمّل من ‎CartRecoveryReason.customer_phone‎ لمطابقة الجلسة."""
        db.create_all()
        main._ensure_store_widget_schema()
        slug = f"vsync_crph_{uuid.uuid4().hex[:10]}"
        store = Store(
            zid_store_id=slug,
            vip_cart_threshold=100,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(store)
        db.session.commit()
        sid_us = f"s_crph_{uuid.uuid4().hex[:8]}"
        cid = f"c_crph_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        crr = CartRecoveryReason(
            store_slug=slug,
            session_id=sid_us,
            reason="other",
            customer_phone="0591112233",
            source="legacy_api",
            created_at=now,
            updated_at=now,
        )
        db.session.add(crr)
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=cid,
            cart_value=500.0,
            status="abandoned",
            vip_mode=True,
            recovery_session_id=sid_us,
        )
        db.session.add(ac)
        db.session.commit()
        dash = main._dashboard_recovery_store_row()
        self.assertIsNotNone(dash)
        self.assertEqual(int(dash.id), int(store.id))
        lst = main._vip_priority_cart_alert_list()
        row = next((x for x in lst if int(x["id"]) == int(ac.id)), None)
        self.assertIsNotNone(row)
        self.assertEqual(row.get("customer_wa_phone"), "966591112233")


if __name__ == "__main__":
    unittest.main()
