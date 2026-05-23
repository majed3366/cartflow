# -*- coding: utf-8 -*-
"""Merchant auth foundation v1."""
from __future__ import annotations

import os
import unittest
import uuid
from unittest import mock

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import MerchantUser, Store
from schema_merchant_auth import reset_merchant_auth_schema_guard_for_tests
from services.merchant_auth_http import merchant_cookie_name
from services.merchant_auth_v1 import (
    hash_password,
    register_merchant_account,
    request_password_reset,
    verify_password,
)


class MerchantAuthV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_env = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-merchant-auth-secret"
        reset_merchant_auth_schema_guard_for_tests()
        self.client = TestClient(app)
        db.create_all()
        from schema_merchant_auth import ensure_merchant_auth_schema

        ensure_merchant_auth_schema(db)

    def tearDown(self) -> None:
        if self._prev_env is None:
            os.environ.pop("ENV", None)
        else:
            os.environ["ENV"] = self._prev_env
        db.session.remove()

    def test_password_hash_roundtrip(self) -> None:
        h = hash_password("secret-pass-12")
        self.assertTrue(verify_password("secret-pass-12", h))
        self.assertFalse(verify_password("wrong", h))

    def test_signup_login_dashboard_logout_flow(self) -> None:
        email = f"merchant-auth-{uuid.uuid4().hex}@example.com"
        r = self.client.post(
            "/signup",
            data={
                "merchant_name": "تاجر تجريبي",
                "store_name": "متجر الاختبار",
                "email": email,
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303, r.text[:300])
        self.assertIn(merchant_cookie_name(), r.cookies)

        dash = self.client.get("/dashboard", cookies=r.cookies)
        self.assertEqual(dash.status_code, 200)
        self.assertIn("data-cf-merchant-app", dash.text.lower())

        out = self.client.get("/logout", cookies=r.cookies, follow_redirects=False)
        self.assertEqual(out.status_code, 303)

        os.environ["ENV"] = "production"
        anon = TestClient(app)
        blocked = anon.get("/dashboard", follow_redirects=False)
        self.assertEqual(blocked.status_code, 302)
        self.assertIn("/login", blocked.headers.get("location", ""))

    def test_production_requires_auth_for_dashboard(self) -> None:
        os.environ["ENV"] = "production"
        anon = TestClient(app)
        r = anon.get("/dashboard", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers.get("location", ""))

    def test_widget_api_not_protected(self) -> None:
        os.environ["ENV"] = "production"
        r = self.client.get("/api/cartflow/widget-runtime-config?store_slug=demo")
        self.assertNotEqual(r.status_code, 302)

    def test_password_reset_dev_token_flow(self) -> None:
        reset_email = f"reset-flow-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            merchant_name="Reset User",
            store_name="Reset Store",
            email=reset_email,
            password="password123",
        )
        self.assertTrue(ok, msg="register_merchant_account failed")
        self.assertIsNotNone(user)
        with mock.patch(
            "services.merchant_auth_v1.is_development_env", return_value=True
        ):
            msg, dev_url = request_password_reset(reset_email)
        self.assertIn("إذا كان البريد", msg)
        self.assertTrue(dev_url and "token=" in dev_url)
        token = dev_url.split("token=", 1)[1]
        page = self.client.get(f"/reset-password?token={token}")
        self.assertEqual(page.status_code, 200)
        post = self.client.post(
            "/reset-password",
            data={
                "token": token,
                "password": "newpassword99",
                "confirm_password": "newpassword99",
            },
            follow_redirects=False,
        )
        self.assertEqual(post.status_code, 303)
        u = db.session.query(MerchantUser).filter(MerchantUser.email == reset_email).first()
        self.assertIsNotNone(u)
        assert u is not None
        self.assertTrue(verify_password("newpassword99", u.password_hash))

    def test_signup_creates_store_link(self) -> None:
        link_email = f"store-link-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            merchant_name="Store Link",
            store_name="متجر الربط",
            email=link_email,
            password="password123",
        )
        self.assertTrue(ok, msg="register_merchant_account failed")
        assert user is not None
        store = db.session.query(Store).filter(Store.merchant_user_id == user.id).first()
        self.assertIsNotNone(store)
        assert store is not None
        self.assertTrue(store.zid_store_id)
        self.assertEqual(user.primary_store_id, store.id)


if __name__ == "__main__":
    unittest.main()
