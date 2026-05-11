# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from models import AbandonedCart
from services.cartflow_product_intelligence import (
    CatalogEntry,
    decide_merchant_offer_line,
    select_cheaper_alternative,
    build_product_intelligence_snapshot,
)
from services.cartflow_reply_intent_engine import (
    CONTINUATION_ACTION_SEND_CHEAPER,
    build_continuation_message,
    decide_continuation,
)


class ProductIntelligenceTests(unittest.TestCase):
    def test_select_cheaper_same_category_lower_price(self) -> None:
        primary = CatalogEntry(
            product_id="a",
            name="هاتف أ",
            price=500.0,
            category="إلكترونيات",
            url="",
            available=True,
        )
        cart_other = CatalogEntry(
            product_id="b",
            name="هاتف ب",
            price=420.0,
            category="إلكترونيات",
            url="https://x/b",
            available=True,
        )
        pick = select_cheaper_alternative(
            primary=primary,
            cart_entries=[cart_other],
            catalog_entries=[],
            recovery_category_label="إلكترونيات",
        )
        self.assertIsNotNone(pick.entry)
        assert pick.entry is not None
        self.assertEqual(pick.entry.product_id, "b")
        self.assertLess(pick.entry.price, primary.price)
        self.assertGreater(pick.cheaper_candidate_score, 0.0)

    def test_select_cheaper_rejects_higher_price(self) -> None:
        primary = CatalogEntry(
            product_id="a",
            name="هاتف أ",
            price=100.0,
            category="إلكترونيات",
            url="",
            available=True,
        )
        bad = CatalogEntry(
            product_id="b",
            name="هاتف ب",
            price=150.0,
            category="إلكترونيات",
            url="",
            available=True,
        )
        pick = select_cheaper_alternative(
            primary=primary,
            cart_entries=[bad],
            catalog_entries=[],
            recovery_category_label="إلكترونيات",
        )
        self.assertIsNone(pick.entry)
        self.assertEqual(pick.fallback_reason, "no_eligible_cheaper_in_category")

    def test_offer_requires_code_and_reason(self) -> None:
        st = SimpleNamespace(
            cf_merchant_offer_settings_json=json.dumps(
                {
                    "offer_enabled": True,
                    "enable_discount_offers": True,
                    "discount_code": "",
                    "offer_trigger_reason": "price",
                },
                ensure_ascii=False,
            ),
            cf_offer_applications_count=0,
        )
        line, apply = decide_merchant_offer_line(
            st,
            reason_tag="price",
            contextual_intent="wants_cheaper_alternative",
            action=CONTINUATION_ACTION_SEND_CHEAPER,
            cart_total=500.0,
            first_seen_at=None,
            has_real_alternative=False,
        )
        self.assertEqual(line, "")
        self.assertFalse(apply)

    def test_offer_allowed_when_rules_pass(self) -> None:
        st = SimpleNamespace(
            cf_merchant_offer_settings_json=json.dumps(
                {
                    "offer_enabled": True,
                    "enable_discount_offers": True,
                    "discount_code": "SAVE10",
                    "discount_percent": 10,
                    "offer_trigger_reason": "price",
                    "offer_min_cart_total": 100.0,
                    "offer_delay_minutes": 0,
                    "offer_max_uses": 5,
                },
                ensure_ascii=False,
            ),
            cf_offer_applications_count=0,
        )
        line, apply = decide_merchant_offer_line(
            st,
            reason_tag="price",
            contextual_intent="wants_cheaper_alternative",
            action=CONTINUATION_ACTION_SEND_CHEAPER,
            cart_total=200.0,
            first_seen_at=None,
            has_real_alternative=False,
        )
        self.assertTrue(apply)
        self.assertIn("SAVE10", line)

    def test_build_snapshot_finds_catalog_alternative(self) -> None:
        store = SimpleNamespace(
            cf_product_catalog_json=json.dumps(
                {
                    "version": 1,
                    "products": [
                        {
                            "id": "c2",
                            "name": "سماعة اقتصادية",
                            "price": 80.0,
                            "category": "إلكترونيات",
                            "url": "https://ex/p2",
                            "available": True,
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            cf_merchant_offer_settings_json=None,
            cf_offer_applications_count=0,
        )
        ac = AbandonedCart(
            zid_cart_id="z_pi_1",
            raw_payload=json.dumps(
                {
                    "cart": {
                        "line_items": [
                            {
                                "name": "سماعة فاخرة",
                                "unit_price": 200.0,
                                "category": "إلكترونيات",
                            }
                        ]
                    }
                },
                ensure_ascii=False,
            ),
            cart_value=200.0,
        )
        snap = build_product_intelligence_snapshot(ac, store)
        self.assertIsNotNone(snap.alternative)
        assert snap.alternative is not None
        self.assertLess(snap.alternative.price, 200.0)
        self.assertIsNotNone(snap.alternative_score)
        assert snap.alternative_score is not None
        self.assertGreater(snap.alternative_score, 0.0)

    def test_cheaper_message_fallback_no_fake_product(self) -> None:
        vars_map = {
            "checkout_url": "https://c.example",
            "alternative_product_name": "",
            "alternative_checkout_url": "https://c.example",
            "alternative_product_price_display": "",
            "current_product_name_display": "",
            "shipping_estimate": "3-7",
            "cheaper_reply_mode": "fallback",
            "has_price_context": "0",
            "current_product_price_display": "",
            "merchant_offer_line": "",
            "merchant_offer_applied": "0",
            "cheaper_candidate_score": "",
            "cheaper_fallback_reason": "no_eligible_cheaper_in_category",
        }
        msg = build_continuation_message(CONTINUATION_ACTION_SEND_CHEAPER, vars_map)
        self.assertIn("ميزانيتك", msg)
        self.assertNotIn("خيار بسعر أوضح", msg)

    def test_cheaper_message_real_format_short_sa(self) -> None:
        vars_map = {
            "checkout_url": "https://c.example/cart",
            "alternative_product_name": "Essentials — هودي قطني خفيف",
            "alternative_checkout_url": "/demo/store/product/12",
            "alternative_product_price_display": "89",
            "current_product_name_display": "Luxe — هودي صوفي",
            "shipping_estimate": "3-7",
            "cheaper_reply_mode": "real",
            "has_price_context": "1",
            "current_product_price_display": "149.00",
            "merchant_offer_line": "",
            "merchant_offer_applied": "0",
            "cheaper_candidate_score": "70",
            "cheaper_fallback_reason": "",
        }
        with patch.dict(os.environ, {"CARTFLOW_PUBLIC_BASE_URL": "https://shop.example"}):
            msg = build_continuation_message(CONTINUATION_ACTION_SEND_CHEAPER, vars_map)
        self.assertIn("لقينا لك خيار قريب", msg)
        self.assertIn("89 ريال", msg)
        self.assertIn("تقدر تشوفه هنا:", msg)
        self.assertIn("https://shop.example/demo/store/product/12", msg)

    def test_select_cheaper_same_fashion_category_hoodie(self) -> None:
        primary = CatalogEntry(
            product_id="demo_hoodie",
            name="Luxe — هودي صوفي",
            price=149.0,
            category="أزياء",
            url="/demo/store/product/13",
            available=True,
            normalized_category="الموضة والأزياء",
            product_family="luxe_apparel",
        )
        ess = CatalogEntry(
            product_id="demo_hoodie_essentials",
            name="Essentials — هودي قطني خفيف",
            price=89.0,
            category="أزياء",
            url="/demo/store/product/12",
            available=True,
            normalized_category="الموضة والأزياء",
            product_family="luxe_apparel",
        )
        pick = select_cheaper_alternative(
            primary=primary,
            cart_entries=[],
            catalog_entries=[ess],
            recovery_category_label="أزياء",
        )
        self.assertIsNotNone(pick.entry)
        assert pick.entry is not None
        self.assertEqual(pick.entry.product_id, "demo_hoodie_essentials")
        self.assertLess(pick.entry.price, primary.price)

    def test_decide_continuation_mock_cart_no_store(self) -> None:
        from unittest.mock import MagicMock

        ac = MagicMock(spec=AbandonedCart)
        ac.zid_cart_id = "c1"
        ac.recovery_session_id = "s1"
        ac.cart_url = ""
        ac.store_id = None
        ac.raw_payload = None
        d = decide_continuation(
            inbound_body="أرخص",
            behavioral={},
            reason_tag="price",
            ac=ac,
            prior_behavioral_before_reply={},
        )
        self.assertEqual(d.action, CONTINUATION_ACTION_SEND_CHEAPER)
        self.assertTrue(d.should_send)

    def test_select_cheaper_rejects_cross_category_perfume(self) -> None:
        primary = CatalogEntry(
            product_id="hp1",
            name="TrueSound Pro — سماعة",
            price=449.0,
            category="إلكترونيات",
            url="",
            available=True,
        )
        wrong_cat = CatalogEntry(
            product_id="p1",
            name="Velvet Musk — عطر",
            price=49.0,
            category="عطور",
            url="https://x/p",
            available=True,
        )
        pick = select_cheaper_alternative(
            primary=primary,
            cart_entries=[wrong_cat],
            catalog_entries=[],
            recovery_category_label="إلكترونيات",
        )
        self.assertIsNone(pick.entry)

    def test_select_cheaper_synonym_beauty_categories(self) -> None:
        primary = CatalogEntry(
            product_id="a",
            name="Amber Oud — عطر",
            price=289.0,
            category="عطور",
            url="",
            available=True,
        )
        cheaper = CatalogEntry(
            product_id="b",
            name="Velvet Musk — عطر يومي",
            price=149.0,
            category="العناية والتجميل",
            url="https://x/b",
            available=True,
        )
        pick = select_cheaper_alternative(
            primary=primary,
            cart_entries=[cheaper],
            catalog_entries=[],
            recovery_category_label=None,
        )
        self.assertIsNotNone(pick.entry)
        assert pick.entry is not None
        self.assertEqual(pick.entry.product_id, "b")

    def test_select_cheaper_prefers_same_product_family(self) -> None:
        primary = CatalogEntry(
            product_id="p",
            name="TrueSound Pro — سماعة",
            price=449.0,
            category="إلكترونيات",
            url="",
            available=True,
            product_family="truesound_headphones",
        )
        charger = CatalogEntry(
            product_id="c",
            name="Nano charger",
            price=29.0,
            category="إلكترونيات",
            url="https://x/c",
            available=True,
            product_family="usb_power",
        )
        earbuds = CatalogEntry(
            product_id="e",
            name="TrueSound Lite — سماعة",
            price=199.0,
            category="إلكترونيات",
            url="https://x/e",
            available=True,
            product_family="truesound_headphones",
        )
        pick = select_cheaper_alternative(
            primary=primary,
            cart_entries=[charger, earbuds],
            catalog_entries=[],
            recovery_category_label="إلكترونيات",
        )
        self.assertIsNotNone(pick.entry)
        assert pick.entry is not None
        self.assertEqual(pick.entry.product_id, "e")


if __name__ == "__main__":
    unittest.main()
