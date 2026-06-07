# -*- coding: utf-8 -*-
"""Plans UI render contract — API fields required by #plans frontend."""
from __future__ import annotations

import os
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from schema_merchant_subscription import reset_merchant_subscription_schema_guard_for_tests
from services.cartflow_plans_v1 import PLAN_GROWTH, PLAN_PRO, PLAN_STARTER


class MerchantPlansUiRenderContractV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-plans-render-contract"
        reset_merchant_subscription_schema_guard_for_tests()
        db.create_all()
        from schema_merchant_subscription import ensure_merchant_subscription_schema

        ensure_merchant_subscription_schema(db)
        self.client = TestClient(app)
        email = f"plans-render-{uuid.uuid4().hex}@example.com"
        r = self.client.post(
            "/signup",
            data={
                "store_name": "متجر العرض",
                "email": email,
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303)

    def tearDown(self) -> None:
        db.session.remove()

    def test_plans_catalog_response_shape_for_ui(self) -> None:
        r = self.client.get("/api/merchant/plans-catalog")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        sub = body["subscription"]
        catalog = body["catalog"]
        self.assertEqual(sub["current_plan"], PLAN_STARTER)
        for key in (
            "current_plan_label_ar",
            "plan_source_label_ar",
            "plan_status_label_ar",
            "current_benefits_ar",
            "upgrade_discovery_sections_ar",
            "subscription_health_ar",
            "days_remaining_label_ar",
        ):
            self.assertIn(key, sub, msg=f"missing subscription.{key}")
        self.assertIsInstance(sub["current_benefits_ar"], list)
        self.assertGreaterEqual(len(sub["current_benefits_ar"]), 1)
        discovery = sub["upgrade_discovery_sections_ar"]
        self.assertIsInstance(discovery, list)
        self.assertGreaterEqual(len(discovery), 2)
        tiers = {s.get("tier") for s in discovery}
        self.assertIn(PLAN_GROWTH, tiers)
        self.assertIn(PLAN_PRO, tiers)
        self.assertIsInstance(catalog.get("plans"), list)
        self.assertEqual(len(catalog["plans"]), 3)
        plan = catalog["plans"][0]
        for key in ("plan_id", "label_ar", "monthly_label_ar", "annual_label_ar", "features_ar"):
            self.assertIn(key, plan)

    def test_subscription_endpoint_shape_for_settings_card(self) -> None:
        r = self.client.get("/api/merchant/subscription")
        self.assertEqual(r.status_code, 200)
        sub = r.json()["subscription"]
        self.assertIn("current_benefits_ar", sub)
        self.assertIn("upgrade_discovery_sections_ar", sub)


if __name__ == "__main__":
    unittest.main()
