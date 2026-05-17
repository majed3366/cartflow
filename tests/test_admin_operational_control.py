# -*- coding: utf-8 -*-
"""Admin operational control v2 — modular read-only layers."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_operational_control import (
    build_admin_operational_control_readonly,
    clear_verification_state_for_tests,
)
from services.admin_operational_health import (
    clear_operational_health_buffers_for_tests,
    record_cart_event_finish_sample,
    record_db_pool_timeout,
)


class AdminOperationalControlV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._prev_admin = os.environ.get("CARTFLOW_ADMIN_PASSWORD")
        self._prev_secret = os.environ.get("SECRET_KEY")
        clear_operational_health_buffers_for_tests()
        clear_verification_state_for_tests()

    def tearDown(self) -> None:
        clear_operational_health_buffers_for_tests()
        clear_verification_state_for_tests()
        if self._prev_admin is not None:
            os.environ["CARTFLOW_ADMIN_PASSWORD"] = self._prev_admin
        else:
            os.environ.pop("CARTFLOW_ADMIN_PASSWORD", None)
        if self._prev_secret is not None:
            os.environ["SECRET_KEY"] = self._prev_secret
        else:
            os.environ.pop("SECRET_KEY", None)

    def test_v2_modules_present(self) -> None:
        p = build_admin_operational_control_readonly()
        self.assertEqual(p.get("version"), "admin_operational_control_v2")
        for key in (
            "admin_risk_summary",
            "admin_impact_layer",
            "admin_actions_layer",
            "admin_verification_layer",
            "admin_revenue_protection",
            "admin_operational_timeline",
            "quick_answers",
        ):
            self.assertIn(key, p)

    def test_risk_detected_on_pool_timeout(self) -> None:
        record_db_pool_timeout(detail="QueuePool limit")
        p = build_admin_operational_control_readonly()
        risk = p["admin_risk_summary"]
        self.assertTrue(risk.get("risk_detected"))
        self.assertIn("🔴", risk.get("status_emoji", ""))

    def test_verification_after_issue_clears(self) -> None:
        record_db_pool_timeout(detail="t1")
        build_admin_operational_control_readonly()
        clear_operational_health_buffers_for_tests()
        verify = build_admin_operational_control_readonly()["admin_verification_layer"]
        self.assertTrue(verify.get("has_recoveries"))

    def test_page_renders_control_v2(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "control-v2-test-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={
                "password": "control-v2-test-pass",
                "next": "/admin/operational-health",
            },
        )
        r = client.get("/admin/operational-health")
        self.assertEqual(r.status_code, 200, r.text[:500])
        body = r.text
        self.assertIn("التحكم التشغيلي", body)
        self.assertIn("طبقة الأثر", body)
        self.assertIn("إجراء مقترح", body)
        self.assertIn("الخط الزمني", body)
        self.assertIn("حماية الإيراد", body)
        self.assertIn("هل النظام سليم", body)
