# -*- coding: utf-8 -*-
"""SaaS Foundation Phase 3.1 — automatic subscription dates + billing interval."""
from __future__ import annotations

import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from extensions import db
from models import MerchantUser
from schema_merchant_subscription import reset_merchant_subscription_schema_guard_for_tests
from services.admin_subscription_control_v1 import (
    apply_admin_subscription_action,
    list_subscription_audit_logs,
)
from services.merchant_billing_interval_v1 import (
    ANNUAL_DURATION_DAYS,
    BILLING_INTERVAL_ANNUAL,
    BILLING_INTERVAL_MANUAL_CUSTOM,
    BILLING_INTERVAL_MONTHLY,
    BILLING_INTERVAL_TRIAL,
    MONTHLY_DURATION_DAYS,
    TRIAL_DURATION_DAYS,
    calculate_expires_at_from_interval,
    preview_marketplace_subscription_dates,
)
from services.merchant_subscription_v1 import (
    PLAN_STATUS_ACTIVE,
    PLAN_STATUS_TRIALING,
    build_merchant_subscription_status,
)


class MerchantBillingIntervalV1Tests(unittest.TestCase):
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

    def _create_merchant(self) -> MerchantUser:
        email = f"billing-{uuid.uuid4().hex}@example.com"
        user = MerchantUser(
            email=email,
            password_hash="x",
            merchant_name="Test Store",
        )
        db.session.add(user)
        db.session.commit()
        return user

    def test_start_trial_auto_sets_14_day_expiry(self) -> None:
        user = self._create_merchant()
        before = datetime.now(timezone.utc)
        result = apply_admin_subscription_action(
            int(user.id),
            action="start_trial",
            plan="growth",
            reason="trial pilot",
        )
        self.assertTrue(result.ok, result.message)
        db.session.refresh(user)
        self.assertEqual(user.billing_interval, BILLING_INTERVAL_TRIAL)
        self.assertEqual(user.plan_status, PLAN_STATUS_TRIALING)
        assert user.trial_started_at is not None and user.trial_expires_at is not None
        delta = user.trial_expires_at.replace(tzinfo=timezone.utc) - before
        self.assertGreaterEqual(delta.days, TRIAL_DURATION_DAYS - 1)
        self.assertLessEqual(delta.days, TRIAL_DURATION_DAYS + 1)

    def test_activate_monthly_auto_sets_30_day_expiry(self) -> None:
        user = self._create_merchant()
        before = datetime.now(timezone.utc)
        result = apply_admin_subscription_action(
            int(user.id),
            action="activate_monthly",
            plan="pro",
            reason="monthly pilot",
        )
        self.assertTrue(result.ok, result.message)
        db.session.refresh(user)
        self.assertEqual(user.billing_interval, BILLING_INTERVAL_MONTHLY)
        self.assertEqual(user.plan_status, PLAN_STATUS_ACTIVE)
        assert user.plan_started_at is not None and user.plan_expires_at is not None
        delta = user.plan_expires_at.replace(tzinfo=timezone.utc) - before
        self.assertGreaterEqual(delta.days, MONTHLY_DURATION_DAYS - 1)
        self.assertLessEqual(delta.days, MONTHLY_DURATION_DAYS + 1)

    def test_activate_annual_auto_sets_365_day_expiry(self) -> None:
        user = self._create_merchant()
        before = datetime.now(timezone.utc)
        result = apply_admin_subscription_action(
            int(user.id),
            action="activate_annual",
            plan="growth",
            reason="annual pilot",
        )
        self.assertTrue(result.ok, result.message)
        db.session.refresh(user)
        self.assertEqual(user.billing_interval, BILLING_INTERVAL_ANNUAL)
        assert user.plan_expires_at is not None
        delta = user.plan_expires_at.replace(tzinfo=timezone.utc) - before
        self.assertGreaterEqual(delta.days, ANNUAL_DURATION_DAYS - 1)
        self.assertLessEqual(delta.days, ANNUAL_DURATION_DAYS + 1)

    def test_custom_date_still_works(self) -> None:
        user = self._create_merchant()
        custom_start = "2026-01-01"
        custom_end = "2026-06-15"
        result = apply_admin_subscription_action(
            int(user.id),
            action="activate_custom",
            plan="starter",
            plan_started_at=custom_start,
            plan_expires_at=custom_end,
            reason="custom contract",
        )
        self.assertTrue(result.ok, result.message)
        db.session.refresh(user)
        self.assertEqual(user.billing_interval, BILLING_INTERVAL_MANUAL_CUSTOM)
        self.assertEqual(user.plan_status, PLAN_STATUS_ACTIVE)
        assert user.plan_started_at is not None and user.plan_expires_at is not None
        self.assertEqual(user.plan_started_at.strftime("%Y-%m-%d"), custom_start)
        self.assertEqual(user.plan_expires_at.strftime("%Y-%m-%d"), custom_end)

    def test_audit_log_records_billing_interval_and_dates(self) -> None:
        user = self._create_merchant()
        apply_admin_subscription_action(
            int(user.id),
            action="activate_monthly",
            plan="growth",
            reason="audit interval test",
        )
        logs = list_subscription_audit_logs(int(user.id))
        self.assertGreaterEqual(len(logs), 1)
        latest = logs[0]
        self.assertEqual(latest["action"], "activate_monthly")
        self.assertEqual(latest["new_billing_interval"], BILLING_INTERVAL_MONTHLY)
        self.assertIsNotNone(latest["new_plan_expires_at"])
        self.assertIsNotNone(latest["new_plan_started_at"])
        self.assertEqual(latest["reason"], "audit interval test")

    def test_merchant_dashboard_reflects_billing_interval_and_expiry(self) -> None:
        user = self._create_merchant()
        apply_admin_subscription_action(
            int(user.id),
            action="activate_annual",
            plan="pro",
            reason="dashboard reflect",
        )
        db.session.refresh(user)
        status = build_merchant_subscription_status(merchant_user=user)
        self.assertEqual(status.billing_interval, BILLING_INTERVAL_ANNUAL)
        self.assertNotEqual(status.billing_interval_label_ar, "—")
        self.assertIsNotNone(status.plan_expires_at)
        self.assertNotEqual(status.subscription_expires_at_ar, "—")

    def test_marketplace_preview_calculates_missing_expires_at(self) -> None:
        started = datetime(2026, 1, 1, tzinfo=timezone.utc)
        exp = calculate_expires_at_from_interval(
            billing_interval=BILLING_INTERVAL_MONTHLY,
            started_at=started,
        )
        assert exp is not None
        self.assertEqual((exp - started).days, MONTHLY_DURATION_DAYS)
        preview = preview_marketplace_subscription_dates(
            {"billing_interval": "annual", "started_at": started.isoformat()},
            default_started_at=started,
        )
        self.assertEqual(preview["billing_interval"], BILLING_INTERVAL_ANNUAL)
        self.assertIn("plan_expires_at", preview)


if __name__ == "__main__":
    unittest.main()
