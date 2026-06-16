# -*- coding: utf-8 -*-
"""Per-store Zid OAuth Authorization persistence."""
from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from io import StringIO
from unittest import mock

import models  # noqa: F401
from extensions import db, init_database
from models import Store
from schema_zid_oauth_authorization import (
    ensure_store_zid_oauth_authorization_schema,
    reset_store_zid_oauth_authorization_schema_cache_for_tests,
)
from integrations.zid_client import (
    exchange_code_for_token,
    parse_zid_authorization_from_token_response,
    persist_oauth_tokens_on_store_row,
)
from services.merchant_store_connection_v1 import (
    apply_oauth_token_to_merchant_store,
    disconnect_merchant_store,
)
from services.merchant_auth_http import merchant_cookie_name
from services.merchant_auth_v1 import register_merchant_account, session_cookie_value_for_user


class ZidOauthAuthorizationPersistTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_store_zid_oauth_authorization_schema_cache_for_tests()
        db_path = os.path.join(
            tempfile.gettempdir(),
            f"cartflow_zid_auth_persist_{uuid.uuid4().hex}.db",
        )
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        init_database()
        db.create_all()
        ensure_store_zid_oauth_authorization_schema(db)
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        reset_store_zid_oauth_authorization_schema_cache_for_tests()
        db.session.remove()

    def test_parse_authorization_strips_bearer(self) -> None:
        self.assertEqual(
            parse_zid_authorization_from_token_response(
                {"Authorization": "Bearer abc123", "access_token": "x"}
            ),
            "abc123",
        )
        self.assertEqual(
            parse_zid_authorization_from_token_response(
                {"authorization": "Bearer def456", "access_token": "x"}
            ),
            "def456",
        )
        self.assertIsNone(parse_zid_authorization_from_token_response({"access_token": "x"}))

    def test_persist_oauth_tokens_on_store_row_saves_authorization(self) -> None:
        row = Store(zid_store_id=f"zid-auth-{self._suffix}", is_active=True)
        db.session.add(row)
        db.session.commit()
        ok = persist_oauth_tokens_on_store_row(
            row,
            {
                "access_token": "mgr-token",
                "Authorization": "Bearer partner-auth",
                "refresh_token": "ref",
                "zid_store_id": row.zid_store_id,
            },
        )
        self.assertTrue(ok)
        db.session.commit()
        loaded = db.session.get(Store, row.id)
        assert loaded is not None
        self.assertEqual((loaded.access_token or "").strip(), "mgr-token")
        self.assertEqual((loaded.zid_authorization_token or "").strip(), "partner-auth")

    def test_apply_oauth_and_disconnect_clears_authorization(self) -> None:
        email = f"zid-auth-{self._suffix}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        store = db.session.get(Store, int(user.primary_store_id or 0))
        assert store is not None
        store.zid_store_id = f"zid-auth-{self._suffix}"
        db.session.commit()
        applied = apply_oauth_token_to_merchant_store(
            store_id=int(store.id),
            merchant_user_id=int(user.id),
            token_response={
                "access_token": "mgr-token",
                "Authorization": "Bearer store-partner-auth",
                "zid_store_id": store.zid_store_id,
            },
        )
        self.assertTrue(applied)
        loaded = db.session.get(Store, store.id)
        assert loaded is not None
        self.assertEqual(
            (loaded.zid_authorization_token or "").strip(),
            "store-partner-auth",
        )
        cookie = session_cookie_value_for_user(user)
        disconnected, _ = disconnect_merchant_store(
            cookies={merchant_cookie_name(): cookie}
        )
        self.assertTrue(disconnected)
        cleared = db.session.get(Store, store.id)
        assert cleared is not None
        self.assertEqual((cleared.access_token or "").strip(), "")
        self.assertIsNone(cleared.zid_authorization_token)

    def test_exchange_logs_authorization_present_without_value(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "cid"
        os.environ["ZID_CLIENT_SECRET"] = "sec"
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mgr-secret-token",
            "Authorization": "Bearer partner-secret-token",
        }
        buf = StringIO()
        with mock.patch("integrations.zid_client.requests.post", return_value=mock_resp):
            with mock.patch("sys.stdout", buf):
                body, status = exchange_code_for_token("code-1")
        self.assertEqual(status, 200)
        out = buf.getvalue()
        self.assertIn("authorization_present=true", out)
        self.assertNotIn("partner-secret-token", out)
        self.assertNotIn("mgr-secret-token", out)


if __name__ == "__main__":
    unittest.main()
