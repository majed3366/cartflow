# -*- coding: utf-8 -*-
"""E2E: merchant test-widget must scope recoveries to authenticated store slug."""
from __future__ import annotations

import os
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, MerchantUser, Store
from schema_merchant_auth import ensure_merchant_auth_schema, reset_merchant_auth_schema_guard_for_tests
from services.merchant_activation_v1 import resolve_activation_demo_for_request
from services.merchant_test_widget_store_v1 import coerce_cart_event_store_slug


class MerchantTestWidgetStoreScopeE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        reset_merchant_auth_schema_guard_for_tests()

    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-merchant-widget-scope"
        self._suffix = uuid.uuid4().hex[:10]
        self.client = TestClient(app)
        db.create_all()
        ensure_merchant_auth_schema(db)

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"mwt-{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(MerchantUser).filter(
                MerchantUser.email.like(f"%{self._suffix}%@example.com")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _signup_merchant(self) -> tuple[TestClient, str, dict]:
        email = f"mwt-{self._suffix}@example.com"
        r = self.client.post(
            "/signup",
            data={
                "store_name": f"MWT Store {self._suffix}",
                "email": email,
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303, r.text[:400])
        cookies = dict(r.cookies)
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).first()
        self.assertIsNotNone(user)
        st = (
            db.session.query(Store)
            .filter(Store.merchant_user_id == int(user.id))
            .first()
        )
        self.assertIsNotNone(st)
        slug = (st.zid_store_id or "").strip()
        return self.client, slug, cookies

    def _merchant_slug_from_cookies(self, cookies: dict) -> str:
        user = None
        from services.merchant_auth_v1 import merchant_id_from_request_cookies

        mid = merchant_id_from_request_cookies(cookies)
        if mid:
            user = db.session.query(MerchantUser).filter(MerchantUser.id == int(mid)).first()
        self.assertIsNotNone(user)
        st = (
            db.session.query(Store)
            .filter(Store.merchant_user_id == int(user.id))
            .order_by(Store.id.desc())
            .first()
        )
        self.assertIsNotNone(st)
        return (st.zid_store_id or "").strip()

    def test_test_widget_redirect_scopes_demo_store(self) -> None:
        client, _slug, cookies = self._signup_merchant()
        slug = self._merchant_slug_from_cookies(cookies)
        tw = client.get("/dashboard/test-widget", cookies=cookies, follow_redirects=False)
        self.assertEqual(tw.status_code, 302)
        loc = tw.headers.get("location", "")
        self.assertIn("store_slug=", loc)
        self.assertIn(slug, loc)
        self.assertIn("merchant_activation=1", loc)

        page = client.get(loc, cookies=cookies)
        self.assertEqual(page.status_code, 200, page.text[:300])
        self.assertIn(f'CARTFLOW_STORE_SLUG = "{slug}"', page.text)
        self.assertIn(f'data-store="{slug}"', page.text)

    def test_cart_event_coerces_demo_slug_when_merchant_logged_in(self) -> None:
        client, _slug, cookies = self._signup_merchant()
        slug = self._merchant_slug_from_cookies(cookies)
        sid = f"sess-{self._suffix}"
        cid = f"cf_cart_{self._suffix}"
        r = client.post(
            "/api/cart-event",
            json={
                "event": "cart_state_sync",
                "reason": "add",
                "store": "demo",
                "session_id": sid,
                "cart_id": cid,
                "cart_total": 150.0,
                "items_count": 1,
            },
            cookies=cookies,
        )
        self.assertEqual(r.status_code, 200, r.text)
        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == cid)
            .first()
        )
        self.assertIsNotNone(ac)
        st = db.session.query(Store).filter(Store.id == int(ac.store_id)).first()
        self.assertEqual((st.zid_store_id or "").strip(), slug)

    def test_activation_demo_never_demo_when_merchant_activation_flag(self) -> None:
        _client, _slug, cookies = self._signup_merchant()
        slug = self._merchant_slug_from_cookies(cookies)
        req = type(
            "Req",
            (),
            {
                "query_params": {
                    "merchant_activation": "1",
                    "reset_demo": "1",
                },
                "cookies": cookies,
            },
        )()
        act = resolve_activation_demo_for_request(req, cookies=cookies)
        self.assertEqual(act.widget_store_slug, slug)
        self.assertFalse(act.widget_store_slug == "demo")
        self.assertTrue(act.is_merchant_activation)

    def test_coerce_cart_event_store_slug_unit(self) -> None:
        from services.merchant_auth_context import (
            reset_merchant_auth_store_slug,
            set_merchant_auth_store_slug,
        )

        tok = set_merchant_auth_store_slug(f"mwt-{self._suffix}")
        try:
            self.assertEqual(
                coerce_cart_event_store_slug("demo"),
                f"mwt-{self._suffix}",
            )
        finally:
            reset_merchant_auth_store_slug(tok)


if __name__ == "__main__":
    unittest.main()
