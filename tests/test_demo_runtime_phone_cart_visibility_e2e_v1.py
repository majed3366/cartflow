# -*- coding: utf-8 -*-
"""E2E: real demo runtime endpoints — store_slug coercion, phone, cart visibility."""

from __future__ import annotations

import os
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import (
    app,
    _api_json_dashboard_vip_carts,
    _normal_recovery_merchant_lightweight_alert_list_for_api,
)
from models import AbandonedCart, CartRecoveryReason, MerchantUser, Store
from schema_merchant_auth import ensure_merchant_auth_schema, reset_merchant_auth_schema_guard_for_tests
from services.merchant_auth_context import reset_merchant_auth_store_slug, set_merchant_auth_store_slug


class DemoRuntimePhoneCartVisibilityE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        reset_merchant_auth_schema_guard_for_tests()

    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-demo-runtime-e2e"
        self._suffix = uuid.uuid4().hex[:10]
        self._client = TestClient(app)
        db.create_all()
        ensure_merchant_auth_schema(db)

    def tearDown(self) -> None:
        try:
            for model, filt in (
                (CartRecoveryReason, CartRecoveryReason.session_id.like(f"%{self._suffix}%")),
                (AbandonedCart, AbandonedCart.recovery_session_id.like(f"%{self._suffix}%")),
                (Store, Store.zid_store_id.like(f"mrt-{self._suffix}%")),
                (MerchantUser, MerchantUser.email.like(f"%{self._suffix}%@example.com")),
            ):
                db.session.query(model).filter(filt).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _signup_merchant(self) -> tuple[str, dict]:
        email = f"mrt-{self._suffix}@example.com"
        r = self._client.post(
            "/signup",
            data={
                "store_name": f"MRT {self._suffix}",
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
        st.vip_cart_threshold = 1000
        db.session.commit()
        return slug, cookies

    def test_logged_in_demo_slug_reason_coerces_to_merchant_store(self) -> None:
        slug, cookies = self._signup_merchant()
        sid = f"s-coerce-{self._suffix}"
        tok = set_merchant_auth_store_slug(slug)
        try:
            r = self._client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": "demo",
                    "session_id": sid,
                    "reason": "quality",
                },
                cookies=cookies,
            )
        finally:
            reset_merchant_auth_store_slug(tok)
        self.assertEqual(r.status_code, 200, r.text)
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.session_id == sid,
                CartRecoveryReason.store_slug == slug,
            )
            .first()
        )
        self.assertIsNotNone(crr, msg="CRR must persist under coerced merchant store_slug")
        assert crr is not None
        self.assertNotEqual((crr.store_slug or "").strip(), "demo")

    def test_normal_cart_demo_flow_visible_on_dashboard(self) -> None:
        slug, cookies = self._signup_merchant()
        sid = f"s-norm-{self._suffix}"
        cid = f"cf_norm_{self._suffix}"
        tok = set_merchant_auth_store_slug(slug)
        try:
            sync = self._client.post(
                "/api/cart-event",
                json={
                    "event": "cart_state_sync",
                    "reason": "add",
                    "store": "demo",
                    "session_id": sid,
                    "cart_id": cid,
                    "cart_total": 250.0,
                    "items_count": 1,
                },
                cookies=cookies,
            )
            self.assertEqual(sync.status_code, 200, sync.text)
            reason = self._client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": "demo",
                    "session_id": sid,
                    "reason": "quality",
                    "customer_phone": "0598877660",
                },
                cookies=cookies,
            )
            self.assertEqual(reason.status_code, 200, reason.text)
        finally:
            reset_merchant_auth_store_slug(tok)

        st = db.session.query(Store).filter(Store.zid_store_id == slug).first()
        self.assertIsNotNone(st)
        assert st is not None
        rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=20,
            nr_session=sid,
            lifecycle="active",
            dash_store=st,
        )
        self.assertEqual(len(rows), 1, rows)
        self.assertTrue(rows[0].get("merchant_has_customer_phone"))

    def test_vip_phone_capture_demo_flow_shows_phone_and_manual_contact(self) -> None:
        slug, cookies = self._signup_merchant()
        sid = f"s-vip-{self._suffix}"
        cid = f"cf_vip_{self._suffix}"
        tok = set_merchant_auth_store_slug(slug)
        try:
            sync = self._client.post(
                "/api/cart-event",
                json={
                    "event": "cart_state_sync",
                    "reason": "add",
                    "store": "demo",
                    "session_id": sid,
                    "cart_id": cid,
                    "cart_total": 2500.0,
                    "items_count": 1,
                },
                cookies=cookies,
            )
            self.assertEqual(sync.status_code, 200, sync.text)
            phone = self._client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": "demo",
                    "session_id": sid,
                    "cart_id": cid,
                    "reason": "vip_phone_capture",
                    "customer_phone": "0598877665",
                    "custom_text": "vip_cart_phone_capture",
                },
                cookies=cookies,
            )
            self.assertEqual(phone.status_code, 200, phone.text)
        finally:
            reset_merchant_auth_store_slug(tok)

        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == cid)
            .first()
        )
        self.assertIsNotNone(ac)
        assert ac is not None
        self.assertEqual("966598877665", (ac.customer_phone or "").strip())
        st = db.session.query(Store).filter(Store.zid_store_id == slug).first()
        self.assertIsNotNone(st)
        assert st is not None
        self.assertEqual(int(ac.store_id), int(st.id))

        vip_body = _api_json_dashboard_vip_carts(st)
        page_rows = vip_body.get("merchant_vip_page_rows") or []
        row = next((x for x in page_rows if int(x.get("id") or 0) == int(ac.id)), None)
        self.assertIsNotNone(row, page_rows)
        assert row is not None
        self.assertTrue(row.get("has_phone"))
        self.assertTrue(row.get("manual_contact_available"))
        self.assertTrue(str(row.get("contact_href") or "").startswith("https://wa.me/"))

        tok2 = set_merchant_auth_store_slug(slug)
        try:
            mc = self._client.get(
                f"/api/dashboard/vip-cart/{int(ac.id)}/manual-contact",
                cookies=cookies,
            )
        finally:
            reset_merchant_auth_store_slug(tok2)
        self.assertEqual(mc.status_code, 200, mc.text)
        mc_body = mc.json()
        self.assertTrue(mc_body.get("ok"))
        self.assertTrue(mc_body.get("manual_contact_available"))

    def test_vip_phone_before_cart_sync_hydrates_on_next_sync(self) -> None:
        slug, cookies = self._signup_merchant()
        sid = f"s-early-{self._suffix}"
        cid = f"cf_early_{self._suffix}"
        tok = set_merchant_auth_store_slug(slug)
        try:
            phone = self._client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": "demo",
                    "session_id": sid,
                    "reason": "vip_phone_capture",
                    "customer_phone": "0598877001",
                    "custom_text": "vip_cart_phone_capture",
                },
                cookies=cookies,
            )
            self.assertEqual(phone.status_code, 200, phone.text)
            sync = self._client.post(
                "/api/cart-event",
                json={
                    "event": "cart_state_sync",
                    "reason": "add",
                    "store": "demo",
                    "session_id": sid,
                    "cart_id": cid,
                    "cart_total": 1800.0,
                    "items_count": 1,
                },
                cookies=cookies,
            )
            self.assertEqual(sync.status_code, 200, sync.text)
        finally:
            reset_merchant_auth_store_slug(tok)
        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == cid)
            .first()
        )
        self.assertIsNotNone(ac)
        assert ac is not None
        self.assertEqual("966598877001", (ac.customer_phone or "").strip())

    def test_normal_cart_archive_then_reopen_real_endpoints(self) -> None:
        """Part C: archive removes from active + shows in archived; reopen restores."""
        slug, cookies = self._signup_merchant()
        sid = f"s-arch-{self._suffix}"
        cid = f"cf_arch_{self._suffix}"
        tok = set_merchant_auth_store_slug(slug)
        try:
            sync = self._client.post(
                "/api/cart-event",
                json={
                    "event": "cart_state_sync",
                    "reason": "add",
                    "store": "demo",
                    "session_id": sid,
                    "cart_id": cid,
                    "cart_total": 250.0,
                    "items_count": 1,
                },
                cookies=cookies,
            )
            self.assertEqual(sync.status_code, 200, sync.text)
            reason = self._client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": "demo",
                    "session_id": sid,
                    "reason": "quality",
                },
                cookies=cookies,
            )
            self.assertEqual(reason.status_code, 200, reason.text)
        finally:
            reset_merchant_auth_store_slug(tok)

        st = db.session.query(Store).filter(Store.zid_store_id == slug).first()
        self.assertIsNotNone(st)
        assert st is not None
        ac = db.session.query(AbandonedCart).filter(AbandonedCart.zid_cart_id == cid).first()
        self.assertIsNotNone(ac)
        assert ac is not None

        def _active_count() -> int:
            rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
                page_limit=50, nr_session=sid, lifecycle="active", dash_store=st
            )
            return len(rows)

        def _archived_count() -> int:
            rows, _ = _normal_recovery_merchant_lightweight_alert_list_for_api(
                page_limit=50, nr_session=sid, lifecycle="archived", dash_store=st
            )
            return len(rows)

        self.assertEqual(_active_count(), 1)
        self.assertEqual(_archived_count(), 0)

        rk = f"{slug}:{sid}"
        tok2 = set_merchant_auth_store_slug(slug)
        try:
            arch = self._client.post(
                "/api/dashboard/cart-lifecycle/archive",
                json={
                    "recovery_key": rk,
                    "store_slug": slug,
                    "abandoned_cart_id": int(ac.id),
                    "session_id": sid,
                    "cart_id": cid,
                },
                cookies=cookies,
            )
            self.assertEqual(arch.status_code, 200, arch.text)
            self.assertTrue(arch.json().get("ok"), arch.text)
        finally:
            reset_merchant_auth_store_slug(tok2)
        db.session.expire_all()
        self.assertEqual(_active_count(), 0)
        self.assertEqual(_archived_count(), 1)

        tok3 = set_merchant_auth_store_slug(slug)
        try:
            reopen = self._client.post(
                "/api/dashboard/cart-lifecycle/reopen",
                json={
                    "recovery_key": rk,
                    "store_slug": slug,
                    "abandoned_cart_id": int(ac.id),
                    "session_id": sid,
                    "cart_id": cid,
                },
                cookies=cookies,
            )
            self.assertEqual(reopen.status_code, 200, reopen.text)
            self.assertTrue(reopen.json().get("ok"), reopen.text)
        finally:
            reset_merchant_auth_store_slug(tok3)
        db.session.expire_all()
        self.assertEqual(_active_count(), 1)
        self.assertEqual(_archived_count(), 0)

    @patch("services.merchant_auth_v1.development_dashboard_bypass_active", return_value=True)
    def test_dev_bypass_dashboard_resolves_demo_store(self, _mock_bypass) -> None:
        tok = set_merchant_auth_store_slug(None)
        try:
            from main import _dashboard_recovery_store_row

            row = _dashboard_recovery_store_row()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual((row.zid_store_id or "").strip(), "demo")
        finally:
            reset_merchant_auth_store_slug(tok)


if __name__ == "__main__":
    unittest.main()
