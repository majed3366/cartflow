# -*- coding: utf-8 -*-
"""Lightweight multi-page demo routes for behavioral / return-to-site operational testing."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from main import (
    _is_user_returned,
    _recovery_key_from_payload,
    _test_set_recovery_flow_armed_at,
    app,
)

from tests.test_recovery_isolation import (
    _post_recovery_reason_for_session,
    _reset_recovery_memory,
)


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
        sid = "demo-nav-return-1"
        cid = "cart-demo-nav-1"
        _post_recovery_reason_for_session(self.client, "demo", sid)
        abandon = {
            "event": "cart_abandoned",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart": [{"name": "T", "price": 1.0}],
            "phone": "9665111222333",
        }
        r0 = self.client.post("/api/cart-event", json=abandon)
        self.assertEqual(200, r0.status_code, r0.text)
        key = _recovery_key_from_payload(
            {"store": "demo", "session_id": sid, "cart_id": cid}
        )
        _test_set_recovery_flow_armed_at(
            key, datetime.now(timezone.utc) - timedelta(seconds=120)
        )
        payload = {
            "event_type": "user_returned_to_site",
            "user_returned_to_site": True,
            "store": "demo",
            "store_slug": "demo",
            "session_id": sid,
            "cart_id": cid,
            "recovery_return_context": "product",
        }
        r = self.client.post("/api/cart-event", json=payload)
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue(_is_user_returned(key), key)

    def test_return_without_recovery_armed_does_not_mark(self) -> None:
        payload = {
            "event_type": "user_returned_to_site",
            "user_returned_to_site": True,
            "store": "demo",
            "session_id": "demo-no-arm-1",
            "cart_id": "cart-no-arm-1",
        }
        r = self.client.post("/api/cart-event", json=payload)
        self.assertEqual(200, r.status_code, r.text)
        key = _recovery_key_from_payload(payload)
        self.assertFalse(_is_user_returned(key), key)

    def test_return_immediately_after_abandon_does_not_mark(self) -> None:
        sid = "demo-cooldown-1"
        cid = "cart-cooldown-1"
        _post_recovery_reason_for_session(self.client, "demo", sid)
        abandon = {
            "event": "cart_abandoned",
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
            "cart": [{"name": "T", "price": 1.0}],
            "phone": "9665111222333",
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=abandon).status_code)
        ret = {
            "event_type": "user_returned_to_site",
            "user_returned_to_site": True,
            "store": "demo",
            "session_id": sid,
            "cart_id": cid,
        }
        self.assertEqual(200, self.client.post("/api/cart-event", json=ret).status_code)
        key = _recovery_key_from_payload(ret)
        self.assertFalse(_is_user_returned(key), key)


if __name__ == "__main__":
    unittest.main()
