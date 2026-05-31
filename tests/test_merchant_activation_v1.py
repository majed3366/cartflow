# -*- coding: utf-8 -*-
"""Merchant Activation v1 — funnel, scoped demo, milestones."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from services.merchant_activation_v1 import (
    build_merchant_activation_payload,
    merchant_activation_test_store_url,
    resolve_activation_demo_for_request,
    sanitize_activation_store_slug,
)
class TestMerchantActivationSlug(unittest.TestCase):
    def test_sanitize_rejects_empty(self) -> None:
        self.assertEqual(sanitize_activation_store_slug(""), "")
        self.assertEqual(sanitize_activation_store_slug("bad slug!"), "")

    def test_sanitize_accepts_alnum(self) -> None:
        self.assertEqual(sanitize_activation_store_slug("my-store_1"), "my-store_1")


class TestActivationDemoResolution(unittest.TestCase):
    def test_anon_unknown_slug_falls_back_demo(self) -> None:
        req = MagicMock()
        req.query_params = {"store_slug": "not-owned-store"}
        req.cookies = {}
        act = resolve_activation_demo_for_request(req)
        self.assertTrue(act.denied)
        self.assertEqual(act.widget_store_slug, "demo")

    def test_merchant_activation_without_store_slug_never_demo(self) -> None:
        import uuid

        from extensions import db
        from models import Store
        from schema_merchant_auth import ensure_merchant_auth_schema
        from services.merchant_auth_http import merchant_cookie_name
        from services.merchant_auth_v1 import (
            register_merchant_account,
            session_cookie_value_for_user,
        )

        db.create_all()
        ensure_merchant_auth_schema(db)
        email = f"ma-demo-{uuid.uuid4().hex}@example.com"
        ok, err, user = register_merchant_account(
            store_name="Activation Demo Store",
            email=email,
            password="password123",
        )
        self.assertTrue(ok, err)
        st = (
            db.session.query(Store)
            .filter(Store.merchant_user_id == int(user.id))
            .order_by(Store.id.desc())
            .first()
        )
        self.assertIsNotNone(st)
        req = MagicMock()
        req.query_params = {"merchant_activation": "1"}
        cookies = {merchant_cookie_name(): session_cookie_value_for_user(user)}
        act = resolve_activation_demo_for_request(req, cookies=cookies)
        self.assertEqual(act.widget_store_slug, (st.zid_store_id or "").strip())
        self.assertNotEqual((st.zid_store_id or "").strip(), "demo")
        self.assertTrue(act.is_merchant_activation)

    def test_public_demo_slug(self) -> None:
        req = MagicMock()
        req.query_params = {"store_slug": "demo"}
        act = resolve_activation_demo_for_request(req)
        self.assertEqual(act.widget_store_slug, "demo")
        self.assertFalse(act.is_merchant_activation)


class TestActivationPayload(unittest.TestCase):
    def test_empty_store_no_carts(self) -> None:
        p = build_merchant_activation_payload(None)
        self.assertEqual(p.current_state_id, "no_carts")
        self.assertFalse(p.activation_working)


class TestActivationRoutes(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from main import app  # noqa: PLC0415

        self.client = TestClient(app)

    def test_register_redirects_signup(self) -> None:
        r = self.client.get("/register", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/signup", r.headers.get("Location", ""))

    def test_landing_links_signup(self) -> None:
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        body = r.text
        self.assertIn('href="/signup"', body)
        self.assertIn('href="/login"', body)
        self.assertNotIn('href="/register"', body)
        self.assertNotIn('href="/dashboard"', body)

    def test_landing_merchant_entry_copy(self) -> None:
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        body = r.text
        self.assertIn("استرجع السلال المترددة بذكاء ووضوح", body)
        self.assertIn("CartFlow يفهم سبب تردد العميل من الودجيت", body)
        self.assertIn("ابدأ الآن", body)
        self.assertIn("تسجيل الدخول", body)
        self.assertIn("كيف يعمل؟", body)
        self.assertIn("العميل يضيف للسلة", body)
        self.assertIn("الداشبورد يشرح ما حدث", body)
        self.assertIn("لماذا يناسب التجار؟", body)
        self.assertIn("ابدأ تجربة CartFlow", body)
        self.assertIn("حالياً في مرحلة الإطلاق التجريبي والتحسين المستمر", body)

    def test_landing_no_fake_stats_or_placeholders(self) -> None:
        r = self.client.get("/")
        body = r.text.lower()
        for banned in (
            "500 stores",
            "500 متجر",
            "placeholder",
            "lorem ipsum",
            "href=\"#\"",
            "href=\"javascript:",
        ):
            self.assertNotIn(banned, body, msg=f"unexpected {banned!r}")

    def test_landing_mobile_viewport(self) -> None:
        r = self.client.get("/")
        self.assertIn('name="viewport"', r.text)
        self.assertIn('dir="rtl"', r.text)
        self.assertIn('lang="ar"', r.text)

    def test_landing_dashboard_green_identity(self) -> None:
        r = self.client.get("/")
        body = r.text
        self.assertIn("#16a34a", body)
        self.assertIn("#166534", body)
        self.assertNotIn("#4f46e5", body)
        self.assertIn("معاينة توضيحية للوحة التاجر", body)

    def test_landing_cta_routes_work(self) -> None:
        signup = self.client.get("/signup", follow_redirects=False)
        self.assertEqual(signup.status_code, 200)
        self.assertIn("إنشاء حساب", signup.text)
        login = self.client.get("/login", follow_redirects=False)
        self.assertEqual(login.status_code, 200)
        self.assertIn("تسجيل الدخول", login.text)

    def test_test_widget_requires_login(self) -> None:
        r = self.client.get("/dashboard/test-widget", follow_redirects=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers.get("Location", ""))


class TestActivationStoreUrl(unittest.TestCase):
    def test_url_includes_slug_and_flags(self) -> None:
        u = merchant_activation_test_store_url("shop-abc")
        self.assertIn("store_slug=shop-abc", u)
        self.assertIn("merchant_activation=1", u)
        self.assertIn("reset_demo=1", u)


if __name__ == "__main__":
    unittest.main()
