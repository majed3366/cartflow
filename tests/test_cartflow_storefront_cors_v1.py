# -*- coding: utf-8 -*-
"""Storefront widget CORS for Zid merchant domains."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app
from services.cartflow_storefront_cors_v1 import (
    is_allowed_storefront_widget_origin,
    widget_cors_path_matches,
)


class CartflowStorefrontCorsUnitTests(unittest.TestCase):
    def test_zid_store_origin_allowed(self) -> None:
        self.assertTrue(
            is_allowed_storefront_widget_origin("https://4hz49e.zid.store")
        )
        self.assertTrue(
            is_allowed_storefront_widget_origin("https://demo-shop.zid.store")
        )

    def test_non_zid_origin_rejected(self) -> None:
        self.assertFalse(is_allowed_storefront_widget_origin("https://evil.example.com"))
        self.assertFalse(is_allowed_storefront_widget_origin("http://4hz49e.zid.store"))

    def test_widget_cors_paths(self) -> None:
        self.assertTrue(widget_cors_path_matches("/api/cartflow/ready"))
        self.assertTrue(widget_cors_path_matches("/api/cartflow/public-config"))
        self.assertTrue(widget_cors_path_matches("/api/cartflow/reason"))
        self.assertTrue(widget_cors_path_matches("/api/cart-event"))
        self.assertTrue(widget_cors_path_matches("/api/storefront/widget-seen"))
        self.assertFalse(widget_cors_path_matches("/api/recovery-settings"))


class CartflowStorefrontCorsHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.zid_origin = "https://4hz49e.zid.store"

    def test_options_preflight_zid_origin(self) -> None:
        r = self.client.options(
            "/api/cartflow/ready",
            headers={
                "Origin": self.zid_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(204, r.status_code)
        self.assertEqual(self.zid_origin, r.headers.get("access-control-allow-origin"))
        self.assertIn("GET", r.headers.get("access-control-allow-methods", ""))

    def test_get_ready_zid_origin_acao(self) -> None:
        r = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "demo", "session_id": "cors-test-sid"},
            headers={"Origin": self.zid_origin},
        )
        self.assertEqual(200, r.status_code)
        self.assertEqual(self.zid_origin, r.headers.get("access-control-allow-origin"))
        body = r.json() or {}
        self.assertTrue(body.get("ok"))

    def test_get_ready_empty_session_id_not_422(self) -> None:
        r = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "demo", "session_id": ""},
            headers={"Origin": self.zid_origin},
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertEqual(self.zid_origin, r.headers.get("access-control-allow-origin"))

    def test_get_ready_foreign_origin_no_acao(self) -> None:
        r = self.client.get(
            "/api/cartflow/ready",
            params={"store_slug": "demo", "session_id": "x"},
            headers={"Origin": "https://not-zid.example.com"},
        )
        self.assertEqual(200, r.status_code)
        self.assertIsNone(r.headers.get("access-control-allow-origin"))

    def test_public_config_zid_origin(self) -> None:
        r = self.client.get(
            "/api/cartflow/public-config",
            params={"store_slug": "demo"},
            headers={"Origin": self.zid_origin},
        )
        self.assertEqual(200, r.status_code)
        self.assertEqual(self.zid_origin, r.headers.get("access-control-allow-origin"))

    def test_options_preflight_widget_seen(self) -> None:
        r = self.client.options(
            "/api/storefront/widget-seen",
            headers={
                "Origin": self.zid_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        self.assertEqual(204, r.status_code)
        self.assertEqual(self.zid_origin, r.headers.get("access-control-allow-origin"))
        self.assertIn("POST", r.headers.get("access-control-allow-methods", ""))
        self.assertIn("Content-Type", r.headers.get("access-control-allow-headers", ""))

    def test_post_widget_seen_zid_origin_acao(self) -> None:
        r = self.client.post(
            "/api/storefront/widget-seen",
            json={
                "store_slug": "demo",
                "runtime_truth": {"widget_enabled": False, "config_loaded": True},
            },
            headers={"Origin": self.zid_origin},
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertEqual(self.zid_origin, r.headers.get("access-control-allow-origin"))
        self.assertTrue((r.json() or {}).get("ok"))

    def test_post_widget_seen_foreign_origin_no_acao(self) -> None:
        r = self.client.post(
            "/api/storefront/widget-seen",
            json={"store_slug": "demo"},
            headers={"Origin": "https://not-zid.example.com"},
        )
        self.assertEqual(200, r.status_code)
        self.assertIsNone(r.headers.get("access-control-allow-origin"))


if __name__ == "__main__":
    unittest.main()
