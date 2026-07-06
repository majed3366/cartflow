# -*- coding: utf-8 -*-
"""Product Excellence preview routes — static visual review build."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class ProductExcellencePreviewRoutesV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_preview_hub_returns_html(self) -> None:
        r = self.client.get("/preview/product-excellence")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers.get("content-type", ""))
        self.assertEqual(r.headers.get("x-cartflow-preview"), "product-excellence-v1")
        self.assertIn("Product Excellence Visual Rebuild", r.text)

    def test_surface_prototype_routes(self) -> None:
        paths = (
            "/preview/product-excellence/home",
            "/preview/product-excellence/carts",
            "/preview/product-excellence/cart-detail",
        )
        for path in paths:
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 200)
                self.assertIn("Prototype", r.text)

    def test_compare_and_asset_routes(self) -> None:
        r = self.client.get("/preview/product-excellence/compare/home-before")
        self.assertEqual(r.status_code, 200)
        css = self.client.get("/preview/product-excellence/assets/pe-visual-system.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn("text/css", css.headers.get("content-type", ""))

    def test_production_dashboard_unaffected(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        self.assertIn("ma-home-experience-root", r.text)


if __name__ == "__main__":
    unittest.main()
