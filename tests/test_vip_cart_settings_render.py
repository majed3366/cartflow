# -*- coding: utf-8 -*-
"""Merchant dashboard routes return the lightweight rebuild placeholder."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class MerchantDashboardPlaceholderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_vip_cart_settings_get_returns_placeholder(self) -> None:
        r = self.client.get("/dashboard/vip-cart-settings")
        self.assertEqual(r.status_code, 200, r.text[:2000] if r.text else "")
        html = r.text or ""
        self.assertIn("data-cf-merchant-dashboard-placeholder", html.lower())
        self.assertIn("Merchant Dashboard is being rebuilt", html)
        self.assertNotIn("vip-priority-alerts-ul", html.lower())

    def test_normal_carts_merchant_get_returns_placeholder(self) -> None:
        r = self.client.get("/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200, r.text[:2000] if r.text else "")
        html = r.text or ""
        self.assertIn("data-cf-merchant-dashboard-placeholder", html.lower())
        self.assertIn("Merchant Dashboard is being rebuilt", html)
        self.assertNotIn("merchant-normal-carts-table", html.lower())

    def test_normal_recovery_legacy_redirects(self) -> None:
        r = self.client.get("/dashboard/normal-recovery", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text[:500] if r.text else "")
        loc = r.headers.get("location") or ""
        self.assertIn("/dashboard/normal-carts", loc)


if __name__ == "__main__":
    unittest.main()
