# -*- coding: utf-8 -*-
"""Operational-first language layer for admin health."""

from __future__ import annotations

import os
import unittest

from services.admin_operational_health_language import (
    build_db_due_scanner_operational_layer,
    enrich_db_due_scanner_admin_card,
)
from services.db_due_scanner_health import (
    clear_db_due_scanner_health_for_tests,
    record_db_due_scanner_loop_started,
    record_db_due_scanner_tick_result,
)


class AdminOperationalHealthLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_db_due_scanner_health_for_tests()
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)

    def test_scanner_operational_layer_healthy(self) -> None:
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        record_db_due_scanner_loop_started()
        record_db_due_scanner_tick_result({"found": 0, "dispatched": 1, "skipped": 0})
        card = enrich_db_due_scanner_admin_card(
            {
                "enabled": True,
                "status": "healthy",
                "loop_running": True,
                "total_dispatches": 1,
                "last_error": None,
                "last_found": 0,
                "interval_seconds": 30,
                "last_dispatch_ago": "1 min ago",
            }
        )
        op = card["operational"]
        self.assertEqual(op["title_ar"], "فحص المهام المؤجلة")
        self.assertIn("يعمل طبيعي", op["status_line_ar"])
        self.assertEqual(op["monitoring_ar"], "تعمل")
        self.assertEqual(op["processed_tasks_ar"], "1")
        self.assertEqual(op["merchant_impact_ar"], "لا يوجد")
        self.assertIn("لا حاجة", op["suggested_action_ar"])
        tech = "\n".join(card["technical_detail_lines"])
        self.assertIn("DB Due Scanner", tech)
        self.assertIn("found (مهام بحاجة معالجة)", tech)
        self.assertIn("dispatched (مهام تمت معالجتها)", tech)

    def test_operational_required_fields(self) -> None:
        op = build_db_due_scanner_operational_layer(
            {"enabled": False, "status": "disabled", "loop_running": False, "total_dispatches": 0}
        )
        for key in (
            "has_risk_ar",
            "needs_intervention_ar",
            "merchant_impact_ar",
            "suggested_action_ar",
            "last_problem_ar",
            "last_success_ar",
        ):
            self.assertIn(key, op, msg=key)


if __name__ == "__main__":
    unittest.main()
