# -*- coding: utf-8 -*-
"""POST /api/cartflow/generate-whatsapp-message (Mock نصوص)."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app
from services.cartflow_whatsapp_mock import build_mock_whatsapp_message


class GenerateWhatsappMessageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_build_price_discount_no_cart_in_body(self) -> None:
        t = build_mock_whatsapp_message(
            reason="price",
            sub_category="price_discount_request",
            product_name="سماعة",
            cart_url="https://x/cart",
        )
        self.assertIn("عرض مناسب", t)
        self.assertNotIn("رابط السلة", t, t)
        self.assertNotIn("https://x", t, t)

    def test_post_requires_session(self) -> None:
        r = self.client.post(
            "/api/cartflow/generate-whatsapp-message",
            json={"store_slug": "demo", "session_id": "", "reason": "quality"},
        )
        self.assertEqual(400, r.status_code, r.text)

    def test_post_price_ok(self) -> None:
        r = self.client.post(
            "/api/cartflow/generate-whatsapp-message",
            json={
                "store_slug": "demo",
                "session_id": "s1",
                "reason": "price",
                "sub_category": "price_budget_issue",
                "product_name": "P",
                "cart_url": "#",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertIn("ميزانيتك", (j.get("message") or ""), j)
        self.assertIn("merchant_whatsapp_e164", j)
        self.assertIsNone(j.get("merchant_whatsapp_e164"))

    def test_post_warranty(self) -> None:
        r = self.client.post(
            "/api/cartflow/generate-whatsapp-message",
            json={
                "store_slug": "demo",
                "session_id": "s1",
                "reason": "warranty",
                "product_name": "X",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        m = r.json().get("message") or ""
        self.assertIn("الضمان", m, m)
        self.assertIn("قبل إكمال الطلب", m, m)

    def test_post_thinking(self) -> None:
        r = self.client.post(
            "/api/cartflow/generate-whatsapp-message",
            json={
                "store_slug": "demo",
                "session_id": "s1",
                "reason": "thinking",
                "product_name": "منتج",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        m = (r.json().get("message") or "")
        self.assertIn("راحتك", m, m)
        self.assertIn("منتج", m, m)

    def test_post_price_without_sub_400(self) -> None:
        r = self.client.post(
            "/api/cartflow/generate-whatsapp-message",
            json={"store_slug": "demo", "session_id": "s1", "reason": "price"},
        )
        self.assertEqual(400, r.status_code, r.text)


if __name__ == "__main__":
    unittest.main()
