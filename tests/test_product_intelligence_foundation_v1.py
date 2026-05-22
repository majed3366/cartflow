# -*- coding: utf-8 -*-
"""Product Intelligence Foundation v1 — context only, no fake alternatives."""
from __future__ import annotations

import unittest
from unittest import mock

from services.product_intelligence_foundation_v1 import (
    PRICE_CONFIDENCE_NONE,
    CustomerContext,
    ProductContext,
    ProductContextResolver,
    ProductIntelligenceInputs,
    build_product_intelligence_context,
    observe_product_intelligence,
)


class ProductIntelligenceFoundationV1Tests(unittest.TestCase):
    def test_missing_product_identity(self) -> None:
        ctx = ProductContextResolver.resolve_from_cart({})
        self.assertFalse(ctx.has_product_identity)
        intel = build_product_intelligence_context(
            ProductIntelligenceInputs(product=ctx, reason_tag="price")
        )
        self.assertFalse(intel.has_product_identity)
        self.assertFalse(intel.has_cheaper_option)

    def test_missing_category(self) -> None:
        product = ProductContext(
            product_name="Test Item",
            product_id="p1",
            price=99.0,
            source="test",
        )
        intel = build_product_intelligence_context(
            ProductIntelligenceInputs(product=product, reason_tag="shipping")
        )
        self.assertFalse(intel.has_same_category)
        self.assertIn("category_missing", intel.evidence)

    def test_missing_price_confidence_none(self) -> None:
        product = ProductContext(
            product_name="Test Item",
            product_id="p1",
            category="إلكترونيات",
            source="test",
        )
        intel = build_product_intelligence_context(
            ProductIntelligenceInputs(product=product)
        )
        self.assertEqual(intel.price_confidence, PRICE_CONFIDENCE_NONE)
        self.assertFalse(intel.has_cheaper_option)

    def test_product_context_from_cart_only(self) -> None:
        cart = {
            "cart": [
                {
                    "id": "sku-9",
                    "name": "سماعة لاسلكية",
                    "price": 199.0,
                    "category": "إلكترونيات",
                    "currency": "SAR",
                    "warranty": "سنة",
                    "shipping_info": "شحن 2-4 أيام",
                }
            ]
        }
        ctx = ProductContextResolver.resolve_from_cart(cart)
        self.assertEqual(ctx.product_id, "sku-9")
        self.assertEqual(ctx.price, 199.0)
        self.assertEqual(ctx.source, "cart")
        intel = build_product_intelligence_context(
            ProductIntelligenceInputs(
                product=ctx,
                reason_tag="price",
                customer=CustomerContext(store_slug="demo", session_id="s1"),
            )
        )
        self.assertTrue(intel.has_same_category)
        self.assertTrue(intel.has_warranty_signal)
        self.assertTrue(intel.has_shipping_reassurance)
        self.assertEqual(intel.price_confidence, "high")

    def test_no_fake_cheaper_without_catalog(self) -> None:
        product = ProductContext(
            product_name="هاتف",
            product_id="a",
            category="إلكترونيات",
            price=500.0,
            source="cart",
        )
        intel = build_product_intelligence_context(
            ProductIntelligenceInputs(product=product, reason_tag="price")
        )
        self.assertFalse(intel.has_cheaper_option)
        self.assertIn("catalog_not_provided", intel.evidence)

    def test_cheaper_only_when_catalog_fact(self) -> None:
        product = ProductContext(
            product_name="هاتف أ",
            product_id="a",
            category="إلكترونيات",
            price=500.0,
            source="cart",
        )
        catalog = (
            {"product_id": "b", "category": "إلكترونيات", "price": 400.0, "available": True},
            {"product_id": "c", "category": "إلكترونيات", "price": 600.0, "available": True},
        )
        intel = build_product_intelligence_context(
            ProductIntelligenceInputs(
                product=product,
                catalog_entries=catalog,
            )
        )
        self.assertTrue(intel.has_cheaper_option)

        intel_high_only = build_product_intelligence_context(
            ProductIntelligenceInputs(
                product=product,
                catalog_entries=(catalog[1],),
            )
        )
        self.assertFalse(intel_high_only.has_cheaper_option)

    def test_observe_logs_without_side_effects(self) -> None:
        with mock.patch("builtins.print") as mock_print:
            observe_product_intelligence(
                ProductIntelligenceInputs(
                    product=ProductContext(product_name="X", price=10.0, source="t"),
                    customer=CustomerContext(store_slug="demo"),
                )
            )
        joined = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("PRODUCT CONTEXT", joined)
        self.assertIn("PRODUCT INTELLIGENCE", joined)
        self.assertNotIn("recommend", joined.lower())


if __name__ == "__main__":
    unittest.main()
