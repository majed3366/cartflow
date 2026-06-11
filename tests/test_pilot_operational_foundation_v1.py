# -*- coding: utf-8 -*-
"""Tests for Pilot Operational Visibility Foundation v1."""
from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.cartflow_admin_http_auth import admin_cookie_name
from services.pilot_operational_foundation_mapping_v1 import (
    HEALTHY_PROBLEM_AR,
    classify_action_required,
    compose_last_activity_fields,
    format_relative_activity_ar,
    issue_title_ar,
    priority_from_ops_row,
    resolve_pilot_owner,
    status_from_severity,
)
from services.pilot_operational_foundation_v1 import build_pilot_operational_foundation_readonly

REQUIRED_STORE_FIELDS = (
    "store_slug",
    "store_name_ar",
    "status",
    "primary_reason",
    "priority",
    "owner",
    "recommended_action_ar",
    "action_required",
    "last_activity_at",
    "last_activity_display_ar",
    "last_cart_event_at",
    "last_recovery_at",
)


def _assert_no_status_reason(obj: object) -> None:
    if isinstance(obj, dict):
        assert "status_reason" not in obj
        for value in obj.values():
            _assert_no_status_reason(value)
    elif isinstance(obj, list):
        for item in obj:
            _assert_no_status_reason(item)


