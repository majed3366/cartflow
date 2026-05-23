# -*- coding: utf-8 -*-
"""Onboarding store resolution — authenticated merchant only."""
from __future__ import annotations

import os
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import MerchantUser, Store
from schema_merchant_auth import reset_merchant_auth_schema_guard_for_tests
from services.merchant_auth_http import merchant_cookie_name
from services.merchant_auth_v1 import register_merchant_account, session_cookie_value_for_user
from services.merchant_onboarding_store import resolve_merchant_onboarding_store
from services.merchant_setup_experience_v1 import build_merchant_setup_experience_api_payload


class MerchantOnboardingStoreScopingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_env = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-onboarding-scope"
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

    def test_new_merchant_not_ready_via_api(self) -> None:
        email = f"onb-new-{uuid.uuid4().hex}@example.com"
        ok, _, user = register_merchant_account(
            store_name="متجر جديد",
            email=email,
            password="password123",
        )
        self.assertTrue(ok)
        assert user is not None
        cookie_val = session_cookie_value_for_user(user)
        cookies = {merchant_cookie_name(): cookie_val}

        payload = build_merchant_setup_experience_api_payload(cookies=cookies)
        self.assertFalse(payload.get("onboarding_complete"))
        self.assertFalse(payload.get("first_recovery_ready"))
        self.assertNotIn("جاهز", payload.get("card_title_ar") or "")
        self.assertEqual(payload.get("merchant_store_display_name"), "متجر جديد")

        r = self.client.get(
            "/api/merchant/setup-experience",
            cookies=cookies,
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        mse = body.get("merchant_setup_experience") or {}
        self.assertFalse(mse.get("onboarding_complete"))
        self.assertIn("إعداد", mse.get("card_title_ar") or "")

    def test_unauthenticated_does_not_use_latest_store(self) -> None:
        demo = Store(
            zid_store_id=f"latest-fallback-{uuid.uuid4().hex[:8]}",
            access_token="demo-token",
            store_whatsapp_number="+966500000001",
            cartflow_widget_enabled=True,
            recovery_attempts=2,
        )
        db.session.add(demo)
        db.session.commit()

        store, meta = resolve_merchant_onboarding_store(cookies={})
        self.assertIsNone(store)
        self.assertEqual(meta.source, "unauthenticated")

        payload = build_merchant_setup_experience_api_payload(cookies={})
        self.assertFalse(payload.get("onboarding_complete"))

    def test_cross_merchant_isolation(self) -> None:
        ok_a, _, user_a = register_merchant_account(
            store_name="متجر أ",
            email=f"onb-a-{uuid.uuid4().hex}@example.com",
            password="password123",
        )
        ok_b, _, user_b = register_merchant_account(
            store_name="متجر ب",
            email=f"onb-b-{uuid.uuid4().hex}@example.com",
            password="password123",
        )
        self.assertTrue(ok_a and ok_b)
        assert user_a is not None and user_b is not None

        mature = Store(
            zid_store_id=f"mature-{uuid.uuid4().hex[:8]}",
            merchant_user_id=user_a.id,
            access_token="zid-oauth-token",
            store_whatsapp_number="+966511111111",
            whatsapp_recovery_enabled=True,
            cartflow_widget_enabled=True,
            recovery_attempts=2,
            widget_display_name="متجر ناضج",
        )
        db.session.add(mature)
        db.session.commit()

        cookies_b = {merchant_cookie_name(): session_cookie_value_for_user(user_b)}
        store_b, meta_b = resolve_merchant_onboarding_store(cookies=cookies_b)
        self.assertIsNotNone(store_b)
        assert store_b is not None
        self.assertEqual(int(store_b.merchant_user_id), int(user_b.id))
        self.assertNotEqual(int(store_b.id), int(mature.id))
        self.assertEqual(meta_b.store_name, "متجر ب")

        payload_b = build_merchant_setup_experience_api_payload(cookies=cookies_b)
        self.assertFalse(payload_b.get("onboarding_complete"))


if __name__ == "__main__":
    unittest.main()
