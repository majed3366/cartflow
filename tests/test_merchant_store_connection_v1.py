# -*- coding: utf-8 -*-
"""Merchant store connection setup v1 — authenticated store only."""
from __future__ import annotations

import os
import unittest
import uuid
from unittest import mock

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import Store
from schema_merchant_auth import reset_merchant_auth_schema_guard_for_tests
from services.merchant_auth_http import merchant_cookie_name
from services.merchant_auth_v1 import register_merchant_account, session_cookie_value_for_user
from services.merchant_onboarding_v1 import build_merchant_onboarding_flow
from services.merchant_store_connection_v1 import (
    build_merchant_store_connection_status,
    disconnect_merchant_store,
    is_merchant_store_platform_connected,
    issue_oauth_state,
    parse_oauth_state,
)


class MerchantStoreConnectionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_env = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-store-connection"
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
        os.environ.pop("ZID_CLIENT_ID", None)
        os.environ.pop("ZID_CLIENT_SECRET", None)
        os.environ.pop("OAUTH_REDIRECT_URI", None)
        os.environ.pop("CARTFLOW_PUBLIC_BASE_URL", None)
        os.environ.pop("ZID_OAUTH_SCOPE", None)
        db.session.remove()

    def test_new_merchant_shows_not_connected(self) -> None:
        email = f"sc-new-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر تجريبي",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}

        status = build_merchant_store_connection_status(cookies=cookies)
        self.assertFalse(status.connected)
        self.assertEqual(status.status_label_ar, "غير مربوط")
        self.assertEqual(status.store_name, "متجر تجريبي")

        r = self.client.get("/api/merchant/store-connection", cookies=cookies)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        sc = body.get("store_connection") or {}
        self.assertFalse(sc.get("connected"))
        self.assertEqual(sc.get("status_label_ar"), "غير مربوط")

    def test_dashboard_settings_contains_store_connection_section(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertIn("ربط المتجر", html)
        self.assertIn("اربط متجرك لقراءة الطلبات والسلال", html)
        self.assertIn("ma-store-connection-root", html)
        self.assertIn("merchant_store_connection.js", html)

    def test_zid_connect_without_oauth_config_shows_pending_redirect(self) -> None:
        os.environ.pop("ZID_CLIENT_ID", None)
        os.environ.pop("ZID_CLIENT_SECRET", None)
        email = f"sc-pend-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}
        r = self.client.get(
            "/api/merchant/store-connection/zid/connect",
            cookies=cookies,
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("store_connect_pending=1", r.headers.get("location") or "")

    def test_connected_merchant_shows_connected_state(self) -> None:
        email = f"sc-ok-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر مربوط",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        store = db.session.get(Store, int(user.primary_store_id))
        assert store is not None
        store.access_token = "zid-oauth-access-token"
        db.session.commit()

        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}
        status = build_merchant_store_connection_status(cookies=cookies)
        self.assertTrue(status.connected)
        self.assertEqual(status.status_label_ar, "تم الربط")
        self.assertEqual(status.platform_ar, "زد")
        self.assertTrue(is_merchant_store_platform_connected(store))

    def test_disconnect_clears_token(self) -> None:
        email = f"sc-disc-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        store = db.session.get(Store, int(user.primary_store_id))
        assert store is not None
        store.access_token = "tok"
        db.session.commit()
        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}

        ok_d, _ = disconnect_merchant_store(cookies=cookies)
        self.assertTrue(ok_d)
        db.session.refresh(store)
        self.assertEqual((store.access_token or "").strip(), "")
        status = build_merchant_store_connection_status(cookies=cookies)
        self.assertFalse(status.connected)

    def test_onboarding_store_step_after_real_token(self) -> None:
        email = f"sc-onb-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        store = db.session.get(Store, int(user.primary_store_id))
        assert store is not None
        flow_before = build_merchant_onboarding_flow(
            store, merchant_user_id=int(user.id), emit_logs=False
        )
        store_step_before = next(s for s in flow_before.steps if s.step_id == "store")
        self.assertFalse(store_step_before.is_complete)

        store.access_token = "zid-oauth-access-token"
        db.session.commit()
        flow_after = build_merchant_onboarding_flow(
            store, merchant_user_id=int(user.id), emit_logs=False
        )
        store_step_after = next(s for s in flow_after.steps if s.step_id == "store")
        self.assertTrue(store_step_after.is_complete)

    def test_oauth_state_roundtrip(self) -> None:
        state = issue_oauth_state(merchant_user_id=7, store_id=42)
        parsed = parse_oauth_state(state)
        self.assertEqual(parsed, (42, 7))

    def test_oauth_redirect_uri_explicit_env(self) -> None:
        os.environ["OAUTH_REDIRECT_URI"] = "https://app.example/auth/callback"
        os.environ.pop("CARTFLOW_PUBLIC_BASE_URL", None)
        from integrations.zid_client import get_oauth_redirect_uri

        self.assertEqual(get_oauth_redirect_uri(), "https://app.example/auth/callback")

    def test_oauth_redirect_uri_from_public_base(self) -> None:
        os.environ.pop("OAUTH_REDIRECT_URI", None)
        os.environ["CARTFLOW_PUBLIC_BASE_URL"] = "https://shop.example/"
        from integrations.zid_client import get_oauth_redirect_uri

        self.assertEqual(get_oauth_redirect_uri(), "https://shop.example/auth/callback")

    def test_zid_connect_builds_authorize_url_with_redirect_uri(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "test-client-id"
        os.environ["ZID_CLIENT_SECRET"] = "test-client-secret"
        os.environ["OAUTH_REDIRECT_URI"] = "https://app.example/auth/callback"
        email = f"sc-oauth-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}
        r = self.client.get(
            "/api/merchant/store-connection/zid/connect",
            cookies=cookies,
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("oauth.zid.sa/oauth/authorize", loc)
        self.assertIn("redirect_uri=https%3A%2F%2Fapp.example%2Fauth%2Fcallback", loc)
        self.assertIn("response_type=code", loc)
        self.assertIn("scope=abandoned_carts.read+orders.read", loc)
        self.assertIn("state=", loc)

    def test_zid_connect_scope_override_via_env(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "test-client-id"
        os.environ["ZID_CLIENT_SECRET"] = "test-client-secret"
        os.environ["ZID_OAUTH_SCOPE"] = "orders.read webhooks.read_write"
        email = f"sc-scope-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}
        r = self.client.get(
            "/api/merchant/store-connection/zid/connect",
            cookies=cookies,
            follow_redirects=False,
        )
        loc = r.headers.get("location") or ""
        self.assertIn("scope=orders.read+webhooks.read_write", loc)

    def test_zid_connect_empty_scope_env_omits_scope(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "test-client-id"
        os.environ["ZID_CLIENT_SECRET"] = "test-client-secret"
        os.environ["ZID_OAUTH_SCOPE"] = ""
        email = f"sc-noscope-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}
        r = self.client.get(
            "/api/merchant/store-connection/zid/connect",
            cookies=cookies,
            follow_redirects=False,
        )
        loc = r.headers.get("location") or ""
        self.assertNotIn("scope=", loc)

    def test_get_zid_oauth_scope_default(self) -> None:
        os.environ.pop("ZID_OAUTH_SCOPE", None)
        from integrations.zid_client import get_zid_oauth_scope

        self.assertEqual(get_zid_oauth_scope(), "abandoned_carts.read orders.read")

    def test_auth_callback_success_redirects_to_dashboard(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "test-client-id"
        os.environ["ZID_CLIENT_SECRET"] = "test-client-secret"
        email = f"sc-cb-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        store = db.session.get(Store, int(user.primary_store_id))
        assert store is not None
        state = issue_oauth_state(merchant_user_id=int(user.id), store_id=int(store.id))
        with mock.patch(
            "main.exchange_code_for_token",
            return_value=({"access_token": "tok-test", "refresh_token": "ref"}, 200),
        ):
            r = self.client.get(
                f"/auth/callback?code=fake-code&state={state}",
                follow_redirects=False,
            )
        self.assertEqual(r.status_code, 302)
        self.assertIn("/dashboard", r.headers.get("location") or "")
        self.assertIn("store_connected=1", r.headers.get("location") or "")
        db.session.refresh(store)
        self.assertEqual((store.access_token or "").strip(), "tok-test")

    def test_auth_callback_missing_code_on_probe(self) -> None:
        r = self.client.get("/auth/callback", follow_redirects=False)
        self.assertEqual(r.status_code, 200)
        self.assertIn("callback route exists", (r.text or ""))

    def test_auth_callback_token_failure_redirects(self) -> None:
        with mock.patch(
            "main.exchange_code_for_token",
            return_value=({"error": "invalid_grant"}, 400),
        ):
            r = self.client.get(
                "/auth/callback?code=bad-code&state=1:2:3:4",
                follow_redirects=False,
            )
        self.assertEqual(r.status_code, 302)
        self.assertIn("store_connect_error=", r.headers.get("location") or "")

    def test_auth_zid_alias_starts_oauth(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "test-client-id"
        os.environ["ZID_CLIENT_SECRET"] = "test-client-secret"
        email = f"sc-zid-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}
        r = self.client.get("/auth/zid", cookies=cookies, follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("oauth.zid.sa/oauth/authorize", r.headers.get("location") or "")

    def test_unauthenticated_api_shows_not_connected_without_leak(self) -> None:
        """Without session cookie, status is disconnected (no demo/latest store leak)."""
        r = self.client.get("/api/merchant/store-connection")
        self.assertEqual(r.status_code, 200)
        sc = (r.json() or {}).get("store_connection") or {}
        self.assertFalse(sc.get("connected"))
        self.assertEqual(sc.get("status_label_ar"), "غير مربوط")


if __name__ == "__main__":
    unittest.main()