class PilotOperationalFoundationMappingTests(unittest.TestCase):
    def test_status_arabic_labels(self) -> None:
        healthy = status_from_severity("healthy", has_issues=False)
        self.assertEqual(healthy["label_ar"], "سليم")
        warning = status_from_severity("warning", has_issues=True)
        self.assertEqual(warning["label_ar"], "يحتاج متابعة")
        critical = status_from_severity("critical", has_issues=True)
        self.assertEqual(critical["label_ar"], "حرج")

    def test_priority_from_ops_row(self) -> None:
        high = priority_from_ops_row({"priority": "CRITICAL", "has_issues": True})
        self.assertEqual(high["label_ar"], "مرتفعة")
        low = priority_from_ops_row({"priority": "LOW", "has_issues": False})
        self.assertEqual(low["label_ar"], "منخفضة")

    def test_action_required_rules(self) -> None:
        self.assertFalse(
            classify_action_required(
                status_key="healthy",
                owner_key="merchant",
                issue_code="whatsapp_missing",
                recommended_action_ar="x",
            )
        )
        self.assertTrue(
            classify_action_required(
                status_key="warning",
                owner_key="merchant",
                issue_code="whatsapp_missing",
                recommended_action_ar="اطلب من التاجر ربط واتساب.",
            )
        )
        self.assertFalse(
            classify_action_required(
                status_key="warning",
                owner_key="meta",
                issue_code="template_approval_pending",
                recommended_action_ar="انتظار اعتماد القالب من ميتا.",
            )
        )

    def test_last_activity_no_timestamps(self) -> None:
        activity = compose_last_activity_fields(
            last_cart_event_at="غير متوفر",
            last_recovery_at=None,
            widget_last_seen_at=None,
        )
        self.assertIsNone(activity["last_activity_at"])
        self.assertEqual(activity["last_activity_display_ar"], "لا يوجد نشاط")

    def test_last_activity_max_composition(self) -> None:
        now = datetime(2026, 6, 11, 12, 0, 0)
        cart = (now - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M")
        recovery = (now - timedelta(hours=2)).isoformat() + "Z"
        activity = compose_last_activity_fields(
            last_cart_event_at=cart,
            last_recovery_at=recovery,
            widget_last_seen_at=None,
            now=now,
        )
        self.assertEqual(activity["last_activity_display_ar"], "آخر نشاط قبل 5 دقائق")
        self.assertTrue(str(activity["last_activity_at"]).endswith("Z"))

    def test_issue_title_ar_whatsapp(self) -> None:
        self.assertEqual(issue_title_ar("whatsapp_missing"), "واتساب غير مربوط")

    def test_owner_whatsapp_defaults_merchant_for_missing(self) -> None:
        owner = resolve_pilot_owner("whatsapp_missing", provider_readiness={"provider": "twilio"})
        self.assertEqual(owner["label_ar"], "صاحب المتجر")


class PilotOperationalFoundationComposerTests(unittest.TestCase):
    def test_payload_top_level_contract(self) -> None:
        payload = build_pilot_operational_foundation_readonly()
        self.assertEqual(payload.get("version"), "pilot_operational_foundation_v1")
        self.assertIn("generated_at", payload)
        self.assertIn("ok", payload)
        self.assertIn("pilot_health_overview", payload)
        self.assertIn("attention_queue", payload)
        self.assertIn("top_operational_issues", payload)
        self.assertIn("stores", payload)
        self.assertIn("meta", payload)
        _assert_no_status_reason(payload)

    def test_store_rows_have_required_fields(self) -> None:
        payload = build_pilot_operational_foundation_readonly()
        for row in payload.get("stores") or []:
            for field in REQUIRED_STORE_FIELDS:
                self.assertIn(field, row)
            self.assertIn("primary_reason", row)
            self.assertIn("problem_ar", row["primary_reason"])
            self.assertIn("label_ar", row["status"])
            self.assertIn("label_ar", row["priority"])
            self.assertIn("label_ar", row["owner"])
            self.assertIsInstance(row["action_required"], bool)

    def test_healthy_store_row_when_no_production_issues(self) -> None:
        store_rows = [
            {
                "store_id": 1,
                "store_slug": "merchant-vip",
                "display_name": "VIP",
                "ready": True,
                "whatsapp_missing": False,
                "blocking_steps": [],
                "last_cart_event_at": "غير متوفر",
                "widget_last_seen_at": "غير متوفر",
            }
        ]
        sac = {
            "production_queue": [
                {
                    "store_slug": "merchant-vip",
                    "store_name": "VIP",
                    "highest_severity": "healthy",
                    "has_issues": False,
                    "priority": "LOW",
                    "priority_rank": 99,
                    "issues": [],
                }
            ],
            "demo_test_queue": [],
        }
        with patch(
            "services.admin_operations_center_v1._build_ops_shared_context",
            return_value={"store_rows": store_rows, "alerts": []},
        ), patch(
            "services.admin_operations_store_action_center_v1.build_store_action_center_readonly",
            return_value=sac,
        ), patch(
            "services.pilot_operational_foundation_v1._load_store_orm_by_id",
            return_value={},
        ), patch(
            "services.pilot_operational_foundation_v1._provider_readiness_snapshot",
            return_value={},
        ):
            payload = build_pilot_operational_foundation_readonly()
        row = payload["stores"][0]
        self.assertEqual(row["status"]["key"], "healthy")
        self.assertEqual(row["primary_reason"]["problem_ar"], HEALTHY_PROBLEM_AR)
        self.assertFalse(row["action_required"])

    def test_merchant_issue_action_required(self) -> None:
        store_rows = [
            {
                "store_id": 2,
                "store_slug": "merchant-a",
                "display_name": "A",
                "ready": False,
                "whatsapp_missing": True,
                "blocking_steps": ["whatsapp_not_connected"],
                "last_cart_event_at": "غير متوفر",
            }
        ]
        sac = {
            "production_queue": [
                {
                    "store_slug": "merchant-a",
                    "store_name": "A",
                    "highest_severity": "warning",
                    "has_issues": True,
                    "priority": "HIGH",
                    "priority_rank": 1,
                    "primary_issue": {"kind": "whatsapp_missing", "severity": "warning"},
                    "issues": [{"kind": "whatsapp_missing", "severity": "warning"}],
                }
            ],
            "demo_test_queue": [],
        }
        with patch(
            "services.admin_operations_center_v1._build_ops_shared_context",
            return_value={"store_rows": store_rows, "alerts": []},
        ), patch(
            "services.admin_operations_store_action_center_v1.build_store_action_center_readonly",
            return_value=sac,
        ), patch(
            "services.pilot_operational_foundation_v1._load_store_orm_by_id",
            return_value={},
        ), patch(
            "services.pilot_operational_foundation_v1._provider_readiness_snapshot",
            return_value={"provider": "twilio"},
        ):
            payload = build_pilot_operational_foundation_readonly()
        row = payload["stores"][0]
        self.assertTrue(row["action_required"])
        self.assertEqual(row["owner"]["label_ar"], "صاحب المتجر")

    def test_demo_excluded_from_headline_counts(self) -> None:
        store_rows = [
            {
                "store_id": 1,
                "store_slug": "loadtest-store-013",
                "display_name": "Demo",
                "ready": False,
                "whatsapp_missing": True,
                "blocking_steps": ["whatsapp_not_connected"],
            },
            {
                "store_id": 2,
                "store_slug": "merchant-real",
                "display_name": "Real",
                "ready": True,
                "whatsapp_missing": False,
                "blocking_steps": [],
            },
        ]
        sac = {
            "production_queue": [
                {
                    "store_slug": "merchant-real",
                    "store_name": "Real",
                    "highest_severity": "healthy",
                    "has_issues": False,
                    "priority": "LOW",
                    "priority_rank": 99,
                    "issues": [],
                }
            ],
            "demo_test_queue": [
                {
                    "store_slug": "loadtest-store-013",
                    "store_name": "Demo",
                    "highest_severity": "warning",
                    "has_issues": True,
                    "priority": "HIGH",
                    "priority_rank": 1,
                    "primary_issue": {"kind": "whatsapp_missing", "severity": "warning"},
                    "issues": [{"kind": "whatsapp_missing", "severity": "warning"}],
                }
            ],
        }
        with patch(
            "services.admin_operations_center_v1._build_ops_shared_context",
            return_value={"store_rows": store_rows, "alerts": []},
        ), patch(
            "services.admin_operations_store_action_center_v1.build_store_action_center_readonly",
            return_value=sac,
        ), patch(
            "services.pilot_operational_foundation_v1._load_store_orm_by_id",
            return_value={},
        ), patch(
            "services.pilot_operational_foundation_v1._provider_readiness_snapshot",
            return_value={},
        ):
            payload = build_pilot_operational_foundation_readonly(include_demo=True)
        self.assertEqual(payload["pilot_health_overview"]["total_stores"], 1)
        self.assertEqual(len(payload["demo_stores"]), 1)
        self.assertEqual(payload["demo_stores"][0]["store_slug"], "loadtest-store-013")

    def test_attention_queue_sort_critical_before_warning(self) -> None:
        sac = {
            "production_queue": [
                {
                    "store_slug": "warn-store",
                    "store_name": "Warn",
                    "highest_severity": "warning",
                    "has_issues": True,
                    "priority": "MEDIUM",
                    "priority_rank": 2,
                    "primary_issue": {"kind": "no_cart_events", "severity": "warning"},
                    "issues": [{"kind": "no_cart_events", "severity": "warning"}],
                },
                {
                    "store_slug": "crit-store",
                    "store_name": "Crit",
                    "highest_severity": "critical",
                    "has_issues": True,
                    "priority": "CRITICAL",
                    "priority_rank": 0,
                    "primary_issue": {"kind": "failed_recovery", "severity": "critical"},
                    "issues": [{"kind": "failed_recovery", "severity": "critical"}],
                },
            ],
            "demo_test_queue": [],
        }
        with patch(
            "services.admin_operations_center_v1._build_ops_shared_context",
            return_value={"store_rows": [], "alerts": []},
        ), patch(
            "services.admin_operations_store_action_center_v1.build_store_action_center_readonly",
            return_value=sac,
        ), patch(
            "services.pilot_operational_foundation_v1._load_store_orm_by_id",
            return_value={},
        ), patch(
            "services.pilot_operational_foundation_v1._provider_readiness_snapshot",
            return_value={},
        ):
            payload = build_pilot_operational_foundation_readonly()
        slugs = [row["store_slug"] for row in payload["attention_queue"]]
        self.assertEqual(slugs[0], "crit-store")

    def test_admin_operations_command_center_unchanged(self) -> None:
        """Pilot foundation must not mutate admin ops center module surface."""
        import services.admin_operations_center_v1 as ops_center  # noqa: PLC0415

        payload = ops_center.build_admin_operations_command_center_readonly()
        self.assertEqual(payload.get("version"), "admin_operations_center_v2_5")
        self.assertIn("store_action_center", payload)
        self.assertIn("executive_summary", payload)
        self.assertTrue(callable(ops_center._build_ops_shared_context))
        self.assertTrue(callable(ops_center.build_admin_operations_command_center_readonly))


class PilotOperationalFoundationRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "pilot-foundation-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def _login(self) -> None:
        r = self.client.post(
            "/admin/operations/login",
            data={"password": "pilot-foundation-pass", "next": "/admin/operations"},
            follow_redirects=False,
        )
        self.assertEqual(r.status_code, 303, r.text[:300])

    def test_route_requires_auth(self) -> None:
        r = self.client.get("/api/admin/operations/pilot-foundation")
        self.assertEqual(r.status_code, 401)

    def test_route_returns_foundation_payload(self) -> None:
        self._login()
        r = self.client.get("/api/admin/operations/pilot-foundation")
        self.assertEqual(r.status_code, 200, r.text[:500])
        data = r.json()
        self.assertEqual(data.get("version"), "pilot_operational_foundation_v1")
        self.assertTrue(data.get("ok"))
        _assert_no_status_reason(data)
        cookie = self.client.cookies.get(admin_cookie_name())
        self.assertTrue(cookie)


if __name__ == "__main__":
    unittest.main()
