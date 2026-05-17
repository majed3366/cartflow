# -*- coding: utf-8 -*-
"""Operational risk severity tiers — classification only."""

from __future__ import annotations

import unittest

from services.admin_operational_control.admin_risk_severity import (
    LEVEL_ACTUAL,
    LEVEL_CRITICAL,
    LEVEL_HEALTHY,
    LEVEL_WARNING,
    classify_operational_risk,
)
from services.admin_operational_control.context import OperationalControlContext, OperationalIssue
from services.admin_operational_control.signals import build_operational_issues


def _ctx(**kwargs: object) -> OperationalControlContext:
    base = dict(
        generated_at_utc="2026-05-17T12:00:00+00:00",
        admin_rt={"recovery_runtime_ok": True, "provider": {"configured": True}},
        admin_summary={"store_operational_rows": [], "trust_signals_summary": {}},
        cart={},
        pool={},
        bg={},
        wa={},
        warnings=[],
        affected_stores_estimate=0,
        slow_cart_event_count=0,
        pool_timeout_count=0,
        whatsapp_failed_24h=0,
        background_failure_count=0,
        provider_unstable=False,
    )
    base.update(kwargs)
    return OperationalControlContext(**base)  # type: ignore[arg-type]


class AdminRiskSeverityTests(unittest.TestCase):
    def test_level_0_healthy(self) -> None:
        ctx = _ctx()
        sev = classify_operational_risk(ctx, [])
        self.assertEqual(sev["level"], LEVEL_HEALTHY)
        self.assertEqual(sev["status_emoji"], "🟢")
        self.assertFalse(sev["risk_detected"])

    def test_level_1_provider_unstable_only(self) -> None:
        ctx = _ctx(provider_unstable=True)
        issues = build_operational_issues(ctx)
        sev = classify_operational_risk(ctx, issues)
        self.assertEqual(sev["level"], LEVEL_WARNING)
        self.assertEqual(sev["status_emoji"], "🟡")
        self.assertTrue(sev["potential_only"])
        self.assertEqual(sev.get("affected_stores_display"), 0)

    def test_level_2_failed_sends(self) -> None:
        ctx = _ctx(whatsapp_failed_24h=2, provider_unstable=True)
        issues = build_operational_issues(ctx)
        sev = classify_operational_risk(ctx, issues)
        self.assertEqual(sev["level"], LEVEL_ACTUAL)
        self.assertEqual(sev["status_emoji"], "🔴")

    def test_level_2_pool_timeout(self) -> None:
        ctx = _ctx(pool_timeout_count=1)
        issues = build_operational_issues(ctx)
        sev = classify_operational_risk(ctx, issues)
        self.assertEqual(sev["level"], LEVEL_ACTUAL)
        self.assertIn("🔴", sev["status_emoji"])

    def test_level_3_multiple_failures(self) -> None:
        ctx = _ctx(
            pool_timeout_count=1,
            whatsapp_failed_24h=2,
            slow_cart_event_count=1,
            cart={"slow_warning": True},
        )
        issues = build_operational_issues(ctx)
        sev = classify_operational_risk(ctx, issues)
        self.assertEqual(sev["level"], LEVEL_CRITICAL)
        self.assertEqual(sev["status_emoji"], "🚨")

    def test_potential_issue_zero_affected_impact(self) -> None:
        ctx = _ctx(provider_unstable=True)
        issues = build_operational_issues(ctx)
        prov = next(i for i in issues if i.code == "provider_instability")
        self.assertEqual(prov.affected_stores, 0)
        self.assertEqual(prov.tier, "potential")
        from services.admin_operational_control.admin_risk_severity import impact_text_for_issue

        self.assertEqual(impact_text_for_issue(prov), "لا يوجد أثر حالي")
