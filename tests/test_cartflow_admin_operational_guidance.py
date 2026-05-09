# -*- coding: utf-8 -*-
"""Presentation-only admin operational guidance (deterministic copy)."""

from __future__ import annotations

import unittest

from services.cartflow_admin_operational_guidance import (
    PRIORITY_CRITICAL,
    PRIORITY_FOLLOW_UP,
    PRIORITY_INTERVENTION,
    PRIORITY_NORMAL,
    derive_admin_operational_guidance,
)
from services.cartflow_admin_operational_summary import (
    ADMIN_PLATFORM_CATEGORY_HEALTHY,
    ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED,
    ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION,
)


def _base_summary(**overrides) -> dict:
    s = {
        "trust_signals_summary": {
            "runtime_degraded": False,
            "runtime_warning": False,
            "runtime_stable": True,
        },
        "degradation_flags": {},
        "platform_admin_category": ADMIN_PLATFORM_CATEGORY_HEALTHY,
        "aggregate_onboarding": {
            "total_stores_scanned": 0,
            "onboarding_blocked_stores": 0,
            "sandbox_mode_stores": 0,
            "trust_bucket_counts": {},
        },
        "admin_runtime_summary_reuse": {
            "provider_runtime_ok": True,
            "recovery_runtime_ok": True,
            "identity_runtime_ok": True,
            "dashboard_runtime_ok": True,
        },
        "admin_operational_hints_ar": [],
        "anomaly_visibility": {"recent_type_counts": {}},
        "stores_missing_phone_coverage_estimate": 0,
    }
    s.update(overrides)
    return s


class AdminOperationalGuidanceTests(unittest.TestCase):
    def test_priority_normal_empty_scan(self) -> None:
        g = derive_admin_operational_guidance(_base_summary())
        self.assertEqual(g["priority_key"], PRIORITY_NORMAL)
        self.assertEqual(g["priority_label_ar"], "طبيعي")
        self.assertIn("المنصة تبدو", " ".join(g["summary_strip"]))

    def test_priority_critical_runtime_degraded(self) -> None:
        g = derive_admin_operational_guidance(
            _base_summary(
                trust_signals_summary={
                    "runtime_degraded": True,
                    "runtime_warning": False,
                    "runtime_stable": False,
                }
            )
        )
        self.assertEqual(g["priority_key"], PRIORITY_CRITICAL)
        self.assertEqual(g["priority_label_ar"], "خطر تشغيلي")

    def test_priority_intervention_onboarding_blocked_cat(self) -> None:
        g = derive_admin_operational_guidance(
            _base_summary(
                platform_admin_category=ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED,
                aggregate_onboarding={
                    "total_stores_scanned": 4,
                    "onboarding_blocked_stores": 3,
                    "sandbox_mode_stores": 0,
                    "trust_bucket_counts": {},
                },
            )
        )
        self.assertEqual(g["priority_key"], PRIORITY_INTERVENTION)

    def test_priority_follow_provider_attention_and_hints(self) -> None:
        g = derive_admin_operational_guidance(
            _base_summary(
                platform_admin_category=ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION,
                admin_operational_hints_ar=["تنبيه تجريبي"],
            )
        )
        self.assertEqual(g["priority_key"], PRIORITY_FOLLOW_UP)

    def test_empty_degradation_copy_when_clean(self) -> None:
        g = derive_admin_operational_guidance(_base_summary())
        self.assertIn("لا توجد إشارات تعارض", g["degradation_empty_message_ar"])

    def test_action_guidance_when_phone_gap(self) -> None:
        g = derive_admin_operational_guidance(
            _base_summary(stores_missing_phone_coverage_estimate=2)
        )
        self.assertTrue(any("أرقام" in a["step_ar"] for a in g["action_guidance_ar"]))


if __name__ == "__main__":
    unittest.main()
