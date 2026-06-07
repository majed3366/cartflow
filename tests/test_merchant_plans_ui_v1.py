# -*- coding: utf-8 -*-
"""Plans catalog API + UI regression tests."""
from __future__ import annotations

import os
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from schema_merchant_subscription import reset_merchant_subscription_schema_guard_for_tests
from services.cartflow_plans_v1 import PLAN_GROWTH, PLAN_STARTER
from services.merchant_plans_catalog_v1 import (
    MOST_POPULAR_PLAN_ID,
    PLAN_PRICING_SAR,
    build_merchant_plans_catalog,
)


class MerchantPlansCatalogV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-plans-ui-secret"
        reset_merchant_subscription_schema_guard_for_tests()
        db.create_all()
        from schema_merchant_subscription import ensure_merchant_subscription_schema

        ensure_merchant_subscription_schema(db)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        db.session.remove()

    def test_catalog_pricing_and_popular(self) -> None:
        catalog = build_merchant_plans_catalog()
        self.assertTrue(catalog["read_only"])
        self.assertFalse(catalog["billing_available"])
        self.assertEqual(catalog["most_popular_plan_id"], MOST_POPULAR_PLAN_ID)
        plans = {p["plan_id"]: p for p in catalog["plans"]}
        self.assertEqual(plans[PLAN_STARTER]["monthly_sar"], PLAN_PRICING_SAR[PLAN_STARTER]["monthly"])
        self.assertEqual(plans[PLAN_GROWTH]["annual_sar"], PLAN_PRICING_SAR[PLAN_GROWTH]["annual"])
        self.assertTrue(plans[PLAN_GROWTH]["most_popular"])

    def test_plans_catalog_api_authenticated(self) -> None:
        email = f"plans-ui-{uuid.uuid4().hex}@example.com"
        r_signup = self.client.post(
            "/signup",
            data={
                "store_name": "متجر الباقات",
                "email": email,
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(r_signup.status_code, 303)
        r = self.client.get("/api/merchant/plans-catalog")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body["subscription"]["current_plan"], PLAN_STARTER)
        self.assertEqual(len(body["catalog"]["plans"]), 3)
        self.assertFalse(body["catalog"]["upgrade_available"])


if __name__ == "__main__":
    unittest.main()
