# -*- coding: utf-8 -*-
"""Tests for Admin Operations V3 Store Action Center."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from services.admin_operations_store_action_center_v1 import (
    build_store_action_center_readonly,
)


class StoreActionCenterTests(unittest.TestCase):
    def test_healthy_when_no_store_issues(self) -> None:
        payload = build_store_action_center_readonly(store_rows=[], alerts=[])
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["stores"], [])
        self.assertIn(
            "No stores currently require operational intervention",
            payload["healthy"]["message_en"],
        )

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
        store = payload["stores"][0]
        self.assertEqual(store["store_slug"], "store_a")
        issue = store["primary_issue"]
        self.assertEqual(issue["kind"], "widget_runtime_missing")
        self.assertIn("runtime not detected", issue["problem_en"].lower())
        self.assertIn("runtime connectivity", issue["action_en"].lower())

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
        by_slug = {s["store_slug"]: s for s in payload["stores"]}
        store_b_kinds = {i["kind"] for i in by_slug["store_b"]["issues"]}
        self.assertIn("whatsapp_missing", store_b_kinds)
        self.assertIn("store_needs_setup", store_b_kinds)
        whatsapp = next(i for i in by_slug["store_b"]["issues"] if i["kind"] == "whatsapp_missing")
        self.assertEqual(whatsapp["where_en"], "WhatsApp Readiness")
        self.assertIn("setup is incomplete", by_slug["store_c"]["primary_issue"]["problem_en"].lower())

    def test_store_identity_from_truth_status(self) -> None:
        store_rows = [
            {
                "store_slug": "store_d",
                "display_name": "Store D",
                "ready": True,
                "whatsapp_missing": False,
                "widget_runtime_truth_status": "mismatch",
            }
        ]
        with patch(
            "services.widget_health_v1.build_admin_widget_health_section_readonly",
            return_value={"issues": []},
        ):
            payload = build_store_action_center_readonly(
                store_rows=store_rows,
                alerts=[],
            )
        issue = payload["stores"][0]["primary_issue"]
        self.assertEqual(issue["kind"], "store_identity_mismatch")
        self.assertEqual(issue["where_en"], "Store Identity")
        self.assertIn("identity mapping", issue["action_en"].lower())

    def test_multiple_stores_sorted_critical_first(self) -> None:
        store_rows = [
            {"store_slug": "warn_store", "display_name": "Warn", "ready": True, "whatsapp_missing": True},
            {"store_slug": "crit_store", "display_name": "Crit", "ready": True, "whatsapp_missing": False},
        ]
        widget_health = {
            "issues": [
                {
                    "kind": "widget_module_failed",
                    "severity": "critical",
                    "store_slug": "crit_store",
                    "store_name": "Crit",
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
        self.assertEqual(payload["stores"][0]["store_slug"], "crit_store")
        self.assertEqual(payload["stores"][0]["highest_severity"], "critical")
        self.assertEqual(payload["summary"]["affected_count"], 2)


if __name__ == "__main__":
    unittest.main()
