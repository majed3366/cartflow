# -*- coding: utf-8 -*-
"""Legacy merchant routes redirect into the standalone merchant app."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class MerchantDashboardRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_vip_cart_settings_redirects_to_merchant_app_vip(self) -> None:
        r = self.client.get("/dashboard/vip-cart-settings", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text[:2000] if r.text else "")
        loc = r.headers.get("location") or ""
        self.assertIn("/dashboard", loc)
        self.assertIn("#vip", loc)

    def test_normal_carts_redirects_to_merchant_app_carts(self) -> None:
        r = self.client.get("/dashboard/normal-carts", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text[:2000] if r.text else "")
        loc = r.headers.get("location") or ""
        self.assertIn("#carts", loc)
        self.assertNotIn("merchant-normal-carts-table", loc.lower())

    def test_normal_recovery_legacy_redirects(self) -> None:
        r = self.client.get("/dashboard/normal-recovery", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text[:500] if r.text else "")
        loc = r.headers.get("location") or ""
        self.assertIn("#carts", loc)


if __name__ == "__main__":
    unittest.main()
