# -*- coding: utf-8 -*-
"""E2E: dashboard messages/carts resolve sent recoveries by recovery_key."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

import models  # noqa: F401

from extensions import db

from main import (  # noqa: E402
    _api_json_dashboard_normal_carts,
    _merchant_recovery_message_history_rows,
    app,
)
from models import AbandonedCart, CartRecoveryLog, Store  # noqa: E402
from schema_recovery_message_context import ensure_recovery_message_context_schema  # noqa: E402
from services.merchant_cart_row_classifier import PRIMARY_SENT  # noqa: E402
from services.merchant_dashboard_recovery_resolve_v1 import (  # noqa: E402
    find_dashboard_cart_row,
    find_dashboard_message_row,
)


class MerchantDashboardRecoveryResolveE2ETests(unittest.TestCase):
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
                Store.zid_store_id.like(f"demo-{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _seed_sent_case(
        self,
        *,
        message: str = "اختبارالسعر123",
        sent_at: datetime | None = None,
    ) -> tuple[Store, AbandonedCart, CartRecoveryLog, str]:
        slug = f"demo-{self._suffix}"
        sid = f"s_{self._suffix}"
        zid = f"cf_cart_{self._suffix}"
        rk = f"{slug}:{sid}"
        now = sent_at or datetime.now(timezone.utc)
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
            cart_value=88.0,
            last_seen_at=now - timedelta(days=30),
        )
        db.session.add(ac)
        db.session.flush()
        lg = CartRecoveryLog(
            store_slug=slug,
            session_id=sid,
            cart_id=zid,
            phone="966501112233",
            message=message,
            status="mock_sent",
            step=1,
            recovery_key=rk,
            reason_tag="price",
            context_status="ok",
            sent_at=now,
            created_at=now,
        )
        db.session.add(lg)
        db.session.commit()
        return st, ac, lg, rk

    def test_messages_and_carts_find_sent_by_recovery_key(self) -> None:
        st, ac, lg, rk = self._seed_sent_case(message="اختبارالسعر123")
        with patch("main._dashboard_recovery_store_row", return_value=st):
            msgs = _merchant_recovery_message_history_rows(st, limit=80)
            carts_body, _ = _api_json_dashboard_normal_carts(st)
            trace = self._client.get(f"/api/debug/recovery-trace?recovery_key={rk}")

        msg_row = find_dashboard_message_row(
            msgs,
            recovery_key=rk,
            cart_id=ac.zid_cart_id,
            session_id=ac.recovery_session_id,
            log_id=int(lg.id),
        )
        self.assertIsNotNone(msg_row, msg=f"messages rows={len(msgs)}")
        self.assertIn("اختبارالسعر123", msg_row.get("preview_ar") or "")

        cart_row = find_dashboard_cart_row(
            carts_body.get("merchant_carts_page_rows") or [],
            recovery_key=rk,
            cart_id=ac.zid_cart_id,
            session_id=ac.recovery_session_id,
        )
        self.assertIsNotNone(cart_row, msg="cart row missing from normal-carts")
        self.assertEqual(cart_row.get("recovery_key"), rk)
        self.assertEqual(
            cart_row.get("merchant_cart_primary_bucket"),
            PRIMARY_SENT,
        )

        self.assertEqual(trace.status_code, 200, msg=trace.text)
        js = trace.json()
        self.assertTrue(js.get("ok"), msg=js)
        self.assertEqual(js.get("log_id"), int(lg.id))
        self.assertEqual(js.get("recovery_key"), rk)
        self.assertEqual(js.get("cart_id"), ac.zid_cart_id)
        self.assertIn("اختبارالسعر123", js.get("persisted_log_body") or "")
        self.assertIn("اختبارالسعر123", js.get("dashboard_message_body") or "")
        self.assertEqual(js.get("cart_classifier_bucket"), PRIMARY_SENT)
        self.assertIsNone(js.get("divergence_layer"))

    def test_stale_sent_cart_still_resolves_when_outside_last_seen_window(self) -> None:
        """Sent log + old last_seen: augment/scope must still surface cart as sent."""
        st, ac, lg, rk = self._seed_sent_case(
            message="وفرنا لك خيار بنفس الفكرة",
            sent_at=datetime.now(timezone.utc),
        )
        now = datetime.now(timezone.utc)
        for i in range(100):
            db.session.add(
                AbandonedCart(
                    store_id=int(st.id),
                    zid_cart_id=f"cf_cart_filler_{self._suffix}_{i}",
                    recovery_session_id=f"sess_filler_{self._suffix}_{i}",
                    status="abandoned",
                    vip_mode=False,
                    cart_value=10.0 + i,
                    last_seen_at=now - timedelta(minutes=i),
                )
            )
        db.session.commit()

        with patch("main._dashboard_recovery_store_row", return_value=st):
            carts_body, _ = _api_json_dashboard_normal_carts(st)

        cart_row = find_dashboard_cart_row(
            carts_body.get("merchant_carts_page_rows") or [],
            recovery_key=rk,
            cart_id=ac.zid_cart_id,
        )
        self.assertIsNotNone(cart_row, msg="sent cart missing despite stale last_seen")
        self.assertEqual(cart_row.get("merchant_cart_primary_bucket"), PRIMARY_SENT)


if __name__ == "__main__":
    unittest.main()
