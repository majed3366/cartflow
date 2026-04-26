# -*- coding: utf-8 -*-
"""GET /demo/cartflow/sequence and /demo/cartflow/logs (demo slugs only)."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class DemoPanelApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_sequence_returns_three_steps(self) -> None:
        r = self.client.get("/demo/cartflow/sequence")
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertEqual(len(j.get("steps", [])), 3, j)
        self.assertEqual(j["steps"][0].get("step"), 1)

    def test_logs_rejects_non_demo_store(self) -> None:
        r = self.client.get(
            "/demo/cartflow/logs", params={"store_slug": "other", "session_id": "x"}
        )
        self.assertEqual(400, r.status_code, r.text)

    def test_logs_ok_for_demo(self) -> None:
        r = self.client.get(
            "/demo/cartflow/logs", params={"store_slug": "demo", "session_id": "any"}
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertIn("logs", j)
        self.assertIsInstance(j["logs"], list)

    def test_whatsapp_preview_price_sub(self) -> None:
        r = self.client.get(
            "/demo/cartflow/whatsapp-preview",
            params={"reason": "price", "sub_category": "price_discount_request"},
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertIn("عندك كود خصم", (j.get("message") or ""))

    def test_whatsapp_preview_reason_without_sub(self) -> None:
        r = self.client.get(
            "/demo/cartflow/whatsapp-preview",
            params={"reason": "quality"},
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertIn("جودة", (j.get("message") or ""))

    def test_whatsapp_preview_rejects_price_without_sub(self) -> None:
        r = self.client.get(
            "/demo/cartflow/whatsapp-preview",
            params={"reason": "price"},
        )
        self.assertEqual(400, r.status_code, r.text)
        j = r.json()
        self.assertFalse(j.get("ok"), j)

    def test_whatsapp_preview_rejects_unknown(self) -> None:
        r = self.client.get(
            "/demo/cartflow/whatsapp-preview",
            params={"reason": "not_a_reason_key"},
        )
        self.assertEqual(400, r.status_code, r.text)


if __name__ == "__main__":
    unittest.main()
