# -*- coding: utf-8 -*-
"""مسارات اللوحة الساخنة — لا ‎create_all‎ في VIP dedupe بعد التدفئة."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from extensions import db
from main import app
from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS


class DbPoolDashboardHotPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        main._cartflow_api_db_warmed = True

    def tearDown(self) -> None:
        main._vip_dedupe_last_run_mono = 0.0

    def test_vip_cleanup_does_not_call_create_all_when_warmed(self) -> None:
        main._vip_dedupe_last_run_mono = 0.0
        with patch.object(db, "create_all") as mock_ca:
            main._cleanup_duplicate_vip_abandoned_rows(store_id_scope=None)
            mock_ca.assert_not_called()

    def test_merchant_dashboard_db_ready_noop_when_warmed(self) -> None:
        with patch.object(main, "_ensure_cartflow_api_db_warmed") as mock_warm:
            main._merchant_dashboard_db_ready()
            mock_warm.assert_not_called()

    def test_five_consecutive_template_saves_succeed(self) -> None:
        stage1 = DASHBOARD_STAGE_TEXTS["price"][0]
        body = {
            "reason_templates": {
                "price": {
                    "enabled": True,
                    "message": stage1,
                    "message_count": 1,
                    "messages": [{"delay": 5, "unit": "minute", "text": stage1}],
                }
            },
            "selected_stage": 0,
        }
        for i in range(5):
            r = self.client.post("/api/dashboard/trigger-templates", json=body)
            self.assertEqual(r.status_code, 200, msg=f"save {i}: {r.text[:300]}")
            p = r.json()
            self.assertTrue(p.get("ok"), msg=p)
            self.assertTrue(p.get("save_ack"), msg=p)
        g = self.client.get("/api/dashboard/trigger-templates")
        self.assertEqual(g.status_code, 200)
        price = next(x for x in g.json().get("reason_rows") or [] if x.get("key") == "price")
        self.assertEqual(price.get("delay_value"), 5.0)


if __name__ == "__main__":
    unittest.main()
