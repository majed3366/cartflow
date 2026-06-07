# -*- coding: utf-8 -*-
"""SaaS Foundation Phase 4 — subscription experience & plan visibility."""
from __future__ import annotations

import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import MerchantUser
from schema_merchant_subscription import reset_merchant_subscription_schema_guard_for_tests
from services.admin_subscription_control_v1 import (
    apply_admin_subscription_action,
    build_admin_subscription_row,
)
from services.cartflow_plans_v1 import PLAN_GROWTH, PLAN_PRO, PLAN_STARTER
from services.merchant_subscription_experience_v1 import (
    build_subscription_experience_payload,
    current_plan_benefits_ar,
    days_remaining_until,
    upgrade_discovery_ar,
)
from services.merchant_subscription_v1 import (
    PLAN_STATUS_ACTIVE,
    PLAN_STATUS_CANCELLED,
    PLAN_STATUS_TRIALING,
    build_merchant_subscription_status,
)


class MerchantSubscriptionExperienceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-sub-experience-secret"
        reset_merchant_subscription_schema_guard_for_tests()
        db.create_all()
        from schema_merchant_subscription import ensure_merchant_subscription_schema

        ensure_merchant_subscription_schema(db)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        db.session.remove()

    def _create_merchant(self) -> MerchantUser:
        user = MerchantUser(
            email=f"sub-exp-{uuid.uuid4().hex}@example.com",
            password_hash="x",
            merchant_name="Visibility Store",
        )
        db.session.add(user)
        db.session.commit()
        return user

    def test_days_remaining_calculation(self) -> None:
        now = datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc)
        exp = now + timedelta(days=29)
        self.assertEqual(days_remaining_until(exp, now=now), 29)
        self.assertEqual(days_remaining_until(now - timedelta(days=1), now=now), -1)

    def test_trial_visibility(self) -> None:
        user = self._create_merchant()
        apply_admin_subscription_action(
            int(user.id),
            action="start_trial",
            plan="growth",
            reason="trial visibility",
        )
        db.session.refresh(user)
        payload = build_merchant_subscription_status(merchant_user=user).to_api_dict()
        self.assertEqual(payload["plan_status"], PLAN_STATUS_TRIALING)
        self.assertTrue(payload["is_trialing"])
        self.assertIsNotNone(payload["days_remaining"])
        self.assertIn("تنتهي التجربة", payload["subscription_health_ar"])
        self.assertEqual(payload["current_plan"], PLAN_GROWTH)
        self.assertIn("كشف VIP", payload["current_benefits_ar"])

    def test_expiry_visibility(self) -> None:
        user = self._create_merchant()
        apply_admin_subscription_action(
            int(user.id),
            action="activate_monthly",
            plan="pro",
            reason="monthly visibility",
        )
        db.session.refresh(user)
        payload = build_merchant_subscription_status(merchant_user=user).to_api_dict()
        self.assertEqual(payload["plan_status"], PLAN_STATUS_ACTIVE)
        self.assertIsNotNone(payload["days_remaining"])
        self.assertGreaterEqual(payload["days_remaining"], 29)
        self.assertIn("ينتهي الاشتراك", payload["subscription_health_ar"])

    def test_current_plan_benefits_rendering(self) -> None:
        starter = current_plan_benefits_ar(PLAN_STARTER)
        growth = current_plan_benefits_ar(PLAN_GROWTH)
        self.assertIn("الودجيت", starter)
        self.assertIn("كشف VIP", growth)
        self.assertGreater(len(growth), len(starter))

    def test_growth_discovery_rendering(self) -> None:
        discovery = upgrade_discovery_ar(PLAN_STARTER)
        self.assertIn(PLAN_GROWTH, discovery)
        self.assertIn(PLAN_PRO, discovery)
        self.assertIn("كشف VIP", discovery[PLAN_GROWTH])

    def test_pro_discovery_rendering(self) -> None:
        discovery = upgrade_discovery_ar(PLAN_GROWTH)
        self.assertNotIn(PLAN_GROWTH, discovery)
        self.assertIn(PLAN_PRO, discovery)
        self.assertIn("رؤى تشغيلية", discovery[PLAN_PRO])
        self.assertEqual(upgrade_discovery_ar(PLAN_PRO), {})

    def test_admin_visibility_rendering(self) -> None:
        user = self._create_merchant()
        apply_admin_subscription_action(
            int(user.id),
            action="activate_annual",
            plan="growth",
            reason="admin visibility",
        )
        db.session.refresh(user)
        row = build_admin_subscription_row(user)
        data = row.to_api_dict()
        self.assertEqual(data["current_plan"], PLAN_GROWTH)
        self.assertIsNotNone(data["days_remaining"])
        self.assertNotEqual(data["days_remaining_label_ar"], "—")
        self.assertIn("ينتهي الاشتراك", data["subscription_health_ar"])

    def test_cancelled_health_message(self) -> None:
        payload = build_subscription_experience_payload(
            current_plan=PLAN_STARTER,
            plan_status=PLAN_STATUS_CANCELLED,
            plan_source="manual",
            billing_interval="monthly",
            plan_expires_at=None,
            trial_expires_at=None,
            is_trialing=False,
        )
        self.assertEqual(payload["subscription_health_ar"], "تم إلغاء الاشتراك")
        self.assertEqual(payload["subscription_health_tone"], "danger")

    def test_subscription_api_includes_experience_fields(self) -> None:
        email = f"api-exp-{uuid.uuid4().hex}@example.com"
        signup = self.client.post(
            "/signup",
            data={
                "store_name": "متجر",
                "email": email,
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(signup.status_code, 303)
        r = self.client.get("/api/merchant/subscription")
        self.assertEqual(r.status_code, 200)
        sub = r.json()["subscription"]
        self.assertIn("current_benefits_ar", sub)
        self.assertIn("upgrade_discovery_sections_ar", sub)
        self.assertIn("subscription_health_ar", sub)


if __name__ == "__main__":
    unittest.main()
