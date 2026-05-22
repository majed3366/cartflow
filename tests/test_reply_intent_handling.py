# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from fastapi.testclient import TestClient

from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.lifecycle_intelligence import DECISION_FALLBACK, DECISION_HANDOFF, DECISION_STOP
from services.reply_intent_handling import (
    INTENT_DELIVERY,
    INTENT_PRICE,
    INTENT_PURCHASE,
    INTENT_STOP,
    INTENT_UNKNOWN,
    classify_reply_lifecycle_intent_v1,
    handle_customer_reply_lifecycle_intent_v1,
    lifecycle_decision_for_reply_intent,
)


class ReplyIntentClassificationTests(unittest.TestCase):
    def test_tam_altalib_purchase(self) -> None:
        self.assertEqual(classify_reply_lifecycle_intent_v1("تم الطلب"), INTENT_PURCHASE)
        d, a = lifecycle_decision_for_reply_intent(INTENT_PURCHASE)
        self.assertEqual(d, DECISION_STOP)
        self.assertEqual(a, "close_lifecycle")

    def test_la_oreed_stop(self) -> None:
        self.assertEqual(classify_reply_lifecycle_intent_v1("لا أريد"), INTENT_STOP)
        d, a = lifecycle_decision_for_reply_intent(INTENT_STOP)
        self.assertEqual(d, DECISION_STOP)
        self.assertEqual(a, "stop_recovery")

    def test_ghali_price_handoff(self) -> None:
        self.assertEqual(classify_reply_lifecycle_intent_v1("غالي"), INTENT_PRICE)
        d, a = lifecycle_decision_for_reply_intent(INTENT_PRICE)
        self.assertEqual(d, DECISION_HANDOFF)
        self.assertEqual(a, "handoff_later")

    def test_delivery_handoff(self) -> None:
        self.assertEqual(
            classify_reply_lifecycle_intent_v1("متى التوصيل؟"), INTENT_DELIVERY
        )
        d, a = lifecycle_decision_for_reply_intent(INTENT_DELIVERY)
        self.assertEqual(d, DECISION_HANDOFF)
        self.assertEqual(a, "handoff_later")

    def test_unknown_fallback(self) -> None:
        self.assertEqual(
            classify_reply_lifecycle_intent_v1("مرحبا كيف الحال"), INTENT_UNKNOWN
        )
        d, a = lifecycle_decision_for_reply_intent(INTENT_UNKNOWN)
        self.assertEqual(d, DECISION_FALLBACK)
        self.assertEqual(a, "fallback")


class ReplyIntentLogFormatTests(unittest.TestCase):
    def test_log_block_matches_required_shape(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            handle_customer_reply_lifecycle_intent_v1(
                "غالي",
                session_id="sess-ghali",
                cart_id="cart-1",
            )
        out = buf.getvalue()
        self.assertIn("[REPLY INTENT]", out)
        self.assertIn('reply="غالي"', out)
        self.assertIn("intent=PRICE", out)
        self.assertIn("decision=HANDOFF", out)
        self.assertIn("action=handoff_later", out)


class ReplyIntentWebhookIntegrationTests(unittest.TestCase):
    """Real inbound webhook path emits [REPLY INTENT] before behavioral store."""

    def setUp(self) -> None:
        import os

        os.environ.setdefault("CARTFLOW_CONTINUATION_AUTO_REPLY", "0")
        import main

        self.client = TestClient(main.app)
        st = (
            db.session.query(Store).filter(Store.zid_store_id == "demo").first()
            or Store(zid_store_id="demo", recovery_delay=1, recovery_delay_unit="minutes")
        )
        if st.id is None:
            db.session.add(st)
            db.session.flush()
        self.store = st
        self.slug = (st.zid_store_id or "demo").strip()[:255]
        self.sid = "rih-webhook-sess"
        self.cid = "rih-webhook-cart"
        self.phone = "966501239999"
        db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.session_id == self.sid
        ).delete(synchronize_session=False)
        db.session.query(AbandonedCart).filter(
            AbandonedCart.zid_cart_id == self.cid
        ).delete(synchronize_session=False)
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=self.cid,
            recovery_session_id=self.sid,
            customer_phone=f"+{self.phone}",
            cart_value=99.0,
            status="abandoned",
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.add(
            CartRecoveryLog(
                store_slug=self.slug,
                session_id=self.sid,
                cart_id=self.cid,
                phone=self.phone,
                message="recovery sent",
                status="sent_real",
                step=1,
            )
        )
        db.session.commit()

    def test_webhook_ghali_emits_reply_intent_chain(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            r = self.client.post(
                "/webhook/whatsapp",
                data={"Body": "غالي", "From": f"whatsapp:+{self.phone}"},
            )
        self.assertEqual(r.status_code, 200)
        out = buf.getvalue()
        self.assertIn("[REPLY INTENT]", out)
        self.assertIn("intent=PRICE", out)
        self.assertIn("decision=HANDOFF", out)

    def test_webhook_tam_altalib_purchase_close_lifecycle(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            r = self.client.post(
                "/webhook/whatsapp",
                data={"Body": "تم الطلب", "From": f"whatsapp:+{self.phone}"},
            )
        self.assertEqual(r.status_code, 200)
        out = buf.getvalue()
        self.assertIn("intent=PURCHASE", out)
        self.assertIn("decision=STOP", out)
        self.assertIn("action=close_lifecycle", out)


if __name__ == "__main__":
    unittest.main()
