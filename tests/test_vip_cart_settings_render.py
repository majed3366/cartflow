# -*- coding: utf-8 -*-
"""VIP cart settings dashboard must render HTML (no missing Jinja macros)."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class VipCartSettingsRenderTests(unittest.TestCase):
    """Regression: never ship templates that call undefined macros on this route."""

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_vip_cart_settings_get_returns_200(self) -> None:
        r = self.client.get("/dashboard/vip-cart-settings")
        self.assertEqual(r.status_code, 200, r.text[:2000] if r.text else "")
        html = (r.text or "").lower()
        self.assertIn("vip-priority-alerts-ul", html)
        self.assertIn('class="sidebar"', html)
        self.assertNotIn("normal-recovery-alerts-ul", html)
        self.assertIn("/dashboard/normal-carts", r.text or "")

    def test_normal_carts_dashboard_get_returns_200(self) -> None:
        r = self.client.get("/dashboard/normal-carts")
        self.assertEqual(r.status_code, 200, r.text[:2000] if r.text else "")
        html = (r.text or "").lower()
        self.assertIn('class="sidebar"', html)
        self.assertIn("merchant-normal-carts-table", html)
        self.assertIn("cart-recovery-settings", html)

    def test_normal_recovery_legacy_redirects(self) -> None:
        r = self.client.get("/dashboard/normal-recovery", follow_redirects=False)
        self.assertEqual(r.status_code, 302, r.text[:500] if r.text else "")
        loc = r.headers.get("location") or ""
        self.assertIn("/dashboard/normal-carts", loc)


if __name__ == "__main__":
    unittest.main()
