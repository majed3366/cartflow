# -*- coding: utf-8 -*-
"""Actionable admin routing (presentation-only)."""

from __future__ import annotations

import json
import unittest

from services.cartflow_admin_action_guidance import (
    HREF_RUNTIME,
    HREF_WHATSAPP_SETTINGS,
    actionable_panel_meta,
    derive_actionable_operational_items,
)
from services.cartflow_admin_operational_guidance import (
    PRIORITY_CRITICAL,
    PRIORITY_NORMAL,
)
from services.cartflow_admin_operational_summary import (
    ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED,
    ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION,
)


def _minimal_summary(**kw) -> dict:
    s = {
        "trust_signals_summary": {
            "runtime_degraded": False,
            "runtime_warning": False,
            "runtime_stable": True,
        },
        "degradation_flags": {},
        "platform_admin_category": "healthy",
        "aggregate_onboarding": {
            "total_stores_scanned": 2,
            "onboarding_blocked_stores": 0,
            "sandbox_store_ratio": 0.0,
            "trust_bucket_counts": {},
        },
        "admin_runtime_summary_reuse": {
            "provider_runtime_ok": True,
            "recovery_runtime_ok": True,
            "identity_runtime_ok": True,
            "dashboard_runtime_ok": True,
        },
        "stores_missing_phone_coverage_estimate": 0,
    }
    s.update(kw)
    return s


class ActionGuidanceTests(unittest.TestCase):
    def test_normal_priority_empty_actions_calm_copy(self) -> None:
        s = _minimal_summary()
        items = derive_actionable_operational_items(s, priority_key=PRIORITY_NORMAL)
        self.assertEqual(items, [])
        meta = actionable_panel_meta(
            s, priority_key=PRIORITY_NORMAL, action_items=items
        )
        self.assertIn("لا توجد إجراءات", meta["empty_title_ar"])

    def test_runtime_degraded_emits_route(self) -> None:
        s = _minimal_summary(
            trust_signals_summary={"runtime_degraded": True},
        )
        items = derive_actionable_operational_items(s, priority_key=PRIORITY_CRITICAL)
        codes = [x["code"] for x in items]
        self.assertIn("runtime_degraded", codes)
        row = next(x for x in items if x["code"] == "runtime_degraded")
        self.assertTrue(str(row.get("href", "")).startswith(HREF_RUNTIME))

    def test_provider_issue_whatsapp_settings_href(self) -> None:
        s = _minimal_summary(
            platform_admin_category=ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION,
            degradation_flags={"repeated_provider_failures": True},
        )
        items = derive_actionable_operational_items(s, priority_key=PRIORITY_CRITICAL)
        hrefs = [x.get("href") for x in items]
        self.assertIn(HREF_WHATSAPP_SETTINGS, hrefs)

    def test_onboarding_blocked_mapping(self) -> None:
        s = _minimal_summary(
            platform_admin_category=ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED,
            aggregate_onboarding={
                "total_stores_scanned": 3,
                "onboarding_blocked_stores": 2,
                "sandbox_store_ratio": 0.0,
                "trust_bucket_counts": {},
            },
        )
        items = derive_actionable_operational_items(s, priority_key=PRIORITY_CRITICAL)
        self.assertIn("onboarding_blocked", [x["code"] for x in items])

    def test_duplicate_spike_mapping(self) -> None:
        s = _minimal_summary(
            degradation_flags={"high_recent_duplicate_anomalies": True},
        )
        items = derive_actionable_operational_items(s, priority_key=PRIORITY_CRITICAL)
        self.assertIn("duplicate_spike", [x["code"] for x in items])

    def test_normal_priority_low_phone_gap_suppressed(self) -> None:
        s = _minimal_summary(stores_missing_phone_coverage_estimate=1)
        items = derive_actionable_operational_items(s, priority_key=PRIORITY_NORMAL)
        self.assertEqual(items, [])

    def test_no_secret_strings_in_items(self) -> None:
        s = _minimal_summary(
            trust_signals_summary={"runtime_degraded": True},
            degradation_flags={"repeated_provider_failures": True},
        )
        s["_unit_fake_secret"] = "twilio_super_secret_token_xyz"
        items = derive_actionable_operational_items(s, priority_key=PRIORITY_CRITICAL)
        blob = json.dumps(items, ensure_ascii=False)
        self.assertNotIn("twilio_super_secret", blob)


if __name__ == "__main__":
    unittest.main()
