# -*- coding: utf-8 -*-
"""SaaS foundation Phase 1 — plans, entitlements, subscription state."""
from __future__ import annotations

import os
import unittest
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import MerchantUser, Store
from schema_merchant_subscription import reset_merchant_subscription_schema_guard_for_tests
from services.cartflow_entitlements_v1 import (
    has_feature,
    is_growth,
    is_pro,
    is_starter,
    plan_entitlements_enforcement_enabled,
)
from services.cartflow_plans_v1 import (
    PLAN_GROWTH,
    PLAN_PRO,
    PLAN_STARTER,
    features_for_plan,
    normalize_plan_id,
)
from services.merchant_subscription_v1 import (
    MARKETPLACE_PLAN_EVENT_TYPES,
    build_merchant_subscription_status,
    preview_marketplace_plan_event,
    validate_marketplace_plan_event_type,
)


class CartflowPlansEntitlementsV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_enforce = os.environ.get("CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE")
        os.environ.pop("CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE", None)
        reset_merchant_subscription_schema_guard_for_tests()
        db.create_all()
        from schema_merchant_subscription import ensure_merchant_subscription_schema

        ensure_merchant_subscription_schema(db)

    def tearDown(self) -> None:
        if self._prev_enforce is None:
            os.environ.pop("CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE", None)
        else:
            os.environ["CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE"] = self._prev_enforce
        db.session.remove()

    def test_normalize_plan_id_defaults_starter(self) -> None:
        self.assertEqual(normalize_plan_id(None), PLAN_STARTER)
        self.assertEqual(normalize_plan_id("GROWTH"), PLAN_GROWTH)
        self.assertEqual(normalize_plan_id("bogus"), PLAN_STARTER)

    def test_starter_entitlements_subset_of_growth(self) -> None:
        starter = features_for_plan(PLAN_STARTER)
        growth = features_for_plan(PLAN_GROWTH)
        pro = features_for_plan(PLAN_PRO)
        self.assertTrue(starter.issubset(growth))
        self.assertTrue(growth.issubset(pro))
        self.assertIn("widget", starter)
        self.assertIn("vip_alerts", growth)
        self.assertNotIn("vip_alerts", starter)
        self.assertIn("operational_insights", pro)

    def test_has_feature_permissive_when_enforcement_off(self) -> None:
        self.assertFalse(plan_entitlements_enforcement_enabled())
        user = MerchantUser(
            email=f"t-{uuid.uuid4().hex}@example.com",
            password_hash="x",
            merchant_name="Test",
            current_plan=PLAN_STARTER,
        )
        self.assertTrue(has_feature(user, "vip_alerts"))

    def test_has_feature_respects_plan_when_enforcement_on(self) -> None:
        os.environ["CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE"] = "1"
        starter_user = MerchantUser(
            email=f"s-{uuid.uuid4().hex}@example.com",
            password_hash="x",
            merchant_name="Starter Shop",
            current_plan=PLAN_STARTER,
        )
        growth_user = MerchantUser(
            email=f"g-{uuid.uuid4().hex}@example.com",
            password_hash="x",
            merchant_name="Growth Shop",
            current_plan=PLAN_GROWTH,
        )
        self.assertTrue(has_feature(starter_user, "widget"))
        self.assertFalse(has_feature(starter_user, "vip_alerts"))
        self.assertTrue(has_feature(growth_user, "vip_alerts"))
        self.assertTrue(is_starter(starter_user))
        self.assertTrue(is_growth(growth_user))
        self.assertFalse(is_pro(growth_user))

    def test_store_without_merchant_link_stays_permissive_when_enforced(self) -> None:
        os.environ["CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE"] = "1"
        store = Store(zid_store_id=f"orphan-{uuid.uuid4().hex[:8]}")
        self.assertTrue(has_feature(store, "vip_alerts"))

    def test_marketplace_event_types_registered(self) -> None:
        self.assertIn("zid_plan_activated", MARKETPLACE_PLAN_EVENT_TYPES)
        self.assertIn("salla_plan_changed", MARKETPLACE_PLAN_EVENT_TYPES)
        self.assertTrue(validate_marketplace_plan_event_type("zid_plan_activated"))
        self.assertFalse(validate_marketplace_plan_event_type("stripe_invoice_paid"))

    def test_marketplace_event_preview_architecture_only(self) -> None:
        result = preview_marketplace_plan_event(
            "zid_plan_activated",
            {"plan": "growth", "store_id": "123"},
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.accepted)
        self.assertEqual(result.implementation_status, "architecture_only")

    def test_build_subscription_status_defaults(self) -> None:
        user = MerchantUser(
            email=f"sub-{uuid.uuid4().hex}@example.com",
            password_hash="x",
            merchant_name="Plan Test",
        )
        db.session.add(user)
        db.session.commit()
        status = build_merchant_subscription_status(merchant_user=user)
        self.assertEqual(status.current_plan, PLAN_STARTER)
        self.assertEqual(status.plan_source_label_ar, "Manual")
        self.assertTrue(status.entitlements.get("widget"))

    def test_subscription_api_authenticated(self) -> None:
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-subscription-secret"
        email = f"api-sub-{uuid.uuid4().hex}@example.com"
        client = TestClient(app)
        r_signup = client.post(
            "/signup",
            data={
                "store_name": "متجر الباقة",
                "email": email,
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(r_signup.status_code, 303)
        r = client.get("/api/merchant/subscription")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        sub = body.get("subscription") or {}
        self.assertEqual(sub.get("current_plan"), PLAN_STARTER)
        self.assertEqual(sub.get("plan_source_label_ar"), "Manual")
        self.assertTrue(sub.get("read_only"))
        self.assertFalse(sub.get("billing_actions_available"))


if __name__ == "__main__":
    unittest.main()
