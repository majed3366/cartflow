# -*- coding: utf-8 -*-
"""POST /api/cartflow/generate-whatsapp-message (Mock نصوص)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.cartflow_whatsapp_mock import build_mock_whatsapp_message
from services.decision_engine import VIP_CUSTOMER_WHATSAPP_NEUTRAL_BODY


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

    def test_post_auto_default_no_db_uses_price_discount(self) -> None:
        slug = "test_auto_isolated_empty_slug"
        r = self.client.post(
            "/api/cartflow/generate-whatsapp-message",
            json={
                "store_slug": slug,
                "session_id": "auto_session_1",
                "reason": "auto",
                "product_name": "سماعة",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertEqual("price", j.get("resolved_reason"), j)
        self.assertEqual("price_discount_request", j.get("resolved_sub_category"), j)
        self.assertIn("عرض مناسب", (j.get("message") or ""), j)
        self.assertFalse(j.get("used_dashboard_primary"), j)

    def test_post_auto_ok(self) -> None:
        r = self.client.post(
            "/api/cartflow/generate-whatsapp-message",
            json={
                "store_slug": "demo",
                "session_id": "s_auto",
                "reason": "auto",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertIn("resolved_reason", j)
        self.assertIn("primary_reason_log", j)

    def test_post_vip_cart_total_returns_neutral_message_not_price(self) -> None:
        with patch("routes.cartflow.is_vip_cart", return_value=True):
            r = self.client.post(
                "/api/cartflow/generate-whatsapp-message",
                json={
                    "store_slug": "demo",
                    "session_id": "s_vip_neutral_preview",
                    "reason": "price",
                    "sub_category": "price_discount_request",
                    "product_name": "سماعة",
                    "cart_url": "#",
                    "cart_total": 5000.0,
                },
            )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertEqual(j.get("resolved_reason"), "vip_neutral_followup")
        self.assertEqual(
            (j.get("message") or "").strip(),
            VIP_CUSTOMER_WHATSAPP_NEUTRAL_BODY.strip(),
        )
        self.assertNotIn("عرض", (j.get("message") or ""), j)

    def test_build_vip_phone_capture_mock_matches_neutral_body(self) -> None:
        m = build_mock_whatsapp_message(
            reason="vip_phone_capture",
            sub_category=None,
        )
        self.assertEqual(m.strip(), VIP_CUSTOMER_WHATSAPP_NEUTRAL_BODY.strip())

    def test_get_primary_recovery_reason_endpoint(self) -> None:
        r = self.client.get(
            "/api/cartflow/primary-recovery-reason?store_slug=test_slug_pr"
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        self.assertEqual("price", j.get("primary_reason"))

    def test_api_recovery_primary_reason(self) -> None:
        r = self.client.get("/api/recovery/primary-reason?store_id=test_recovery_slug")
        self.assertEqual(200, r.status_code, r.text)
        j = r.json()
        self.assertEqual("price", j.get("primary_reason"), j)
        self.assertIn("primary_reason", j)


if __name__ == "__main__":
    unittest.main()
