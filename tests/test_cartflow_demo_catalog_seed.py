# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest

from services.cartflow_demo_catalog_seed import demo_store_catalog_needs_seed
from services.demo_sandbox_catalog import merchant_catalog_for_intelligence_sync


class DemoCatalogSeedTests(unittest.TestCase):
    def test_demo_store_catalog_needs_seed_empty_cases(self) -> None:
        self.assertTrue(demo_store_catalog_needs_seed(None))
        self.assertTrue(demo_store_catalog_needs_seed(""))
        self.assertTrue(demo_store_catalog_needs_seed("   "))
        self.assertTrue(demo_store_catalog_needs_seed("{}"))
        self.assertTrue(demo_store_catalog_needs_seed('{"products":[]}'))
        self.assertTrue(demo_store_catalog_needs_seed("not-json"))

    def test_demo_store_catalog_needs_seed_when_populated(self) -> None:
        raw = json.dumps({"version": 1, "products": [{"id": "x", "name": "Y", "price": 1.0}]})
        self.assertFalse(demo_store_catalog_needs_seed(raw))

    def test_merchant_catalog_hoodies_same_normalized_fashion_bucket(self) -> None:
        cat = merchant_catalog_for_intelligence_sync(nav_base="https://example.com/demo/store")
        prods = {p["id"]: p for p in cat.get("products", []) if isinstance(p, dict)}
        self.assertIn("demo_hoodie", prods)
        self.assertIn("demo_hoodie_essentials", prods)
        h = prods["demo_hoodie"]
        e = prods["demo_hoodie_essentials"]
        self.assertEqual(h.get("normalized_category"), "الموضة والأزياء")
        self.assertEqual(e.get("normalized_category"), "الموضة والأزياء")
        self.assertLess(float(e["price"]), float(h["price"]))
        self.assertTrue(h.get("url", "").strip().startswith("http"))
        self.assertTrue(e.get("url", "").strip().startswith("http"))
        self.assertNotIn("demo_hoodie", (e.get("url") or ""))
