# -*- coding: utf-8 -*-
"""CartFlow Operations Center presentation layer."""

from __future__ import annotations

import os
import re
import unittest

from fastapi.testclient import TestClient

from main import app
from services.admin_operational_health_language import (
    OPS_CENTER_FIELD_LABELS_AR,
    TITLE_AUTO_RECOVERY_AR,
    TITLE_CUSTOMER_ACTIVITY_AR,
    TITLE_CUSTOMER_COMMS_AR,
    TITLE_DELAYED_RECOVERY_AR,
    TITLE_INTERNAL_HEALTH_AR,
    build_operations_center_page_summary,
    build_operations_center_presentation_context,
    enrich_db_due_scanner_admin_card,
)
from services.admin_operational_health import build_admin_operational_health_readonly
from services.admin_operational_control import build_admin_operational_control_readonly
from services.db_due_scanner_health import clear_db_due_scanner_health_for_tests

_EXPECTED_LABELS = [label for _, label in OPS_CENTER_FIELD_LABELS_AR]
_OPERATIONAL_TITLES = (
    TITLE_DELAYED_RECOVERY_AR,
    TITLE_CUSTOMER_ACTIVITY_AR,
    TITLE_INTERNAL_HEALTH_AR,
    TITLE_AUTO_RECOVERY_AR,
    TITLE_CUSTOMER_COMMS_AR,
)
_ENGINEERING_IN_LAYER1 = re.compile(
    r"QueuePool|cart-event|DB Due Scanner|loop_running",
    re.IGNORECASE,
)


class AdminOperationalHealthLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_db_due_scanner_health_for_tests()
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)

    def test_ops_center_field_order(self) -> None:
        control = build_admin_operational_control_readonly()
        payload = build_admin_operational_health_readonly()
        card = payload["cards"]["db_due_scanner"]
        rows = (card.get("operational") or {}).get("rows") or []
        self.assertEqual([r["label_ar"] for r in rows], _EXPECTED_LABELS)
        self.assertEqual(rows[0]["label_ar"], "المشكلة")
        self.assertEqual(rows[6]["label_ar"], "كيف نتحقق أن المشكلة انتهت؟")
        self.assertTrue(rows[6].get("verification_lines"))

    def test_page_summary_present(self) -> None:
        control = build_admin_operational_control_readonly()
        summary = build_operations_center_page_summary(control)
        self.assertEqual(summary["title_ar"], "مركز عمليات CartFlow")
        self.assertIn("summary_ar", summary)
        self.assertIn("affected_stores_ar", summary)
        self.assertIn("verification_lines_ar", summary)

    def test_operational_layer_avoids_engineering_terms(self) -> None:
        payload = build_admin_operational_health_readonly()
        for key in ("db_due_scanner", "cart_event", "db_pool", "background_tasks", "whatsapp"):
            card = payload["cards"][key]
            op = card.get("operational") or {}
            blob = " ".join(r.get("value_ar", "") for r in op.get("rows") or [])
            self.assertIsNone(_ENGINEERING_IN_LAYER1.search(blob), msg=key)
        pool_tech = "\n".join(payload["cards"]["db_pool"].get("technical_detail_lines") or [])
        self.assertIn("QueuePool", pool_tech)

    def test_renamed_card_titles(self) -> None:
        payload = build_admin_operational_health_readonly()
        titles = {
            (payload["cards"][k].get("operational") or {}).get("title_ar")
            for k in ("db_due_scanner", "cart_event", "db_pool", "background_tasks", "whatsapp")
        }
        self.assertEqual(titles, set(_OPERATIONAL_TITLES))

    def test_visual_operations_center(self) -> None:
        os.environ["CARTFLOW_ADMIN_PASSWORD"] = "ops-center-visual-pass"
        os.environ["SECRET_KEY"] = "unit-test-secret-key-for-admin-cookie-hmac-"
        client = TestClient(app)
        client.post(
            "/admin/operations/login",
            data={
                "password": "ops-center-visual-pass",
                "next": "/admin/operational-health",
            },
        )
        html = client.get("/admin/operational-health").text
        self.assertEqual(client.get("/admin/operational-health").status_code, 200)
        self.assertIn("مركز عمليات CartFlow", html)
        self.assertIn("الملخص التشغيلي", html)
        self.assertIn("المشكلة", html)
        self.assertIn("المتاجر المتأثرة", html)
        self.assertIn("العملاء المحتمل تأثرهم", html)
        self.assertIn("درجة الإلحاح", html)
        self.assertIn("كيف نتحقق أن المشكلة انتهت", html)
        self.assertIn("ماذا نفعل الآن", html)
        for title in _OPERATIONAL_TITLES:
            self.assertIn(title, html, msg=title)
        self.assertEqual(html.count("تفاصيل تقنية (للدعم)"), 5)
        pre = html.split("قرارات حسب المكوّن", 1)[0]
        self.assertNotIn("QueuePool", pre)
        block = html.split(TITLE_DELAYED_RECOVERY_AR, 1)[1].split(
            TITLE_CUSTOMER_ACTIVITY_AR, 1
        )[0]
        positions = [block.find(label) for label in _EXPECTED_LABELS]
        self.assertTrue(all(p >= 0 for p in positions))
        self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
