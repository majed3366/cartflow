# -*- coding: utf-8 -*-
"""Zid verified connection — false-green elimination + identity bind."""
from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

import models  # noqa: F401
from extensions import db, init_database
from main import app
from models import Store, StoreIdentityAlias
from schema_zid_oauth_authorization import (
    ensure_store_zid_oauth_authorization_schema,
    reset_store_zid_oauth_authorization_schema_cache_for_tests,
)
from fastapi.testclient import TestClient

from integrations.zid_client import (
    persist_oauth_tokens_on_store_row,
    reject_cross_store_manager_pair,
    ZID_MANAGER_CROSS_STORE_REJECTED,
)
from services.merchant_auth_http import merchant_cookie_name
from services.merchant_auth_v1 import register_merchant_account, session_cookie_value_for_user
from services.merchant_connection_capability_v1 import (
    STATE_AUTH_INCOMPLETE,
    STATE_AUTH_REJECTED,
    STATE_CONNECTED_VERIFIED,
    STATE_IDENTITY_MISMATCH,
    STATE_RECONNECT_REQUIRED,
    STATE_VERIFICATION_PENDING,
    read_store_connection_capability,
    store_connection_is_verified,
)
from services.merchant_onboarding_v1 import build_merchant_onboarding_flow
from services.merchant_store_connection_v1 import (
    apply_oauth_token_to_merchant_store,
    build_merchant_store_connection_status_for_store,
    is_merchant_store_platform_connected,
    issue_oauth_state,
)
from services.store_identity_v1 import (
    ALIAS_KIND_ZID_NUMERIC_ID,
    PLATFORM_ZID,
    canonical_store_slug_on_row,
    register_store_identity_alias,
    resolve_store_row_by_identifier,
)
from services.zid_connection_verification_v1 import (
    extract_zid_external_identity,
    verify_and_persist_zid_connection,
)


def _probe(body, status=200, outcome="ok"):
    return mock.patch(
        "integrations.zid_client.probe_zid_manager_store",
        return_value=(body, status, outcome),
    )


class ZidVerifiedConnectionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        reset_store_zid_oauth_authorization_schema_cache_for_tests()
        self._env_backup = dict(os.environ)
        db_path = os.path.join(
            tempfile.gettempdir(),
            f"cartflow_zid_verified_{uuid.uuid4().hex}.db",
        )
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-zid-verified"
        init_database()
        db.create_all()
        ensure_store_zid_oauth_authorization_schema(db)
        self._suffix = uuid.uuid4().hex[:10]
        self._store_seq = 0
        self.client = TestClient(app)
        self._widget_patch = mock.patch(
            "services.zid_storefront_widget_install_v1.maybe_install_zid_storefront_widget",
            return_value={"ok": True, "skipped": True, "reason": "unit_test"},
        )
        self._widget_patch.start()

    def tearDown(self) -> None:
        self._widget_patch.stop()
        reset_store_zid_oauth_authorization_schema_cache_for_tests()
        db.session.remove()
        os.environ.clear()
        os.environ.update(self._env_backup)

    def _store(
        self,
        *,
        slug: str | None = None,
        access: str = "",
        authorization: str = "",
        connected_at: datetime | None = None,
        expires_at: datetime | None = None,
        recovery_attempts: int = 2,
        whatsapp_recovery_enabled: bool = False,
    ) -> Store:
        self._store_seq += 1
        row = Store(
            zid_store_id=slug or f"cartflow-{self._suffix}-{self._store_seq}",
            access_token=access,
            zid_authorization_token=authorization or None,
            is_active=True,
            connected_at=connected_at,
            token_expires_at=expires_at,
            recovery_attempts=recovery_attempts,
            whatsapp_recovery_enabled=whatsapp_recovery_enabled,
        )
        db.session.add(row)
        db.session.commit()
        loaded = db.session.get(Store, row.id)
        assert loaded is not None
        return loaded

    def test_access_token_only_auth_incomplete(self) -> None:
        row = self._store(access="mgr-only", authorization="")
        cap = read_store_connection_capability(row)
        self.assertEqual(cap.connection_state, STATE_AUTH_INCOMPLETE)
        self.assertFalse(cap.verified)
        self.assertEqual(cap.merchant_label_ar, "لم يكتمل الربط")
        status = build_merchant_store_connection_status_for_store(row)
        self.assertFalse(status.connected)
        self.assertNotEqual(status.status_label_ar, "تم الربط")
        self.assertFalse(is_merchant_store_platform_connected(row))

    def test_authorization_only_auth_incomplete(self) -> None:
        row = self._store(access="", authorization="auth-only")
        cap = read_store_connection_capability(row)
        self.assertEqual(cap.connection_state, STATE_AUTH_INCOMPLETE)
        self.assertFalse(cap.verified)
        self.assertEqual(cap.merchant_label_ar, "لم يكتمل الربط")

    def test_both_tokens_manager_200_identity_match_verified(self) -> None:
        slug = f"cartflow-{self._suffix}"
        row = self._store(slug=slug, access="mgr-ok", authorization="auth-ok")
        numeric = str(8000000 + int(row.id))
        body = {"id": int(numeric), "url": "https://4hz49e.zid.store/"}
        attempts_before = row.recovery_attempts
        wa_before = row.whatsapp_recovery_enabled
        with _probe(body, 200, "ok"):
            cap = verify_and_persist_zid_connection(row, trigger="test")
        db.session.refresh(row)
        self.assertEqual(cap.connection_state, STATE_CONNECTED_VERIFIED)
        self.assertTrue(cap.verified)
        self.assertEqual(cap.merchant_label_ar, "تم الربط")
        self.assertIsNotNone(row.connected_at)
        self.assertEqual(canonical_store_slug_on_row(row), slug)
        owner, via = resolve_store_row_by_identifier(numeric)
        self.assertIsNotNone(owner)
        self.assertEqual(int(owner.id), int(row.id))
        self.assertIn("zid_numeric_id", via)
        status = build_merchant_store_connection_status_for_store(row)
        self.assertTrue(status.connected)
        self.assertEqual(status.status_label_ar, "تم الربط")
        self.assertEqual(row.recovery_attempts, attempts_before)
        self.assertEqual(row.whatsapp_recovery_enabled, wa_before)

    def test_both_tokens_manager_401_auth_rejected(self) -> None:
        row = self._store(access="mgr", authorization="auth")
        with _probe(None, 401, "auth_rejected"):
            cap = verify_and_persist_zid_connection(row, trigger="test")
        db.session.refresh(row)
        self.assertEqual(cap.connection_state, STATE_AUTH_REJECTED)
        self.assertFalse(cap.verified)
        self.assertIsNone(row.connected_at)
        self.assertEqual(cap.merchant_label_ar, "تعذر التحقق من الربط")
        self.assertNotEqual(
            build_merchant_store_connection_status_for_store(row).status_label_ar,
            "تم الربط",
        )

    def test_identity_mismatch_fail_closed(self) -> None:
        owner = self._store(slug=f"owner-{self._suffix}", access="a", authorization="b")
        other = self._store(slug=f"other-{self._suffix}", access="c", authorization="d")
        numeric = str(8100000 + int(owner.id))
        self.assertTrue(
            register_store_identity_alias(
                store_id=int(owner.id),
                alias_kind=ALIAS_KIND_ZID_NUMERIC_ID,
                alias_value=numeric,
                platform=PLATFORM_ZID,
            )
        )
        db.session.commit()
        with _probe({"id": int(numeric), "url": "https://zzzz.zid.store/"}, 200, "ok"):
            cap = verify_and_persist_zid_connection(other, trigger="test")
        db.session.refresh(other)
        self.assertEqual(cap.connection_state, STATE_IDENTITY_MISMATCH)
        self.assertFalse(cap.verified)
        self.assertIsNone(other.connected_at)
        self.assertEqual(canonical_store_slug_on_row(other), f"other-{self._suffix}")
        self.assertEqual(canonical_store_slug_on_row(owner), f"owner-{self._suffix}")
        rebound, _ = resolve_store_row_by_identifier(numeric)
        self.assertEqual(int(rebound.id), int(owner.id))

    def test_expired_credential_reconnect_required(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(days=1)
        row = self._store(
            access="mgr",
            authorization="auth",
            expires_at=past.replace(tzinfo=None),
        )
        cap = read_store_connection_capability(row)
        self.assertEqual(cap.connection_state, STATE_RECONNECT_REQUIRED)
        self.assertFalse(cap.verified)
        self.assertEqual(cap.merchant_label_ar, "إعادة الربط مطلوبة")
        with _probe({"id": 1}, 200, "ok"):
            cap2 = verify_and_persist_zid_connection(row, trigger="test")
        self.assertEqual(cap2.connection_state, STATE_RECONNECT_REQUIRED)
        db.session.refresh(row)
        self.assertIsNone(row.connected_at)

    def test_oauth_callback_without_authorization_not_connected(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "cid"
        os.environ["ZID_CLIENT_SECRET"] = "sec"
        email = f"zid-v-{self._suffix}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        store = db.session.get(Store, int(user.primary_store_id))
        assert store is not None
        original_slug = (store.zid_store_id or "").strip()
        state = issue_oauth_state(merchant_user_id=int(user.id), store_id=int(store.id))
        with mock.patch(
            "main.exchange_code_for_token",
            return_value=({"access_token": "tok-only", "zid_store_id": "3121837"}, 200),
        ):
            r = self.client.get(
                f"/auth/callback?code=fake-code&state={state}",
                follow_redirects=False,
            )
        self.assertEqual(r.status_code, 302)
        loc = r.headers.get("location") or ""
        self.assertNotIn("store_connected=1", loc)
        self.assertIn("store_connect_incomplete=1", loc)
        db.session.refresh(store)
        self.assertEqual((store.access_token or "").strip(), "tok-only")
        self.assertFalse(bool((store.zid_authorization_token or "").strip()))
        self.assertIsNone(store.connected_at)
        self.assertEqual((store.zid_store_id or "").strip(), original_slug)
        self.assertNotEqual(original_slug, "3121837")
        self.assertFalse(store_connection_is_verified(store))

    def test_oauth_callback_probe_unavailable_pending(self) -> None:
        os.environ["ZID_CLIENT_ID"] = "cid"
        os.environ["ZID_CLIENT_SECRET"] = "sec"
        email = f"zid-p-{self._suffix}@example.com"
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
            return_value=(
                {
                    "access_token": "mgr-tok",
                    "Authorization": "Bearer partner-tok",
                },
                200,
            ),
        ), _probe(None, 0, "unavailable"):
            r = self.client.get(
                f"/auth/callback?code=fake-code&state={state}",
                follow_redirects=False,
            )
        loc = r.headers.get("location") or ""
        self.assertNotIn("store_connected=1", loc)
        self.assertIn("store_verification_pending=1", loc)
        db.session.refresh(store)
        self.assertIsNone(store.connected_at)
        cap = read_store_connection_capability(store)
        self.assertEqual(cap.connection_state, STATE_VERIFICATION_PENDING)

    def test_numeric_alias_only_after_manager_proof(self) -> None:
        row = self._store(access="mgr", authorization="auth")
        persist_oauth_tokens_on_store_row(
            row,
            {
                "access_token": "mgr",
                "Authorization": "Bearer auth",
                "store_id": "3121837",
            },
        )
        db.session.commit()
        count = (
            db.session.query(StoreIdentityAlias)
            .filter(
                StoreIdentityAlias.store_id == int(row.id),
                StoreIdentityAlias.alias_kind == ALIAS_KIND_ZID_NUMERIC_ID,
            )
            .count()
        )
        self.assertEqual(count, 0)
        numeric = str(8200000 + int(row.id))
        with _probe({"id": int(numeric)}, 200, "ok"):
            verify_and_persist_zid_connection(row, trigger="test")
        owner, _ = resolve_store_row_by_identifier(numeric)
        self.assertEqual(int(owner.id), int(row.id))

    def test_connected_at_only_after_verified(self) -> None:
        row = self._store(access="mgr", authorization="auth")
        self.assertIsNone(row.connected_at)
        with _probe(None, 401, "auth_rejected"):
            verify_and_persist_zid_connection(row, trigger="test")
        db.session.refresh(row)
        self.assertIsNone(row.connected_at)
        numeric = str(8300000 + int(row.id))
        with _probe({"id": int(numeric)}, 200, "ok"):
            verify_and_persist_zid_connection(row, trigger="test")
        db.session.refresh(row)
        self.assertIsNotNone(row.connected_at)
        self.assertTrue(store_connection_is_verified(row))

    def test_dashboard_and_onboarding_same_rule(self) -> None:
        email = f"zid-onb-{self._suffix}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        store = db.session.get(Store, int(user.primary_store_id))
        assert store is not None
        store.access_token = "tok-only"
        db.session.commit()
        status = build_merchant_store_connection_status_for_store(store)
        self.assertNotEqual(status.status_label_ar, "تم الربط")
        flow = build_merchant_onboarding_flow(
            store, merchant_user_id=int(user.id), emit_logs=False
        )
        store_step = next(s for s in flow.steps if s.step_id == "store")
        self.assertFalse(store_step.is_complete)

        store.zid_authorization_token = "auth"
        db.session.commit()
        numeric = str(8400000 + int(store.id))
        with _probe({"id": int(numeric), "url": "https://lab.zid.store/"}, 200, "ok"):
            verify_and_persist_zid_connection(store, trigger="test")
        db.session.refresh(store)
        status2 = build_merchant_store_connection_status_for_store(store)
        self.assertEqual(status2.status_label_ar, "تم الربط")
        flow2 = build_merchant_onboarding_flow(
            store, merchant_user_id=int(user.id), emit_logs=False
        )
        store_step2 = next(s for s in flow2.steps if s.step_id == "store")
        self.assertTrue(store_step2.is_complete)

    def test_dashboard_get_does_not_call_manager(self) -> None:
        row = self._store(access="mgr-only", authorization="")
        with mock.patch(
            "integrations.zid_client.probe_zid_manager_store",
        ) as probe:
            status = build_merchant_store_connection_status_for_store(row)
        probe.assert_not_called()
        self.assertNotEqual(status.status_label_ar, "تم الربط")
        self.assertFalse(status.verified)

    def test_stale_snapshot_connected_without_verified_is_not_green(self) -> None:
        from services.merchant_connection_capability_v1 import (
            apply_verified_connection_public_guard,
        )

        guarded = apply_verified_connection_public_guard(
            {
                "connected": True,
                "store_connected_ok": True,
                "status_label_ar": "تم الربط",
            }
        )
        self.assertFalse(guarded.get("connected"))
        self.assertFalse(guarded.get("verified"))
        self.assertNotEqual(guarded.get("status_label_ar"), "تم الربط")

    def test_cross_tenant_credential_combination_rejected(self) -> None:
        a = self._store(
            slug=f"tenant-a-{self._suffix}",
            access="mgr-a",
            authorization="auth-a",
        )
        b = self._store(
            slug=f"tenant-b-{self._suffix}",
            access="mgr-b",
            authorization="auth-b",
        )
        headers, err = reject_cross_store_manager_pair(
            authorization_store=a,
            manager_token_store=b,
        )
        self.assertIsNone(headers)
        assert err is not None
        self.assertEqual(err["error"], ZID_MANAGER_CROSS_STORE_REJECTED)

    def test_persist_does_not_overwrite_cartflow_slug(self) -> None:
        slug = f"cartflow-{self._suffix}"
        row = self._store(slug=slug, access="", authorization="")
        ok = persist_oauth_tokens_on_store_row(
            row,
            {
                "access_token": "mgr",
                "Authorization": "Bearer auth",
                "zid_store_id": "3121837",
            },
        )
        self.assertTrue(ok)
        db.session.commit()
        db.session.refresh(row)
        self.assertEqual((row.zid_store_id or "").strip(), slug)
        self.assertIsNone(row.connected_at)

    def test_no_scheduler_activation_on_verify(self) -> None:
        row = self._store(
            access="mgr",
            authorization="auth",
            recovery_attempts=4,
            whatsapp_recovery_enabled=False,
        )
        active_before = row.is_active
        numeric = str(8500000 + int(row.id))
        with _probe({"id": int(numeric)}, 200, "ok"):
            verify_and_persist_zid_connection(row, trigger="test")
        db.session.refresh(row)
        self.assertEqual(row.recovery_attempts, 4)
        self.assertFalse(row.whatsapp_recovery_enabled)
        self.assertEqual(bool(row.is_active), bool(active_before))

    def test_extract_identity_from_store_payload(self) -> None:
        numeric, permalink = extract_zid_external_identity(
            {"id": 3121837, "url": "https://4hz49e.zid.store/"}
        )
        self.assertEqual(numeric, "3121837")
        self.assertEqual(permalink, "4hz49e")

    def test_apply_oauth_keeps_credentials_on_probe_failure(self) -> None:
        email = f"zid-apply-{self._suffix}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        store = db.session.get(Store, int(user.primary_store_id))
        assert store is not None
        with _probe(None, 401, "auth_rejected"):
            applied = apply_oauth_token_to_merchant_store(
                store_id=int(store.id),
                merchant_user_id=int(user.id),
                token_response={
                    "access_token": "mgr-keep",
                    "Authorization": "Bearer auth-keep",
                },
            )
        self.assertTrue(applied)
        db.session.refresh(store)
        self.assertEqual((store.access_token or "").strip(), "mgr-keep")
        self.assertEqual((store.zid_authorization_token or "").strip(), "auth-keep")
        self.assertIsNone(store.connected_at)
        self.assertEqual(
            read_store_connection_capability(store).connection_state,
            STATE_AUTH_REJECTED,
        )


if __name__ == "__main__":
    unittest.main()
