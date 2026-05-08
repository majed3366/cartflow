# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest
import uuid

from extensions import db
from models import AbandonedCart, Store

from services.recovery_product_suggestions import (
    get_product_aware_recovery_suggestion,
    get_product_aware_recovery_suggestion_for_abandoned_cart,
)


class RecoveryProductSuggestionsTests(unittest.TestCase):
    def test_price_reassurance_without_alternative(self) -> None:
        s = get_product_aware_recovery_suggestion(
            "price",
            "حقيبة جلدية",
            199.0,
            "إكسسوارات",
            "غالي",
        )
        self.assertIn("الجودة", s["suggested_reply"])
        self.assertIn("قيمة", s["suggested_strategy"])
        self.assertEqual(s["optional_offer_type"], "value_framing")

    def test_price_alternative_when_cheaper_exists(self) -> None:
        s = get_product_aware_recovery_suggestion(
            "price",
            "منتج أ",
            100.0,
            None,
            "",
            cheaper_alternative_name="منتج ب",
            cheaper_alternative_price=60.0,
        )
        self.assertIn("بسعر أخف", s["suggested_reply"])
        self.assertEqual(s["optional_offer_type"], "alternative_product")
        self.assertEqual(s["ux_badge_ar"], "اقتراح بيع")

    def test_delivery_reassurance(self) -> None:
        s = get_product_aware_recovery_suggestion(
            "delivery",
            "عطر",
            250.0,
            "العناية والتجميل",
            "متى يوصل",
        )
        self.assertIn("التوصيل", s["suggested_reply"])
        self.assertIn("طمأنة", s["suggested_strategy"])

    def test_ready_to_buy_checkout_mode(self) -> None:
        s = get_product_aware_recovery_suggestion(
            "ready_to_buy",
            "x",
            1.0,
            None,
            "",
        )
        self.assertIn("رابط إكمال الطلب", s["suggested_reply"])
        self.assertIn("حاضر", s["suggested_reply"])
        self.assertEqual(s["checkout_cta_mode"], "calm_checkout_push")
        self.assertEqual(s["ux_badge_ar"], "فرصة تحويل مرتفعة")

    def test_adaptive_checkout_ready_overrides_price_copy(self) -> None:
        s = get_product_aware_recovery_suggestion(
            "price",
            "حقيبة",
            199.0,
            None,
            "غالي لكن تمام",
            adaptive_stage="checkout_ready",
        )
        self.assertIn("مساعدة أنا حاضر", s["suggested_reply"])
        self.assertNotIn("الجودة", s["suggested_reply"])

    def test_for_abandoned_cart_reads_items(self) -> None:
        db.create_all()
        suf = uuid.uuid4().hex[:10]
        st = Store(
            zid_store_id=f"pc-sugg-{suf}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        raw = {
            "cf_behavioral": {"customer_replied": True},
            "cart": {
                "items": [
                    {"name": "ساعة رياضية", "unit_price": 400},
                    {"name": "سوار ذكي بسيط", "price": 150},
                ]
            },
        }
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=f"z-pc-{suf}",
            recovery_session_id=f"s-pc-{suf}",
            customer_phone="+966501111111",
            status="abandoned",
            vip_mode=False,
            cart_value=400.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.commit()

        s = get_product_aware_recovery_suggestion_for_abandoned_cart(
            ac,
            "price",
            "غالي",
        )
        self.assertIn("بسعر أخف", s["suggested_reply"])
        self.assertEqual(s["optional_offer_type"], "alternative_product")

        try:
            db.session.delete(ac)
            db.session.delete(st)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()


if __name__ == "__main__":
    unittest.main()
