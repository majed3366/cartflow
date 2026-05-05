# -*- coding: utf-8 -*-
"""لوحة متابعة التاجر بعد رد إيجابي على واتساب — قراءة و‎ complete‎ يدوي."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import MerchantFollowupAction, Store
from services.whatsapp_positive_reply import (
    STATUS_MERCHANT_FOLLOWUP_COMPLETED,
    STATUS_NEEDS_MERCHANT_FOLLOWUP,
)


class MerchantFollowupActionsApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def test_get_lists_needs_merchant_followup_scoped_to_latest_store(self) -> None:
        db.create_all()
        uid = uuid.uuid4().hex[:10]
        store_latest = Store(zid_store_id=f"z_mf_latest_{uid}")
        store_old = Store(zid_store_id=f"z_mf_old_{uid}")
        db.session.add_all([store_old, store_latest])
        db.session.commit()

        other = MerchantFollowupAction(
            store_id=store_old.id,
            abandoned_cart_id=None,
            customer_phone="966511111111",
            status=STATUS_NEEDS_MERCHANT_FOLLOWUP,
            reason="customer_replied_yes",
            inbound_message="نعم",
        )
        mine = MerchantFollowupAction(
            store_id=store_latest.id,
            abandoned_cart_id=None,
            customer_phone="966522222222",
            status=STATUS_NEEDS_MERCHANT_FOLLOWUP,
            reason="customer_replied_yes",
            inbound_message="ايه",
        )
        db.session.add_all([other, mine])
        db.session.commit()

        r = self.client.get("/api/merchant-followup-actions")
        self.assertEqual(r.status_code, 200, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        phones = {a.get("customer_phone") for a in (j.get("actions") or [])}
        self.assertIn("966522222222", phones)
        self.assertNotIn("966511111111", phones)

    def test_post_complete_updates_status(self) -> None:
        db.create_all()
        uid = uuid.uuid4().hex[:10]
        store = Store(zid_store_id=f"z_mf_done_{uid}")
        db.session.add(store)
        db.session.commit()

        row = MerchantFollowupAction(
            store_id=store.id,
            abandoned_cart_id=None,
            customer_phone="966533333333",
            status=STATUS_NEEDS_MERCHANT_FOLLOWUP,
            reason="customer_replied_yes",
            inbound_message="نعم",
        )
        db.session.add(row)
        db.session.commit()
        aid = int(row.id)

        r_done = self.client.post(
            f"/api/merchant-followup-actions/{aid}/complete",
            json={},
        )
        self.assertEqual(r_done.status_code, 200, r_done.text)
        self.assertTrue(r_done.json().get("ok"))

        db.session.expire_all()
        again = db.session.get(MerchantFollowupAction, aid)
        self.assertIsNotNone(again)
        assert again is not None
        self.assertEqual(again.status, STATUS_MERCHANT_FOLLOWUP_COMPLETED)

        r_list = self.client.get("/api/merchant-followup-actions")
        phones = {a.get("customer_phone") for a in (r_list.json().get("actions") or [])}
        self.assertNotIn("966533333333", phones)

    def test_vip_dashboard_includes_followup_section_heading(self) -> None:
        db.create_all()
        uid = uuid.uuid4().hex[:10]
        store = Store(zid_store_id=f"z_mf_html_{uid}")
        db.session.add(store)
        db.session.commit()
        row = MerchantFollowupAction(
            store_id=store.id,
            abandoned_cart_id=None,
            customer_phone="966544444444",
            status=STATUS_NEEDS_MERCHANT_FOLLOWUP,
            reason="customer_replied_yes",
            inbound_message="نعم",
        )
        db.session.add(row)
        db.session.commit()

        r = self.client.get("/dashboard/vip-cart-settings")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("عملاء يحتاجون متابعة الآن", r.text)
        self.assertIn("تواصل عبر واتساب", r.text)
        self.assertIn("تمت المتابعة", r.text)
        self.assertIn("966544444444", r.text)


if __name__ == "__main__":
    unittest.main()
