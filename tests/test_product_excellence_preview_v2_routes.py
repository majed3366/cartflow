# -*- coding: utf-8 -*-
"""Product Excellence V2 preview routes — static visual review build."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class ProductExcellencePreviewV2RoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_v2_surface_routes(self) -> None:
        paths = (
            "/preview/product-excellence-v2/home",
            "/preview/product-excellence-v2/carts",
            "/preview/product-excellence-v2/cart-detail",
        )
        for path in paths:
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 200)
                self.assertIn("text/html", r.headers.get("content-type", ""))
                self.assertEqual(
                    r.headers.get("x-cartflow-preview"), "product-excellence-v2"
                )

    def test_v2_assets_css(self) -> None:
        r = self.client.get(
            "/preview/product-excellence-v2/assets/pe-v2-system.css"
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/css", r.headers.get("content-type", ""))

    def test_production_dashboard_unchanged(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertIn("ma-home-experience-root", r.text)


if __name__ == "__main__":
    unittest.main()
