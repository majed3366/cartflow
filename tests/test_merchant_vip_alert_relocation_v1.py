# -*- coding: utf-8 -*-
"""VIP alert banner relocation — homepage to carts page (presentation only)."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_HTML = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")


class MerchantVipAlertRelocationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        import os

        os.environ["ENV"] = "development"
        os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-for-vip-alert-relocation")
        self.client = TestClient(app)

    def test_homepage_excludes_vip_alert_banner_host(self) -> None:
        self.assertNotIn('id="ma-home-vip-banner"', _HTML)
        home_idx = _HTML.index('id="page-home"')
        carts_idx = _HTML.index('id="page-carts"')
        home_slice = _HTML[home_idx:carts_idx]
        self.assertNotIn("vip-alert", home_slice)

    def test_carts_page_has_cart_alerts_root_above_filters(self) -> None:
        self.assertIn('id="ma-cart-alerts-root"', _HTML)
        self.assertIn('id="ma-cart-alerts-vip"', _HTML)
        self.assertIn('class="ma-cart-alerts"', _HTML)
        self.assertIn('data-alert-type="vip"', _HTML)
        alerts_idx = _HTML.index('id="ma-cart-alerts-root"')
        filters_idx = _HTML.index('id="ma-cart-filters"')
        self.assertLess(alerts_idx, filters_idx)

    def test_knowledge_layer_precedes_home_kpi_on_homepage(self) -> None:
        home_idx = _HTML.index('id="page-home"')
        carts_idx = _HTML.index('id="page-carts"')
        home_slice = _HTML[home_idx:carts_idx]
        knowledge_idx = home_slice.index('id="ma-knowledge-root"')
        kpi_idx = home_slice.index('class="kpi-grid')
        self.assertLess(knowledge_idx, kpi_idx)

    def test_lazy_js_targets_cart_alerts_not_home_banner(self) -> None:
        self.assertIn("applyVipCartAlert", _LAZY_JS)
        self.assertNotIn("applyVipHomeBanner", _LAZY_JS)
        self.assertNotIn("ma-home-vip-banner", _LAZY_JS)
        self.assertIn("ma-cart-alerts-root", _LAZY_JS)
        self.assertIn("ma-cart-alerts-vip", _LAZY_JS)

    def test_dashboard_html_includes_cart_alerts_markers(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200, r.text[:500])
        html = r.text or ""
        self.assertIn('id="ma-cart-alerts-root"', html)
        self.assertNotIn('id="ma-home-vip-banner"', html)


if __name__ == "__main__":
    unittest.main()
