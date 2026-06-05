# -*- coding: utf-8 -*-
"""Tests for Admin Operations V3 Store Action Center."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from services.admin_operations_store_action_center_v1 import (
    build_store_action_center_readonly,
    classify_store_environment,
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
        self.assertEqual(store["issue_count_label"], "1 Issue")
        issue = store["primary_issue"]
        self.assertEqual(issue["kind"], "widget_runtime_missing")

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
        store_b_kinds = {i["kind"] for i in by_slug["store_b"]["issues"]}
        self.assertIn("whatsapp_missing", store_b_kinds)
        self.assertIn("store_needs_setup", store_b_kinds)
        self.assertEqual(by_slug["store_b"]["issue_count_label"], "2 Issues")

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
        self.assertEqual(store["issue_count_label"], "1 Critical")
        self.assertEqual(store["highest_severity"], "critical")


if __name__ == "__main__":
    unittest.main()
