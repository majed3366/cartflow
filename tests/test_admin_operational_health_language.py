# -*- coding: utf-8 -*-
"""Standard operational decision format for admin health cards."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_operational_health_language import (
    DECISION_FIELD_LABELS_AR,
    build_db_due_scanner_operational_layer,
    build_standard_operational_decision,
    enrich_db_due_scanner_admin_card,
    enrich_operational_health_cards,
)
from services.admin_operational_health import build_admin_operational_health_readonly
from services.db_due_scanner_health import clear_db_due_scanner_health_for_tests

_EXPECTED_LABELS = [label for _, label in DECISION_FIELD_LABELS_AR]


class AdminOperationalHealthLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_db_due_scanner_health_for_tests()
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)

    def test_decision_field_order_fixed(self) -> None:
        op = build_standard_operational_decision(
            title_ar="اختبار",
            status_tier="ok",
            risk_level="none",
            customer_impact_ar="لا",
            merchant_impact_ar="لا",
            intervention="no",
            suggested_action_ar="لا حاجة لأي تدخل",
            last_success_ar="—",
        )
        self.assertEqual([r["label_ar"] for r in op["rows"]], _EXPECTED_LABELS)
        self.assertEqual(op["rows"][0]["value_ar"], "🟢 يعمل طبيعي")
        self.assertEqual(op["rows"][1]["value_ar"], "لا يوجد")
        self.assertEqual(op["rows"][4]["value_ar"], "لا")

    def test_scanner_operational_decision_healthy(self) -> None:
        card = enrich_db_due_scanner_admin_card(
            {
                "enabled": True,
                "status": "healthy",
                "status_emoji": "🟢",
                "status_label": "healthy",
                "loop_running": True,
                "total_dispatches": 3,
                "last_error": None,
                "last_found": 0,
                "interval_seconds": 30,
                "last_dispatch_ago": "3 min ago",
            }
        )
        op = card["operational"]
        self.assertEqual(op["title_ar"], "فحص المهام المؤجلة")
        self.assertIn("يعمل طبيعي", op["rows"][0]["value_ar"])
        self.assertEqual(op["rows"][1]["value_ar"], "لا يوجد")
        self.assertEqual(op["rows"][2]["value_ar"], "لا")
        tech = "\n".join(card["technical_detail_lines"])
        self.assertIn("loop_running:", tech)
        self.assertIn("found:", tech)

    def test_all_cards_have_eight_decision_rows(self) -> None:
        payload = build_admin_operational_health_readonly()
        for key in ("db_due_scanner", "cart_event", "db_pool", "background_tasks", "whatsapp"):
            card = payload["cards"][key]
            rows = (card.get("operational") or {}).get("rows") or []
            self.assertEqual(len(rows), 8, msg=key)
            self.assertEqual([r["label_ar"] for r in rows], _EXPECTED_LABELS, msg=key)

    def test_visual_html_decision_format(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "ops-decision-visual-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={
                "password": "ops-decision-visual-pass",
                "next": "/admin/operational-health",
            },
        )
        html = client.get("/admin/operational-health").text
        self.assertEqual(client.get("/admin/operational-health").status_code, 200)
        self.assertIn("مركز التحكم التشغيلي", html)
        for label in _EXPECTED_LABELS:
            self.assertIn(label, html, msg=f"missing label: {label}")
        # Per-card technical collapsed (5 cards)
        self.assertEqual(html.count("تفاصيل تقنية (للدعم)"), 5)
        # Operational titles
        for title in (
            "فحص المهام المؤجلة",
            "استقبال أحداث السلة",
            "اتصالات قاعدة البيانات",
            "المهام الخلفية والاسترداد",
            "إرسال واتساب",
        ):
            self.assertIn(title, html, msg=title)
        # Decision rows order in first card (before next card title)
        block = html.split("فحص المهام المؤجلة", 1)[1].split("استقبال أحداث السلة", 1)[0]
        positions = [block.find(label) for label in _EXPECTED_LABELS]
        self.assertTrue(all(p >= 0 for p in positions), msg=positions)
        self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
