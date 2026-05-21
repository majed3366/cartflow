# -*- coding: utf-8 -*-
"""Standard operational decision format for admin health cards."""

from __future__ import annotations

import os
import re
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_operational_health_language import (
    DECISION_FIELD_LABELS_AR,
    TITLE_AUTO_RECOVERY_AR,
    TITLE_CUSTOMER_ACTIVITY_AR,
    TITLE_CUSTOMER_COMMS_AR,
    TITLE_DELAYED_RECOVERY_AR,
    TITLE_INTERNAL_HEALTH_AR,
    build_standard_operational_decision,
    enrich_db_due_scanner_admin_card,
    enrich_operational_health_cards,
)
from services.admin_operational_health import build_admin_operational_health_readonly
from services.db_due_scanner_health import clear_db_due_scanner_health_for_tests

_EXPECTED_LABELS = [label for _, label in DECISION_FIELD_LABELS_AR]
_OPERATIONAL_TITLES = (
    TITLE_DELAYED_RECOVERY_AR,
    TITLE_CUSTOMER_ACTIVITY_AR,
    TITLE_INTERNAL_HEALTH_AR,
    TITLE_AUTO_RECOVERY_AR,
    TITLE_CUSTOMER_COMMS_AR,
)
_ENGINEERING_IN_LAYER1 = re.compile(
    r"QueuePool|cart-event|DB Due Scanner|loop_running|db_pool",
    re.IGNORECASE,
)


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

    def test_operational_layer_avoids_engineering_terms(self) -> None:
        payload = build_admin_operational_health_readonly()
        for key in ("db_due_scanner", "cart_event", "db_pool", "background_tasks", "whatsapp"):
            card = payload["cards"][key]
            op = card.get("operational") or {}
            blob = " ".join(
                str(op.get(k, "")) for k in op
            ) + " ".join(r.get("value_ar", "") for r in op.get("rows") or [])
            self.assertIsNone(
                _ENGINEERING_IN_LAYER1.search(blob),
                msg=f"{key} layer1 leaked engineering term: {blob[:200]}",
            )
            tech = "\n".join(card.get("technical_detail_lines") or [])
            self.assertTrue(
                len(tech) > 10,
                msg=f"{key} should keep technical lines",
            )

    def test_renamed_card_titles(self) -> None:
        payload = build_admin_operational_health_readonly()
        titles = {
            (payload["cards"][k].get("operational") or {}).get("title_ar")
            for k in ("db_due_scanner", "cart_event", "db_pool", "background_tasks", "whatsapp")
        }
        self.assertEqual(titles, set(_OPERATIONAL_TITLES))

    def test_visual_html_operations_wording(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "ops-wording-visual-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={
                "password": "ops-wording-visual-pass",
                "next": "/admin/operational-health",
            },
        )
        html = client.get("/admin/operational-health").text
        self.assertEqual(client.get("/admin/operational-health").status_code, 200)
        self.assertIn("مركز التحكم التشغيلي", html)
        self.assertIn("هل النظام يعمل طبيعي؟", html)
        self.assertIn("هل المتاجر متأثرة؟", html)
        self.assertIn("ماذا نفعل الآن؟", html)
        for title in _OPERATIONAL_TITLES:
            self.assertIn(title, html, msg=title)
        self.assertNotIn("استقبال أحداث السلة", html)
        self.assertNotIn("المهام الخلفية والاسترداد", html)
        self.assertNotIn("اتصالات قاعدة البيانات", html)
        self.assertEqual(html.count("تفاصيل تقنية (للدعم)"), 5)
        # Technical terms only in support blocks
        main = html.split("مركز التحكم التشغيلي", 1)[1]
        pre_details = main.split("تفاصيل تقنية (للدعم)")[0]
        self.assertNotIn("QueuePool", pre_details)
        self.assertIn("QueuePool", html)


if __name__ == "__main__":
    unittest.main()
