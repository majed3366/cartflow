# -*- coding: utf-8 -*-
"""ردود واتساب الإيجابية → ‎MerchantFollowupAction‎."""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import AbandonedCart, MerchantFollowupAction, Store


class WhatsappInboundPositiveReplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def test_positive_reply_creates_merchant_followup(self) -> None:
        db.create_all()
        uid = uuid.uuid4().hex[:10]
        store = Store(zid_store_id=f"z_wa_in_{uid}")
        db.session.add(store)
        db.session.commit()
        ph = "966512345678"
        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"zcart_wa_{uid}",
            customer_phone=ph,
            cart_value=120.5,
            status="abandoned",
            vip_mode=False,
            recovery_session_id=f"rs_{uid}",
        )
        db.session.add(ac)
        db.session.commit()

        count_before = (
            db.session.query(MerchantFollowupAction)
            .filter(MerchantFollowupAction.customer_phone == ph)
            .count()
        )
        self.assertEqual(count_before, 0)

        r = self.client.post(
            "/webhook/whatsapp",
            data={
                "Body": "نعم",
                "From": "whatsapp:+966512345678",
            },
        )
        self.assertEqual(r.status_code, 200)
        db.session.expire_all()
        row = (
            db.session.query(MerchantFollowupAction)
            .filter(MerchantFollowupAction.customer_phone == ph)
            .first()
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.status, "needs_merchant_followup")
        self.assertEqual(row.reason, "customer_replied_yes")
        self.assertEqual(int(row.abandoned_cart_id or 0), int(ac.id))

    def test_negative_reply_skips_followup_insert(self) -> None:
        db.create_all()
        uid = uuid.uuid4().hex[:10]
        ph = "9665999888777"
        r = self.client.post(
            "/webhook/whatsapp",
            data={
                "Body": "لا شكراً",
                "From": f"whatsapp:+{ph}",
            },
        )
        self.assertEqual(r.status_code, 200)
        n = (
            db.session.query(MerchantFollowupAction)
            .filter(MerchantFollowupAction.customer_phone == ph)
            .count()
        )
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
