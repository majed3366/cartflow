# -*- coding: utf-8 -*-
"""Lightweight multi-page demo routes for behavioral / return-to-site operational testing."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import (
    _is_user_returned,
    _recovery_key_from_payload,
    app,
)

from tests.test_recovery_isolation import _reset_recovery_memory


class DemoBehavioralNavigationTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    def test_demo_product_pages_and_unknown_id(self) -> None:
        r404 = self.client.get("/demo/store/product/0")
        self.assertEqual(r404.status_code, 404)
        r99 = self.client.get("/demo/store/product/99")
        self.assertEqual(r99.status_code, 404)
        for pid in (1, 2, 6):
            r = self.client.get(f"/demo/store/product/{pid}")
            self.assertEqual(200, r.status_code, r.text[:500])
            t = r.text or ""
            self.assertIn('id="cf-demo-behavioral-nav"', t)
            self.assertIn("/demo/store/cart", t)
            self.assertIn("widget_loader.js", t)
            self.assertIn("cart_abandon_tracking", t)
            self.assertIn('id="cf-demo-product-detail"', t)

    def test_demo_cart_page_hides_catalog_grid(self) -> None:
        r = self.client.get("/demo/store/cart")
        self.assertEqual(200, r.status_code)
        self.assertNotIn('id="cf-demo-products"', r.text)

    def test_demo_list_page_shows_grid(self) -> None:
        r = self.client.get("/demo/store")
        self.assertEqual(200, r.status_code)
        self.assertIn('id="cf-demo-products"', r.text)

    def test_demo_store2_product_and_nav_base(self) -> None:
        r = self.client.get("/demo/store2/product/1")
        self.assertEqual(200, r.status_code)
        t = r.text or ""
        self.assertIn("/demo/store2/cart", t)
        self.assertIn("/demo/store2/product/2", t)
        self.assertNotIn("/demo/store/product/1", t)

    def test_user_returned_to_site_payload_marks_recovery_key(self) -> None:
        payload = {
            "event_type": "user_returned_to_site",
            "user_returned_to_site": True,
            "store": "demo",
            "store_slug": "demo",
            "session_id": "demo-nav-return-1",
            "cart_id": "cart-demo-nav-1",
            "recovery_return_context": "product",
        }
        r = self.client.post("/api/cart-event", json=payload)
        self.assertEqual(200, r.status_code, r.text)
        key = _recovery_key_from_payload(payload)
        self.assertTrue(_is_user_returned(key), key)


if __name__ == "__main__":
    unittest.main()
