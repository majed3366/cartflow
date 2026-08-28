# -*- coding: utf-8 -*-
"""Presentation projection for Operations Center V1.1 — no new eligibility."""
from __future__ import annotations

import unittest

from services.admin_operations_center_v11_present_v1 import (
    build_operations_center_v11_presentation,
    format_generated_at_ar,
    scoped_observation_headline_ar,
    split_intervention_queues,
)
from services.admin_operations_operational_priority_v1 import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    apply_store_operational_priority,
)


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

    def test_count_equals_list(self) -> None:
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
            critical_alerts={"alerts": []},
            recovery_resume_health={"running": 0},
            generated_at_utc="2026-08-28T00:00:00+00:00",
        )
        self.assertEqual(present["intervention_count"], len(present["intervention_stores"]))
        self.assertEqual(present["intervention_count"], 1)
        self.assertEqual(present["monitoring_count"], 1)
        self.assertEqual(present["scoped_observation_headline_ar"], "الرصد غير مكتمل لمتجر واحد")
        self.assertEqual(present["retry_label_ar"], "غير مفعّلة")
        self.assertEqual(present["schedule_running"], 0)
        self.assertIn("أغسطس", present["generated_at_ar"])

    def test_headline_empty_when_no_widget_observation(self) -> None:
        self.assertEqual(scoped_observation_headline_ar(0), "")
        self.assertEqual(format_generated_at_ar(""), "")


if __name__ == "__main__":
    unittest.main()
