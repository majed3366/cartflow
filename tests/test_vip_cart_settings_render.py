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
        self.assertIn("cf-dash-shell", html)
        self.assertIn("vip-priority-alerts-ul", html)
        self.assertIn("normal-recovery-alerts-ul", html)


if __name__ == "__main__":
    unittest.main()
