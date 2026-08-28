# -*- coding: utf-8 -*-
"""Presentation projection for Operations Center V1.1 — no new eligibility."""
from __future__ import annotations

import unittest

from services.admin_operations_center_v11_present_v1 import (
    build_operations_center_v11_presentation,
    explicit_int,
    format_generated_at_ar,
    operator_action_required,
    scoped_observation_headline_ar,
    split_intervention_queues,
    split_platform_alerts_by_action,
)
from services.admin_operations_operational_priority_v1 import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    apply_store_operational_priority,
)
from services.admin_operations_store_action_center_v1 import _PLATFORM_ONLY_KINDS


class OperationsCenterV11PresentTests(unittest.TestCase):
    def test_split_excludes_low_from_intervention(self) -> None:
        high = apply_store_operational_priority(
            {
                "has_issues": True,
                "store_slug": "a",
                "root_causes": [
                    {
                        "root_cause_id": "ROOT_CAUSE_WIDGET_RUNTIME",
                        "symptom_kinds": ["runtime_beacon_missing"],
                        "severity": "warning",
                    }
                ],
            }
        )
        low = apply_store_operational_priority(
            {
                "has_issues": True,
                "store_slug": "b",
                "root_causes": [
                    {
                        "root_cause_id": "ROOT_CAUSE_STANDALONE_NOTE",
                        "symptom_kinds": ["informational_note"],
                        "severity": "information",
                    }
                ],
            }
        )
        self.assertEqual(high.get("priority"), PRIORITY_HIGH)
        self.assertEqual(low.get("priority"), PRIORITY_LOW)
        intervene, monitor = split_intervention_queues([high, low])
        self.assertEqual([s["store_slug"] for s in intervene], ["a"])
        self.assertEqual([s["store_slug"] for s in monitor], ["b"])
        self.assertEqual(len(intervene), 1)

    def test_operator_action_uses_action_en_not_kind_or_severity(self) -> None:
        self.assertFalse(
            operator_action_required(
                "No immediate action required. Startup Warm is protecting dashboard requests."
            )
        )
        self.assertFalse(operator_action_required("No action required. Startup Warm is active."))
        self.assertFalse(operator_action_required(""))
        self.assertFalse(operator_action_required(None))
        self.assertTrue(operator_action_required("Verify Startup Warm completed successfully."))
        self.assertIn("dashboard_db_init_slow", _PLATFORM_ONLY_KINDS)
        no_action = {
            "kind": "dashboard_db_init_slow",
            "severity": "warning",
            "action_en": "No immediate action required. Startup Warm is protecting dashboard requests.",
        }
        action = {
            "kind": "dashboard_db_init_slow",
            "severity": "warning",
            "action_en": "Verify Startup Warm completed successfully.",
        }
        empty_rule = {
            "kind": "dashboard_db_init_slow",
            "severity": "critical",
            "action_en": "",
        }
        act, mon = split_platform_alerts_by_action(
            {"alerts": [no_action, action, empty_rule]}
        )
        self.assertEqual([a["action_en"] for a in act], [action["action_en"]])
        self.assertEqual(len(mon), 2)
        self.assertIn(no_action, mon)
        self.assertIn(empty_rule, mon)

    def test_count_equals_actionable_lists(self) -> None:
        present = build_operations_center_v11_presentation(
            store_action_center={
                "summary": {
                    "production_store_count": 12,
                    "production_affected_count": 2,
                },
                "production_action_queue": [
                    {
                        "has_issues": True,
                        "priority": "HIGH",
                        "store_slug": "a",
                        "root_causes": [
                            {
                                "root_cause_id": "ROOT_CAUSE_WIDGET_RUNTIME",
                                "symptom_kinds": ["runtime_beacon_missing"],
                            }
                        ],
                    },
                    {
                        "has_issues": True,
                        "priority": "LOW",
                        "store_slug": "b",
                        "root_causes": [],
                    },
                ],
            },
            critical_alerts={
                "alerts": [
                    {
                        "kind": "dashboard_db_init_slow",
                        "action_en": (
                            "No immediate action required. "
                            "Startup Warm is protecting dashboard requests."
                        ),
                    }
                ]
            },
            recovery_resume_health={"running": 0},
            generated_at_utc="2026-08-28T00:00:00+00:00",
        )
        self.assertEqual(
            present["intervention_count"],
            len(present["intervention_stores"]) + len(present["actionable_platform_alerts"]),
        )
        self.assertEqual(present["intervention_count"], 1)
        self.assertEqual(present["actionable_platform_alerts"], [])
        self.assertEqual(len(present["monitoring_platform_alerts"]), 1)
        self.assertEqual(present["monitoring_count"], 1)
        self.assertEqual(present["scoped_observation_headline_ar"], "الرصد غير مكتمل لمتجر واحد")
        self.assertEqual(present["retry_label_ar"], "غير مفعّلة")
        self.assertEqual(present["schedule_running"], 0)
        self.assertIn("أغسطس", present["generated_at_ar"])
        self.assertEqual(present["evidence_freshness_utc"], None)
        self.assertEqual(
            present["evidence_freshness_missing_sources"],
            ["store_action_center", "critical_alerts", "recovery_resume_health"],
        )

    def test_missing_numeric_evidence_is_not_coerced_to_zero(self) -> None:
        self.assertIsNone(explicit_int({}, "running"))
        self.assertIsNone(explicit_int({"running": None}, "running"))
        self.assertEqual(explicit_int({"running": 0}, "running"), 0)
        present = build_operations_center_v11_presentation(
            store_action_center={"summary": {}, "production_action_queue": []},
            critical_alerts={"alerts": []},
            recovery_resume_health={},
            generated_at_utc="2026-08-28T00:00:00+00:00",
        )
        self.assertIsNone(present["production_store_count"])
        self.assertIsNone(present["production_affected_count"])
        self.assertIsNone(present["schedule_running"])
        present_zero = build_operations_center_v11_presentation(
            store_action_center={
                "summary": {"production_store_count": 0, "production_affected_count": 0},
                "production_action_queue": [],
            },
            critical_alerts={"alerts": []},
            recovery_resume_health={"running": 0},
            generated_at_utc="2026-08-28T00:00:00+00:00",
        )
        self.assertEqual(present_zero["production_store_count"], 0)
        self.assertEqual(present_zero["production_affected_count"], 0)
        self.assertEqual(present_zero["schedule_running"], 0)

    def test_headline_empty_when_no_widget_observation(self) -> None:
        self.assertEqual(scoped_observation_headline_ar(0), "")
        self.assertEqual(format_generated_at_ar(""), "")


if __name__ == "__main__":
    unittest.main()
