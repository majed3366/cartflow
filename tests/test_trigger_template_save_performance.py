# -*- coding: utf-8 -*-
"""POST trigger-templates — خفيف وسريع؛ لا يعيد بناء الحمولة الكاملة."""

from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from main import app
from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS


class TriggerTemplateSavePerformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_post_faster_and_smaller_than_get(self) -> None:
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
        t0 = time.perf_counter()
        post = self.client.post("/api/dashboard/trigger-templates", json=body)
        post_ms = (time.perf_counter() - t0) * 1000
        self.assertEqual(post.status_code, 200)
        self.assertTrue(post.json().get("save_ack"))

        t1 = time.perf_counter()
        get = self.client.get("/api/dashboard/trigger-templates")
        get_ms = (time.perf_counter() - t1) * 1000
        self.assertEqual(get.status_code, 200)

        self.assertLess(len(post.content), len(get.content) // 2 + 1)
        self.assertLess(post_ms, 5000, msg=f"POST took {post_ms:.0f}ms")


if __name__ == "__main__":
    unittest.main()
