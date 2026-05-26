# -*- coding: utf-8 -*-
"""E2E: cart-presence debug traces normal-carts inclusion stages."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

import models  # noqa: F401

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, Store
from schema_recovery_message_context import ensure_recovery_message_context_schema
from services.recovery_message_context_v1 import (
    CONTEXT_OK,
    build_recovery_message_context,
    serialize_context_json,
)


class MerchantCartPresenceTraceE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_recovery_message_context_schema(db)

    def setUp(self) -> None:
        db.create_all()
        ensure_recovery_message_context_schema(db)
        self._suffix = uuid.uuid4().hex[:10]
        self._client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"cpres-{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _seed_old_cart_sent_recovery(self) -> tuple[Store, str]:
        slug = f"cpres-{self._suffix}"
        sid = f"sess-{self._suffix}"
        zid = f"cf_cart_{self._suffix}"
        now = datetime.now(timezone.utc)
        st = Store(
            zid_store_id=slug,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            cartflow_widget_enabled=True,
            whatsapp_recovery_enabled=True,
        )
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            customer_phone="966501112233",
            status="abandoned",
            vip_mode=False,
            cart_value=50.0,
            last_seen_at=now - timedelta(days=120),
        )
        db.session.add(ac)
        db.session.flush()
        ctx = build_recovery_message_context(
            recovery_key=f"{slug}:{sid}",
            store_slug=slug,
            session_id=sid,
            cart_id=zid,
            customer_phone="966501112233",
            message_body="presence trace body",
            message_type="reason_template",
            attempt=1,
            send_status="mock_sent",
            sent_at=now,
            source="e2e_test",
            store=st,
            abandoned_cart=ac,
        )
        self.assertEqual(ctx.context_status, CONTEXT_OK)
        lg = CartRecoveryLog(
            store_slug=slug,
            session_id=sid,
            cart_id=zid,
            recovery_key=ctx.recovery_key,
            status="mock_sent",
            message=ctx.message_body,
            context_status=ctx.context_status,
            context_json=serialize_context_json(ctx),
            sent_at=now,
            created_at=now,
        )
        db.session.add(lg)
        db.session.commit()
        return st, ctx.recovery_key

    def test_cart_presence_endpoint_flags_stages(self) -> None:
        st, rk = self._seed_old_cart_sent_recovery()
        with patch("main._dashboard_recovery_store_row", return_value=st):
            resp = self._client.get(f"/api/debug/cart-presence?recovery_key={rk}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        for key in (
            "candidate",
            "augmented",
            "grouped",
            "picked",
            "classified",
            "returned_in_api",
            "exclusion_stage",
        ):
            self.assertIn(key, data)
        self.assertTrue(data.get("grouped"))
        self.assertIn(data.get("exclusion_stage"), ("included", "page_slice", "pick", "lifecycle", "loop_cap", "classify"))


if __name__ == "__main__":
    unittest.main()
