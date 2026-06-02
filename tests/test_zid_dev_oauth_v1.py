# -*- coding: utf-8 -*-
"""Zid development-store OAuth activation (gated by ZID_DEV_OAUTH_ENABLED)."""
from __future__ import annotations

import os
import unittest
import uuid
from unittest import mock

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import Store
from services.zid_dev_oauth_v1 import (
    ZID_DEV_INTEGRATION_SOURCE,
    build_zid_dev_store_status_readonly,
    persist_zid_dev_store_from_token_response,
    zid_dev_oauth_enabled,
)


class ZidDevOauthV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_dev = os.environ.get("ZID_DEV_OAUTH_ENABLED")
        self._prev_zid_id = os.environ.get("ZID_CLIENT_ID")
        self._prev_zid_secret = os.environ.get("ZID_CLIENT_SECRET")
        os.environ["ZID_DEV_OAUTH_ENABLED"] = "1"
        os.environ["ZID_CLIENT_ID"] = "test-client-id"
        os.environ["ZID_CLIENT_SECRET"] = "test-client-secret"
        self.client = TestClient(app)
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        try:
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"zid-dev-{self._suffix}%")
            ).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
        if self._prev_dev is not None:
            os.environ["ZID_DEV_OAUTH_ENABLED"] = self._prev_dev
        else:
            os.environ.pop("ZID_DEV_OAUTH_ENABLED", None)
        if self._prev_zid_id is not None:
            os.environ["ZID_CLIENT_ID"] = self._prev_zid_id
        else:
            os.environ.pop("ZID_CLIENT_ID", None)
        if self._prev_zid_secret is not None:
            os.environ["ZID_CLIENT_SECRET"] = self._prev_zid_secret
        else:
            os.environ.pop("ZID_CLIENT_SECRET", None)

    def test_zid_dev_oauth_enabled_flag(self) -> None:
        self.assertTrue(zid_dev_oauth_enabled())
        os.environ["ZID_DEV_OAUTH_ENABLED"] = "0"
        self.assertFalse(zid_dev_oauth_enabled())

    def test_auth_callback_missing_code_message(self) -> None:
        r = self.client.get("/auth/callback", follow_redirects=False)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("no authorization code", (data.get("message") or "").lower())
        self.assertTrue(data.get("callback_query_empty"))
        self.assertEqual(data.get("callback_query_keys"), [])
        self.assertEqual(data.get("callback_query_safe"), "(empty)")
        r2 = self.client.get(
            "/auth/callback?error=access_denied&error_description=denied",
            follow_redirects=False,
        )
        data2 = r2.json()
        self.assertEqual(data2.get("oauth_error"), "access_denied")
        self.assertIn("error=access_denied", data2.get("callback_query_safe") or "")

    def test_auth_callback_dev_flow_redirects_and_persists(self) -> None:
        zid = f"zid-dev-{self._suffix}"
        with mock.patch(
            "main.exchange_code_for_token",
            return_value=(
                {
                    "access_token": "dev-access-token",
                    "refresh_token": "dev-refresh",
                    "zid_store_id": zid,
                },
                200,
            ),
        ):
            r = self.client.get(
                f"/auth/callback?code=dev-code-{self._suffix}",
                follow_redirects=False,
            )
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("/dashboard", loc)
        self.assertIn("store_connected=1", loc)
        row = db.session.query(Store).filter(Store.zid_store_id == zid).first()
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual((row.access_token or "").strip(), "dev-access-token")
        self.assertEqual((row.refresh_token or "").strip(), "dev-refresh")
        self.assertEqual(row.integration_source, ZID_DEV_INTEGRATION_SOURCE)
        self.assertTrue(row.is_active)
        self.assertIsNotNone(row.connected_at)

    def test_dev_status_endpoint_hides_token(self) -> None:
        zid = f"zid-dev-{self._suffix}-status"
        row = persist_zid_dev_store_from_token_response(
            {
                "access_token": "secret-token",
                "refresh_token": "ref",
                "zid_store_id": zid,
            }
        )
        self.assertIsNotNone(row)
        os.environ["ENV"] = "development"
        r = self.client.get("/dev/zid-dev-store-status")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("connected"))
        self.assertEqual(data.get("zid_store_id"), zid)
        self.assertEqual(data.get("integration_source"), ZID_DEV_INTEGRATION_SOURCE)
        self.assertTrue(data.get("token_present"))
        self.assertNotIn("access_token", data)
        self.assertNotIn("secret-token", r.text)
        payload = build_zid_dev_store_status_readonly()
        self.assertIn("token_present", payload)

    def test_dev_flow_disabled_without_flag(self) -> None:
        os.environ["ZID_DEV_OAUTH_ENABLED"] = "0"
        with mock.patch(
            "main.exchange_code_for_token",
            return_value=({"access_token": "tok"}, 200),
        ):
            r = self.client.get(
                "/auth/callback?code=orphan-code",
                follow_redirects=False,
            )
        self.assertEqual(r.status_code, 302)
        self.assertIn("dev_oauth_disabled", r.headers.get("location") or "")

    def test_auth_zid_dev_install_skips_login_and_starts_oauth(self) -> None:
        with mock.patch(
            "services.zid_dev_oauth_v1.zid_dev_oauth_runtime_check_log"
        ) as check_log:
            r = self.client.get("/auth/zid", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertIn("oauth.zid.sa/oauth/authorize", loc)
        self.assertIn("client_id=test-client-id", loc)
        self.assertIn("redirect_uri=", loc)
        self.assertIn("response_type=code", loc)
        self.assertIn("abandoned_carts.read", loc)
        self.assertIn("orders.read", loc)
        self.assertNotIn("/login", loc)
        self.assertNotIn("state=", loc)
        check_log.assert_called_once_with(branch="dev_oauth")

    def test_auth_zid_dev_disabled_requires_login(self) -> None:
        os.environ["ZID_DEV_OAUTH_ENABLED"] = "0"
        r = self.client.get("/auth/zid", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers.get("location") or "")

    def test_api_zid_connect_still_requires_login_when_dev_enabled(self) -> None:
        r = self.client.get(
            "/api/merchant/store-connection/zid/connect",
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers.get("location") or "")
