# -*- coding: utf-8 -*-
"""SaaS Foundation Phase 3 — admin subscription control + trial model."""
from __future__ import annotations

import os
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import MerchantUser
from schema_merchant_subscription import reset_merchant_subscription_schema_guard_for_tests
from services.cartflow_entitlements_v1 import has_feature, plan_entitlements_enforcement_enabled
from services.cartflow_plans_v1 import PLAN_GROWTH, PLAN_STARTER
from services.merchant_subscription_v1 import (
    PLAN_SOURCE_MANUAL,
    PLAN_STATUS_ACTIVE,
    PLAN_STATUS_EXPIRED,
    PLAN_STATUS_TRIALING,
    build_merchant_subscription_status,
)
from services.admin_subscription_control_v1 import (
    apply_admin_subscription_action,
    list_subscription_audit_logs,
)


class AdminSubscriptionControlV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        self._prev_enforce = os.environ.get("CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE")
        os.environ.pop("CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE", None)
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "unit-test-admin-subscription-secret"
        reset_merchant_subscription_schema_guard_for_tests()
        db.create_all()
        from schema_merchant_subscription import ensure_merchant_subscription_schema

        ensure_merchant_subscription_schema(db)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)
        if self._prev_enforce is None:
            os.environ.pop("CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE", None)
        else:
            os.environ["CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE"] = self._prev_enforce
        db.session.remove()

    def _signup_merchant(self) -> tuple[str, TestClient]:
        email = f"admin-sub-{uuid.uuid4().hex}@example.com"
        r = self.client.post(
            "/signup",
            data={
                "store_name": "متجر تجريبي",
                "email": email,
                "password": "password123",
                "confirm_password": "password123",
            },
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303)
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).first()
        assert user is not None
        return email, self.client

    def _admin_login(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "admin-sub-pass-xyz"
        self.client.post(
            "/admin/operations/login",
            data={"password": "admin-sub-pass-xyz"},
        )

    def test_default_merchant_starter_active_manual(self) -> None:
        email, client = self._signup_merchant()
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).one()
        status = build_merchant_subscription_status(merchant_user=user)
        self.assertEqual(status.current_plan, PLAN_STARTER)
        self.assertEqual(status.plan_status, PLAN_STATUS_ACTIVE)
        self.assertEqual(status.plan_source, PLAN_SOURCE_MANUAL)
        r = client.get("/api/merchant/subscription")
        self.assertTrue(r.json()["subscription"]["current_plan"] == PLAN_STARTER)

    def test_admin_assign_growth_trial(self) -> None:
        email, _client = self._signup_merchant()
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).one()
        self._admin_login()
        r = self.client.post(
            f"/api/admin/subscriptions/{user.id}/action",
            json={
                "action": "start_trial",
                "plan": "growth",
                "trial_days": 14,
                "reason": "pilot merchant",
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        db.session.refresh(user)
        self.assertEqual(user.current_plan, PLAN_GROWTH)
        self.assertEqual(user.plan_status, PLAN_STATUS_TRIALING)
        self.assertIsNotNone(user.trial_expires_at)

    def test_growth_trial_entitlements_when_enforced(self) -> None:
        email, _client = self._signup_merchant()
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).one()
        apply_admin_subscription_action(
            int(user.id),
            action="start_trial",
            plan="growth",
            trial_days=14,
            reason="entitlement test",
        )
        db.session.refresh(user)
        os.environ["CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE"] = "1"
        self.assertTrue(plan_entitlements_enforcement_enabled())
        self.assertTrue(has_feature(user, "vip_alerts"))
        self.assertTrue(has_feature(user, "multi_message"))

    def test_admin_extend_trial(self) -> None:
        email, _client = self._signup_merchant()
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).one()
        apply_admin_subscription_action(
            int(user.id),
            action="start_trial",
            plan="growth",
            trial_days=7,
            reason="start",
        )
        db.session.refresh(user)
        first_exp = user.trial_expires_at
        apply_admin_subscription_action(
            int(user.id),
            action="extend_trial",
            extend_days=7,
            reason="extend pilot",
        )
        db.session.refresh(user)
        self.assertIsNotNone(user.trial_expires_at)
        assert first_exp is not None and user.trial_expires_at is not None
        self.assertGreater(user.trial_expires_at, first_exp)

    def test_admin_mark_expired(self) -> None:
        email, _client = self._signup_merchant()
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).one()
        apply_admin_subscription_action(
            int(user.id),
            action="mark_expired",
            reason="pilot ended",
        )
        db.session.refresh(user)
        self.assertEqual(user.plan_status, PLAN_STATUS_EXPIRED)

    def test_merchant_dashboard_reflects_trial(self) -> None:
        email, client = self._signup_merchant()
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).one()
        apply_admin_subscription_action(
            int(user.id),
            action="start_trial",
            plan="growth",
            trial_days=10,
            reason="dashboard reflect",
        )
        r = client.get("/api/merchant/subscription")
        sub = r.json()["subscription"]
        self.assertEqual(sub["current_plan"], PLAN_GROWTH)
        self.assertEqual(sub["plan_status"], PLAN_STATUS_TRIALING)
        self.assertTrue(sub["is_trialing"])
        self.assertEqual(sub["plan_source_label_ar"], "Manual")

    def test_audit_log_records_change(self) -> None:
        email, _client = self._signup_merchant()
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).one()
        result = apply_admin_subscription_action(
            int(user.id),
            action="change_plan",
            plan="pro",
            reason="upgrade pilot",
        )
        self.assertTrue(result.ok)
        logs = list_subscription_audit_logs(int(user.id))
        self.assertGreaterEqual(len(logs), 1)
        latest = logs[0]
        self.assertEqual(latest["old_plan"], PLAN_STARTER)
        self.assertEqual(latest["new_plan"], "pro")
        self.assertEqual(latest["action"], "change_plan")
        self.assertEqual(latest["reason"], "upgrade pilot")

    def test_enforcement_off_preserves_permissive_behavior(self) -> None:
        email, _client = self._signup_merchant()
        user = db.session.query(MerchantUser).filter(MerchantUser.email == email).one()
        apply_admin_subscription_action(
            int(user.id),
            action="mark_expired",
            reason="expired but enforce off",
        )
        db.session.refresh(user)
        self.assertFalse(plan_entitlements_enforcement_enabled())
        self.assertTrue(has_feature(user, "vip_alerts"))


if __name__ == "__main__":
    unittest.main()
