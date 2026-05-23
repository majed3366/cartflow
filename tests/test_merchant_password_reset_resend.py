# -*- coding: utf-8 -*-
"""Resend password reset delivery for merchant auth."""
from __future__ import annotations

import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import MerchantPasswordResetToken, MerchantUser
from schema_merchant_auth import reset_merchant_auth_schema_guard_for_tests
from services.merchant_auth_v1 import (
    _hash_reset_token,
    apply_password_reset,
    authenticate_merchant,
    register_merchant_account,
    request_password_reset,
    reset_token_is_valid,
    verify_password,
)
from services.merchant_password_reset_email import (
    build_password_reset_link,
    deliver_password_reset_email,
)


class MerchantPasswordResetResendTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_env = os.environ.get("ENV")
        self._prev_resend = os.environ.get("RESEND_API_KEY")
        self._prev_from = os.environ.get("RESEND_FROM_EMAIL")
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-merchant-auth-secret"
        os.environ.pop("RESEND_API_KEY", None)
        os.environ.pop("RESEND_FROM_EMAIL", None)
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
        if self._prev_resend is None:
            os.environ.pop("RESEND_API_KEY", None)
        else:
            os.environ["RESEND_API_KEY"] = self._prev_resend
        if self._prev_from is None:
            os.environ.pop("RESEND_FROM_EMAIL", None)
        else:
            os.environ["RESEND_FROM_EMAIL"] = self._prev_from
        db.session.remove()

    def test_dev_fallback_without_resend_key(self) -> None:
        email = f"reset-dev-{uuid.uuid4().hex}@example.com"
        register_merchant_account(
            store_name="Dev Store",
            email=email,
            password="password123",
        )
        msg, dev_url = request_password_reset(
            email, reset_base_url="https://app.cartflow.test"
        )
        self.assertIn("إذا كان البريد", msg)
        self.assertTrue(dev_url and dev_url.startswith("/reset-password?token="))

    @mock.patch("services.merchant_password_reset_email.requests.post")
    def test_resend_called_in_production(self, mock_post: mock.MagicMock) -> None:
        os.environ["ENV"] = "production"
        os.environ["RESEND_API_KEY"] = "re_test_key"
        os.environ["RESEND_FROM_EMAIL"] = "CartFlow <auth@example.com>"
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"id":"email_1"}'
        mock_post.return_value = mock_resp

        email = f"reset-prod-{uuid.uuid4().hex}@example.com"
        register_merchant_account(
            store_name="Prod Store",
            email=email,
            password="password123",
        )
        msg, dev_url = request_password_reset(
            email, reset_base_url="https://app.cartflow.test"
        )
        self.assertIn("إذا كان البريد", msg)
        self.assertIsNone(dev_url)
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["to"], [email])
        self.assertEqual(payload["subject"], "استعادة كلمة المرور — CartFlow")
        self.assertIn("https://app.cartflow.test/reset-password?token=", payload["text"])

    def test_expired_token_invalid(self) -> None:
        email = f"expired-{uuid.uuid4().hex}@example.com"
        register_merchant_account(
            store_name="Exp",
            email=email,
            password="password123",
        )
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).first()
        self.assertIsNotNone(user)
        assert user is not None
        raw = "expired-test-token-value"
        row = MerchantPasswordResetToken(
            merchant_user_id=user.id,
            token_hash=_hash_reset_token(raw),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.session.add(row)
        db.session.commit()
        self.assertFalse(reset_token_is_valid(raw))

    def test_used_token_invalid(self) -> None:
        email = f"used-{uuid.uuid4().hex}@example.com"
        register_merchant_account(
            store_name="Used",
            email=email,
            password="password123",
        )
        msg, dev_url = request_password_reset(email, reset_base_url="")
        self.assertIsNotNone(dev_url)
        token = dev_url.split("token=", 1)[1]
        ok, _ = apply_password_reset(token=token, password="newpassword99")
        self.assertTrue(ok)
        self.assertFalse(reset_token_is_valid(token))

    def test_full_reset_login_flow(self) -> None:
        email = f"flow-{uuid.uuid4().hex}@example.com"
        register_merchant_account(
            store_name="Flow Store",
            email=email,
            password="oldpassword1",
        )
        _, dev_url = request_password_reset(email, reset_base_url="")
        assert dev_url is not None
        token = dev_url.split("token=", 1)[1]
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
        self.assertIn("password_reset=1", post.headers.get("location", ""))

        login_page = self.client.get("/login?password_reset=1")
        self.assertIn("تم تحديث كلمة المرور بنجاح", login_page.text)

        self.assertIsNone(authenticate_merchant(email, "oldpassword1"))
        self.assertIsNotNone(authenticate_merchant(email, "newpassword99"))

    def test_build_password_reset_link_absolute(self) -> None:
        link = build_password_reset_link("abc", base_url="https://host.example")
        self.assertEqual(link, "https://host.example/reset-password?token=abc")

    def test_deliver_logs_on_dev_without_key(self) -> None:
        sent, dev_path = deliver_password_reset_email(
            to_email="x@example.com",
            reset_link="https://host.example/reset-password?token=tok",
        )
        self.assertFalse(sent)
        self.assertEqual(dev_path, "/reset-password?token=tok")


if __name__ == "__main__":
    unittest.main()
