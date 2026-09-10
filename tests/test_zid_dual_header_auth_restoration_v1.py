# -*- coding: utf-8 -*-
"""Zid dual-header Manager auth: same-store bind, fail-closed, no env fallback."""
from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from io import StringIO
from types import SimpleNamespace
from unittest import mock

import models  # noqa: F401
from extensions import db, init_database
from models import Store
from schema_zid_oauth_authorization import (
    ensure_store_zid_oauth_authorization_schema,
    reset_store_zid_oauth_authorization_schema_cache_for_tests,
)
from integrations.zid_client import (
    ZID_MANAGER_AUTH_INCOMPLETE,
    ZID_MANAGER_CROSS_STORE_REJECTED,
    exchange_code_for_token,
    fetch_abandoned_carts,
    fetch_orders,
    manager_headers_for_oauth_grant,
    manager_headers_for_store,
    manager_headers_from_explicit_pair,
    persist_oauth_tokens_on_store_row,
    reject_cross_store_manager_pair,
    zid_manager_auth_state,
)


class ZidDualHeaderAuthRestorationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_store_zid_oauth_authorization_schema_cache_for_tests()
        self._env_backup = dict(os.environ)
        db_path = os.path.join(
            tempfile.gettempdir(),
            f"cartflow_zid_dual_hdr_{uuid.uuid4().hex}.db",
        )
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        init_database()
        db.create_all()
        ensure_store_zid_oauth_authorization_schema(db)
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        reset_store_zid_oauth_authorization_schema_cache_for_tests()
        db.session.remove()
        os.environ.clear()
        os.environ.update(self._env_backup)

    def _store(
        self,
        *,
        access: str = "mgr-a",
        authorization: str = "auth-a",
        slug: str | None = None,
    ) -> Store:
        row = Store(
            zid_store_id=slug or f"zid-dual-{self._suffix}-{uuid.uuid4().hex[:6]}",
            access_token=access,
            zid_authorization_token=authorization,
            is_active=True,
        )
        db.session.add(row)
        db.session.commit()
        loaded = db.session.get(Store, row.id)
        assert loaded is not None
        return loaded

    def test_same_store_dual_header(self) -> None:
        row = self._store(access="mgr-same", authorization="auth-same")
        headers, err = manager_headers_for_store(row)
        self.assertIsNone(err)
        assert headers is not None
        self.assertEqual(headers["Authorization"], "Bearer auth-same")
        self.assertEqual(headers["X-MANAGER-TOKEN"], "mgr-same")
        state = zid_manager_auth_state(row)
        self.assertTrue(state["ready"])
        self.assertEqual(state["store_id"], row.id)

    def test_missing_authorization_fail_closed(self) -> None:
        row = self._store(access="mgr-only", authorization="")
        headers, err = manager_headers_for_store(row)
        self.assertIsNone(headers)
        assert err is not None
        self.assertEqual(err["error"], ZID_MANAGER_AUTH_INCOMPLETE)
        self.assertEqual(err["missing"], ["zid_authorization_token"])
        body, status = fetch_orders(row, page=1, page_size=1)
        self.assertEqual(status, 409)
        self.assertEqual(body.get("error"), ZID_MANAGER_AUTH_INCOMPLETE)

    def test_missing_manager_token_fail_closed(self) -> None:
        row = self._store(access="", authorization="auth-only")
        headers, err = manager_headers_for_store(row)
        self.assertIsNone(headers)
        assert err is not None
        self.assertEqual(err["error"], ZID_MANAGER_AUTH_INCOMPLETE)
        self.assertEqual(err["missing"], ["access_token"])
        body, status = fetch_abandoned_carts(row)
        self.assertEqual(status, 409)
        self.assertEqual(body.get("error"), ZID_MANAGER_AUTH_INCOMPLETE)

    def test_store_a_auth_plus_store_b_manager_rejected(self) -> None:
        store_a = self._store(access="mgr-a", authorization="auth-a")
        store_b = self._store(access="mgr-b", authorization="auth-b")
        headers, err = reject_cross_store_manager_pair(
            authorization_store=store_a,
            manager_token_store=store_b,
        )
        self.assertIsNone(headers)
        assert err is not None
        self.assertEqual(err["error"], ZID_MANAGER_CROSS_STORE_REJECTED)
        mixed, mixed_err = manager_headers_from_explicit_pair(
            store=store_a,
            authorization_token=store_a.zid_authorization_token or "",
            access_token=store_b.access_token or "",
        )
        self.assertIsNone(mixed)
        assert mixed_err is not None
        self.assertEqual(mixed_err["error"], ZID_MANAGER_CROSS_STORE_REJECTED)

    def test_oauth_response_with_authorization_persisted(self) -> None:
        row = Store(zid_store_id=f"zid-persist-yes-{self._suffix}", is_active=True)
        db.session.add(row)
        db.session.commit()
        ok = persist_oauth_tokens_on_store_row(
            row,
            {
                "access_token": "mgr-new",
                "Authorization": "Bearer auth-new",
                "refresh_token": "ref-new",
                "expires_in": 3600,
                "zid_store_id": row.zid_store_id,
            },
        )
        self.assertTrue(ok)
        db.session.commit()
        loaded = db.session.get(Store, row.id)
        assert loaded is not None
        self.assertEqual((loaded.access_token or "").strip(), "mgr-new")
        self.assertEqual((loaded.zid_authorization_token or "").strip(), "auth-new")
        self.assertEqual((loaded.refresh_token or "").strip(), "ref-new")
        self.assertIsNotNone(loaded.token_expires_at)
        headers, err = manager_headers_for_store(loaded)
        self.assertIsNone(err)
        assert headers is not None
        self.assertEqual(headers["Authorization"], "Bearer auth-new")

    def test_oauth_response_without_authorization_explicit_missing(self) -> None:
        row = Store(zid_store_id=f"zid-persist-no-{self._suffix}", is_active=True)
        db.session.add(row)
        db.session.commit()
        grant = {"access_token": "mgr-only", "zid_store_id": row.zid_store_id}
        headers, err = manager_headers_for_oauth_grant(grant)
        self.assertIsNone(headers)
        assert err is not None
        self.assertEqual(err["error"], ZID_MANAGER_AUTH_INCOMPLETE)
        self.assertEqual(err["missing"], ["Authorization"])
        ok = persist_oauth_tokens_on_store_row(row, grant)
        self.assertTrue(ok)
        db.session.commit()
        loaded = db.session.get(Store, row.id)
        assert loaded is not None
        state = zid_manager_auth_state(loaded)
        self.assertFalse(state["ready"])
        self.assertEqual(state["zid_authorization_token"], "missing")
        self.assertEqual(state["access_token"], "present")

    def test_no_env_fallback(self) -> None:
        os.environ["ZID_API_AUTHORIZATION"] = "env-must-not-be-used"
        row = self._store(access="mgr-env", authorization="")
        headers, err = manager_headers_for_store(row)
        self.assertIsNone(headers)
        assert err is not None
        self.assertEqual(err["error"], ZID_MANAGER_AUTH_INCOMPLETE)
        self.assertNotIn("Authorization", err)

    def test_env_ignored_when_store_pair_present(self) -> None:
        os.environ["ZID_API_AUTHORIZATION"] = "env-must-not-be-used"
        row = self._store(access="mgr-row", authorization="auth-row")
        headers, err = manager_headers_for_store(row)
        self.assertIsNone(err)
        assert headers is not None
        self.assertEqual(headers["Authorization"], "Bearer auth-row")
        self.assertNotIn("env-must-not-be-used", headers["Authorization"])

    def test_exchange_and_headers_never_log_tokens(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "cid"
        os.environ["ZID_CLIENT_SECRET"] = "client-secret-value"
        mock_resp = mock.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mgr-secret-token",
            "Authorization": "Bearer partner-secret-token",
        }
        buf = StringIO()
        with mock.patch("integrations.zid_client.requests.post", return_value=mock_resp):
            with mock.patch("sys.stdout", buf):
                body, status = exchange_code_for_token("code-secret")
        self.assertEqual(status, 200)
        out = buf.getvalue()
        self.assertIn("authorization_present=true", out)
        self.assertNotIn("partner-secret-token", out)
        self.assertNotIn("mgr-secret-token", out)
        self.assertNotIn("client-secret-value", out)
        store = SimpleNamespace(
            id=99,
            access_token="mgr-secret-token",
            zid_authorization_token="partner-secret-token",
        )
        log_buf = StringIO()
        with mock.patch("sys.stdout", log_buf):
            headers, err = manager_headers_for_store(store)
        self.assertIsNone(err)
        assert headers is not None
        logged = log_buf.getvalue()
        self.assertNotIn("partner-secret-token", logged)
        self.assertNotIn("mgr-secret-token", logged)


if __name__ == "__main__":
    unittest.main()
