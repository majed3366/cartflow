# -*- coding: utf-8 -*-
"""Tests for Admin Operations V3.3 root cause grouping."""
from __future__ import annotations

import unittest

from services.admin_operations_root_cause_groups_v1 import (
    ROOT_CAUSE_ONBOARDING,
    ROOT_CAUSE_WHATSAPP,
    ROOT_CAUSE_WIDGET_RUNTIME,
    group_issues_into_root_causes,
    resolve_root_cause_group,
    root_cause_count_label,
    summarize_root_causes,
)


def _symptom(kind: str, *, severity: str = "warning") -> dict:
    return {"kind": kind, "source_kind": kind, "severity": severity, "problem_en": kind}


class RootCauseGroupingTests(unittest.TestCase):
    def test_resolve_widget_runtime_kinds(self) -> None:
        for kind in (
            "runtime_beacon_missing",
            "widget_not_seen",
            "no_cart_events",
            "cart_event_bridge_missing",
        ):
            self.assertEqual(resolve_root_cause_group(kind), ROOT_CAUSE_WIDGET_RUNTIME)

    def test_resolve_whatsapp_and_onboarding(self) -> None:
        self.assertEqual(resolve_root_cause_group("whatsapp_missing"), ROOT_CAUSE_WHATSAPP)
        self.assertEqual(resolve_root_cause_group("store_needs_setup"), ROOT_CAUSE_ONBOARDING)

    def test_widget_symptoms_collapse_to_one_root_cause(self) -> None:
        issues = [
            _symptom("widget_not_seen"),
            _symptom("runtime_beacon_missing"),
            _symptom("no_cart_events"),
        ]
        root_causes = group_issues_into_root_causes(issues)
        self.assertEqual(len(root_causes), 1)
        rc = root_causes[0]
        self.assertEqual(rc["root_cause_id"], ROOT_CAUSE_WIDGET_RUNTIME)
        self.assertEqual(rc["display_name_en"], "Widget Runtime Missing")
        self.assertEqual(
            set(rc["affected_signals"]),
            {"Widget Visibility", "Runtime Beacon", "Cart Events"},
        )

    def test_separate_root_causes_for_different_groups(self) -> None:
        issues = [
            _symptom("whatsapp_missing"),
            _symptom("store_needs_setup"),
        ]
        root_causes = group_issues_into_root_causes(issues)
        self.assertEqual(len(root_causes), 2)
        ids = {rc["root_cause_id"] for rc in root_causes}
        self.assertEqual(ids, {ROOT_CAUSE_WHATSAPP, ROOT_CAUSE_ONBOARDING})

    def test_standalone_for_ungrouped_kind(self) -> None:
        issues = [
            {
                "kind": "widget_module_failed",
                "source_kind": "widget_module_failed",
                "severity": "critical",
                "problem_en": "Widget module failed to load.",
                "impact_en": "Widget may not appear.",
                "action_en": "Reinstall widget.",
                "verification_en": "Modules load.",
            }
        ]
        root_causes = group_issues_into_root_causes(issues)
        self.assertEqual(len(root_causes), 1)
        self.assertEqual(root_causes[0]["severity"], "critical")
        self.assertTrue(
            root_causes[0]["root_cause_id"].startswith("ROOT_CAUSE_STANDALONE_")
        )

    def test_root_cause_count_label(self) -> None:
        self.assertEqual(root_cause_count_label(count=1), "1 Root Cause")
        self.assertEqual(root_cause_count_label(count=2), "2 Root Causes")
        self.assertEqual(root_cause_count_label(count=0), "Healthy")

    def test_summarize_root_causes(self) -> None:
        stores = [
            {
                "has_issues": True,
                "root_cause_count": 2,
                "root_causes": [
                    {"severity": "critical"},
                    {"severity": "warning"},
                ],
            },
            {
                "has_issues": True,
                "root_cause_count": 1,
                "root_causes": [{"severity": "warning"}],
            },
        ]
        metrics = summarize_root_causes(stores)
        self.assertEqual(metrics["root_cause_count"], 3)
        self.assertEqual(metrics["critical_root_cause_count"], 1)
        self.assertEqual(metrics["warning_root_cause_count"], 2)


if __name__ == "__main__":
    unittest.main()
