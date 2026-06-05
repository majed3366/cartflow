# -*- coding: utf-8 -*-
"""Tests for Admin Operations V3.4 operational priority queue."""
from __future__ import annotations

import unittest

from services.admin_operations_operational_priority_v1 import (
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    apply_store_operational_priority,
    classify_root_cause_priority,
    sort_stores_by_operational_priority,
    summarize_operational_priority_stores,
)
from services.admin_operations_root_cause_groups_v1 import (
    ROOT_CAUSE_IDENTITY,
    ROOT_CAUSE_ONBOARDING,
    ROOT_CAUSE_WHATSAPP,
    ROOT_CAUSE_WIDGET_RUNTIME,
)


def _rc(group_id: str, *, kinds: list[str] | None = None, severity: str = "warning") -> dict:
    return {
        "root_cause_id": group_id,
        "display_name_en": group_id,
        "severity": severity,
        "symptom_kinds": kinds or [],
    }


class OperationalPriorityTests(unittest.TestCase):
    def test_root_cause_priority_rules(self) -> None:
        self.assertEqual(
            classify_root_cause_priority(_rc(ROOT_CAUSE_IDENTITY)),
            PRIORITY_CRITICAL,
        )
        self.assertEqual(
            classify_root_cause_priority(_rc(ROOT_CAUSE_WIDGET_RUNTIME)),
            PRIORITY_HIGH,
        )
        self.assertEqual(
            classify_root_cause_priority(
                _rc(ROOT_CAUSE_WHATSAPP, kinds=["whatsapp_missing"])
            ),
            PRIORITY_HIGH,
        )
        self.assertEqual(
            classify_root_cause_priority(
                _rc(ROOT_CAUSE_WHATSAPP, kinds=["provider_unavailable"])
            ),
            PRIORITY_CRITICAL,
        )
        self.assertEqual(
            classify_root_cause_priority(_rc(ROOT_CAUSE_ONBOARDING)),
            PRIORITY_MEDIUM,
        )

    def test_standalone_widget_module_failed_is_critical(self) -> None:
        rc = _rc(
            "ROOT_CAUSE_STANDALONE_widget_module_failed",
            kinds=["widget_module_failed"],
            severity="critical",
        )
        self.assertEqual(classify_root_cause_priority(rc), PRIORITY_CRITICAL)

    def test_store_priority_escalates_to_highest_urgency(self) -> None:
        row = {
            "store_slug": "mixed",
            "has_issues": True,
            "root_causes": [
                _rc(ROOT_CAUSE_ONBOARDING),
                _rc(ROOT_CAUSE_IDENTITY),
            ],
        }
        enriched = apply_store_operational_priority(row)
        self.assertEqual(enriched["priority"], PRIORITY_CRITICAL)
        self.assertEqual(enriched["priority_display_en"], "🔥 Requires Immediate Action")

    def test_store_row_includes_primary_root_cause_name(self) -> None:
        row = {
            "store_slug": "store_a",
            "has_issues": True,
            "root_causes": [
                {
                    "root_cause_id": ROOT_CAUSE_WIDGET_RUNTIME,
                    "display_name_en": "Widget Runtime Missing",
                    "severity": "warning",
                    "symptom_kinds": ["runtime_beacon_missing"],
                }
            ],
        }
        enriched = apply_store_operational_priority(row)
        self.assertEqual(enriched["priority"], PRIORITY_HIGH)
        self.assertEqual(enriched["priority_display_en"], "⚠ Needs Review")
        self.assertEqual(enriched["primary_root_cause_name_en"], "Widget Runtime Missing")

    def test_sort_by_priority_not_alphabetical(self) -> None:
        stores = [
            {
                "store_slug": "zulu",
                "store_name": "Zulu Shop",
                "has_issues": True,
                "priority_rank": 2,
                "priority": PRIORITY_MEDIUM,
            },
            {
                "store_slug": "alpha",
                "store_name": "Alpha Shop",
                "has_issues": True,
                "priority_rank": 0,
                "priority": PRIORITY_CRITICAL,
            },
            {
                "store_slug": "mike",
                "store_name": "Mike Shop",
                "has_issues": True,
                "priority_rank": 1,
                "priority": PRIORITY_HIGH,
            },
        ]
        ordered = sort_stores_by_operational_priority(stores)
        self.assertEqual([s["store_slug"] for s in ordered], ["alpha", "mike", "zulu"])

    def test_summarize_priority_stores(self) -> None:
        stores = [
            {"has_issues": True, "priority": PRIORITY_CRITICAL},
            {"has_issues": True, "priority": PRIORITY_HIGH},
            {"has_issues": True, "priority": PRIORITY_HIGH},
            {"has_issues": True, "priority": PRIORITY_MEDIUM},
            {"has_issues": False, "priority": PRIORITY_LOW},
        ]
        metrics = summarize_operational_priority_stores(stores)
        self.assertEqual(metrics["critical_priority_store_count"], 1)
        self.assertEqual(metrics["high_priority_store_count"], 2)
        self.assertEqual(metrics["medium_priority_store_count"], 1)
        self.assertEqual(metrics["monitoring_store_count"], 0)


if __name__ == "__main__":
    unittest.main()
