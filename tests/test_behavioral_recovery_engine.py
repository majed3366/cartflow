# -*- coding: utf-8 -*-
"""Behavioral recovery engine — incrementally layered on existing normal recovery."""
from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, Store


def _ensure_demo_store() -> Store:
    db.create_all()
    row = db.session.query(Store).order_by(Store.id.desc()).first()
    if row is not None:
        return row
    st = Store(zid_store_id="demo", recovery_attempts=2)
    db.session.add(st)
    db.session.commit()
    return st


class BehavioralRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        db.create_all()
        self._prev_base = os.environ.get("CARTFLOW_PUBLIC_BASE_URL")
        os.environ["CARTFLOW_PUBLIC_BASE_URL"] = "https://cartflow.test"

    def tearDown(self) -> None:
        if self._prev_base is None:
            os.environ.pop("CARTFLOW_PUBLIC_BASE_URL", None)
        else:
            os.environ["CARTFLOW_PUBLIC_BASE_URL"] = self._prev_base

    def test_customer_whatsapp_reply_sets_behavioral_and_blocks_followup(self) -> None:
        st = _ensure_demo_store()
        slug = (st.zid_store_id or "demo").strip()[:255]
        sid = "beh-session-reply-1"
        cid = "beh-cart-reply-1"
        db.session.query(CartRecoveryLog).filter(CartRecoveryLog.session_id == sid).delete(
            synchronize_session=False
        )
        db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).delete(
            synchronize_session=False
        )
        db.session.commit()
        ac = AbandonedCart(
            store_id=st.id,
            zid_cart_id=cid,
            recovery_session_id=sid,
            customer_phone="+966501234567",
            cart_value=120.0,
            status="abandoned",
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.commit()
        log_row = CartRecoveryLog(
            store_slug=slug,
            session_id=sid,
            cart_id=cid,
            phone="966501234567",
            message="first recovery",
            status="sent_real",
            step=1,
        )
        db.session.add(log_row)
        db.session.commit()

        from services.behavioral_recovery.state_store import (
            behavioral_dict_for_abandoned_cart,
        )

        with self.client as c:
            r = c.post(
                "/webhook/whatsapp",
                data={"Body": "أي استفسار بسيط", "From": "whatsapp:+966501234567"},
            )
        self.assertEqual(r.status_code, 200)
        db.session.expire_all()
        ac2 = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        self.assertIsNotNone(ac2)
        b = behavioral_dict_for_abandoned_cart(ac2)
        self.assertTrue(b.get("customer_replied"))
        self.assertEqual(b.get("recovery_conversation_state"), "engaged")
        self.assertTrue(str(b.get("last_customer_reply_preview") or ""))

        from main import _normal_recovery_positive_reply_blocks_followup

        self.assertTrue(
            _normal_recovery_positive_reply_blocks_followup(
                session_id=sid, cart_id=cid
            )
        )

    def test_recovery_link_click_marks_payload(self) -> None:
        st = _ensure_demo_store()
        sid = "beh-session-click-1"
        cid = "beh-cart-click-1"
        db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).delete(
            synchronize_session=False
        )
        db.session.commit()
        ac = AbandonedCart(
            store_id=st.id,
            zid_cart_id=cid,
            recovery_session_id=sid,
            customer_phone="+966501234567",
            cart_url="https://example.test/cart",
            cart_value=50.0,
            status="abandoned",
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.commit()

        from services.behavioral_recovery.link_tracking import sign_recovery_click_token
        from services.behavioral_recovery.state_store import behavioral_dict_for_abandoned_cart

        tok = sign_recovery_click_token(cid, sid)
        r = self.client.get(f"/api/recover/r?t={tok}", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("example.test", r.headers.get("location", ""))
        db.session.expire_all()
        ac2 = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        b = behavioral_dict_for_abandoned_cart(ac2)
        self.assertTrue(b.get("recovery_link_clicked"))

    def test_user_return_merges_behavioral(self) -> None:
        st = _ensure_demo_store()
        slug = (st.zid_store_id or "demo").strip()
        sid = "beh-session-ret-1"
        cid = "beh-cart-ret-1"
        db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).delete(
            synchronize_session=False
        )
        db.session.commit()
        ac = AbandonedCart(
            store_id=st.id,
            zid_cart_id=cid,
            recovery_session_id=sid,
            cart_value=80.0,
            status="abandoned",
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.commit()

        from services.behavioral_recovery.state_store import behavioral_dict_for_abandoned_cart

        r = self.client.post(
            "/api/cart-event",
            json={
                "event": "page_view",
                "store": slug,
                "session_id": sid,
                "cart_id": cid,
                "user_returned_to_site": True,
            },
        )
        self.assertEqual(r.status_code, 200)
        db.session.expire_all()
        ac2 = db.session.query(AbandonedCart).filter_by(zid_cart_id=cid).first()
        b = behavioral_dict_for_abandoned_cart(ac2)
        self.assertTrue(b.get("user_returned_to_site"))


if __name__ == "__main__":
    unittest.main()
