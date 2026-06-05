# -*- coding: utf-8 -*-
"""Tests for Admin Operations V3 Store Action Center."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from services.admin_operations_production_truth_v1 import classify_store_environment
from services.admin_operations_store_action_center_v1 import (
    build_store_action_center_readonly,
)


class StoreActionCenterTests(unittest.TestCase):
    def test_healthy_when_no_store_issues(self) -> None:
        payload = build_store_action_center_readonly(store_rows=[], alerts=[])
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["stores"], [])
        self.assertIn(
            "No production stores currently require intervention",
            payload["healthy"]["message_en"],
        )

    def test_classify_demo_test_stores(self) -> None:
        self.assertEqual(classify_store_environment("loadtest-store-013"), "demo_test")
        self.assertEqual(classify_store_environment("demo2"), "demo_test")
        self.assertEqual(classify_store_environment("sandbox-shop"), "demo_test")
        self.assertEqual(classify_store_environment("merchant-real"), "production")

    def test_production_healthy_when_only_demo_affected(self) -> None:
        store_rows = [
            {
                "store_slug": "loadtest-store-013",
                "display_name": "CartFlow 013",
                "ready": False,
                "whatsapp_missing": True,
            },
            {
                "store_slug": "merchant-vip",
                "display_name": "CartFlow VIP",
                "ready": True,
                "whatsapp_missing": False,
            },
        ]
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value={"issues": []},
        ):
            payload = build_store_action_center_readonly(
                store_rows=store_rows,
                alerts=[],
            )
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["summary"]["production_affected_count"], 0)
        self.assertEqual(payload["summary"]["demo_test_affected_count"], 1)
        demo_slugs = [s["store_slug"] for s in payload["demo_test_queue"]]
        prod_slugs = [s["store_slug"] for s in payload["production_queue"]]
        self.assertIn("loadtest-store-013", demo_slugs)
        self.assertIn("merchant-vip", prod_slugs)
        self.assertFalse(payload["production_queue"][0]["has_issues"])

    def test_widget_runtime_issue_per_store(self) -> None:
        store_rows = [
            {
                "store_slug": "store_a",
                "display_name": "Store A",
                "ready": True,
                "whatsapp_missing": False,
            }
        ]
        widget_health = {
            "issues": [
                {
                    "kind": "runtime_beacon_missing",
                    "severity": "warning",
                    "store_slug": "store_a",
                    "store_name": "Store A",
                }
            ]
        }
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value=widget_health,
        ):
            payload = build_store_action_center_readonly(
                store_rows=store_rows,
                alerts=[],
            )
        self.assertEqual(payload["status"], "affected")
        self.assertEqual(len(payload["stores"]), 1)
        store = payload["production_queue"][0]
        self.assertEqual(store["store_slug"], "store_a")
        self.assertTrue(store["has_issues"])
        self.assertEqual(store["root_cause_count_label"], "1 Root Cause")
        self.assertEqual(store["root_cause_count"], 1)
        rc = store["primary_root_cause"]
        self.assertEqual(rc["root_cause_id"], "ROOT_CAUSE_WIDGET_RUNTIME")
        self.assertEqual(rc["display_name_en"], "Widget Runtime Missing")
        self.assertEqual(store["priority"], "HIGH")
        self.assertEqual(store["priority_display_en"], "⚠ Needs Review")
        self.assertEqual(store["primary_root_cause_name_en"], "Widget Runtime Missing")

    def test_whatsapp_and_setup_issues(self) -> None:
        store_rows = [
            {
                "store_slug": "store_b",
                "display_name": "Store B",
                "ready": False,
                "whatsapp_missing": True,
            },
            {
                "store_slug": "store_c",
                "display_name": "Store C",
                "ready": False,
                "whatsapp_missing": False,
            },
        ]
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value={"issues": []},
        ):
            payload = build_store_action_center_readonly(
                store_rows=store_rows,
                alerts=[],
            )
        by_slug = {s["store_slug"]: s for s in payload["production_queue"]}
        store_b = by_slug["store_b"]
        rc_ids = {rc["root_cause_id"] for rc in store_b["root_causes"]}
        self.assertIn("ROOT_CAUSE_WHATSAPP", rc_ids)
        self.assertIn("ROOT_CAUSE_ONBOARDING", rc_ids)
        self.assertEqual(store_b["root_cause_count_label"], "2 Root Causes")

    def test_critical_issue_count_label(self) -> None:
        store_rows = [
            {
                "store_slug": "crit_store",
                "display_name": "CartFlow VIP",
                "ready": True,
                "whatsapp_missing": False,
            }
        ]
        widget_health = {
            "issues": [
                {
                    "kind": "widget_module_failed",
                    "severity": "critical",
                    "store_slug": "crit_store",
                    "store_name": "CartFlow VIP",
                }
            ]
        }
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value=widget_health,
        ):
            payload = build_store_action_center_readonly(
                store_rows=store_rows,
                alerts=[],
            )
        store = payload["production_queue"][0]
        self.assertEqual(store["root_cause_count_label"], "1 Root Cause")
        self.assertEqual(store["highest_severity"], "critical")
        self.assertEqual(store["root_causes"][0]["severity"], "critical")
        self.assertEqual(store["priority"], "CRITICAL")
        self.assertEqual(store["priority_display_en"], "🔥 Requires Immediate Action")

    def test_production_action_queue_excludes_healthy(self) -> None:
        store_rows = [
            {
                "store_slug": "healthy_prod",
                "display_name": "Healthy Prod",
                "ready": True,
                "whatsapp_missing": False,
            },
            {
                "store_slug": "needs_action",
                "display_name": "Needs Action",
                "ready": False,
                "whatsapp_missing": False,
            },
        ]
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value={"issues": []},
        ):
            payload = build_store_action_center_readonly(
                store_rows=store_rows,
                alerts=[],
            )
        action_slugs = [s["store_slug"] for s in payload["production_action_queue"]]
        self.assertEqual(action_slugs, ["needs_action"])
        self.assertEqual(payload["summary"]["affected_count"], 1)

    def test_widget_runtime_symptoms_grouped_in_store_row(self) -> None:
        store_rows = [
            {
                "store_slug": "store_x",
                "display_name": "مساعد المتجر",
                "ready": True,
                "whatsapp_missing": False,
            }
        ]
        widget_health = {
            "issues": [
                {
                    "kind": "widget_not_seen",
                    "severity": "warning",
                    "store_slug": "store_x",
                    "store_name": "مساعد المتجر",
                },
                {
                    "kind": "runtime_beacon_missing",
                    "severity": "warning",
                    "store_slug": "store_x",
                    "store_name": "مساعد المتجر",
                },
            ]
        }
        alerts = [
            {
                "kind": "no_cart_events",
                "severity": "low",
                "records": [
                    {
                        "store_slug": "store_x",
                        "store_name": "مساعد المتجر",
                    }
                ],
            }
        ]
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value=widget_health,
        ):
            payload = build_store_action_center_readonly(
                store_rows=store_rows,
                alerts=alerts,
            )
        store = payload["production_action_queue"][0]
        self.assertEqual(store["root_cause_count"], 1)
        self.assertEqual(store["root_cause_count_label"], "1 Root Cause")
        rc = store["root_causes"][0]
        self.assertEqual(rc["display_name_en"], "Widget Runtime Missing")
        self.assertEqual(
            set(rc["affected_signals"]),
            {"Widget Visibility", "Runtime Beacon", "Cart Events"},
        )
        self.assertEqual(payload["summary"]["root_cause_count"], 1)
        self.assertEqual(payload["summary"]["warning_root_cause_count"], 1)
        self.assertEqual(store["priority"], "HIGH")
        self.assertEqual(payload["summary"]["high_priority_store_count"], 1)

    def test_queue_sorted_critical_before_high(self) -> None:
        store_rows = [
            {
                "store_slug": "high_store",
                "display_name": "Alpha High",
                "ready": True,
                "whatsapp_missing": False,
            },
            {
                "store_slug": "crit_store",
                "display_name": "Zulu Critical",
                "ready": True,
                "whatsapp_missing": False,
                "widget_runtime_truth_status": "mismatch",
            },
        ]
        widget_health = {
            "issues": [
                {
                    "kind": "runtime_beacon_missing",
                    "severity": "warning",
                    "store_slug": "high_store",
                    "store_name": "Alpha High",
                }
            ]
        }
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value=widget_health,
        ):
            payload = build_store_action_center_readonly(
                store_rows=store_rows,
                alerts=[],
            )
        queue = payload["production_action_queue"]
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue[0]["store_slug"], "crit_store")
        self.assertEqual(queue[0]["priority"], "CRITICAL")
        self.assertEqual(queue[1]["store_slug"], "high_store")
        self.assertEqual(queue[1]["priority"], "HIGH")
        self.assertEqual(payload["summary"]["critical_priority_store_count"], 1)
        self.assertEqual(payload["summary"]["high_priority_store_count"], 1)


if __name__ == "__main__":
    unittest.main()
