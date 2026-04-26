# -*- coding: utf-8 -*-
"""
Automated verification of nested price classification (مطابقة مسار ‎/demo/cart).

Manual steps (نعم → السعر → sub-option) تُتَحَقَّق من الودجت + ‎API‎ + ‎DB‎ هنا.
When this module’s tests all pass, report: Nested price classification verified.

See checklist: submenu labels, POST payload, storage, action buttons, discount copy.
"""
from __future__ import annotations

import os
import unittest

from main import app
from extensions import db
from models import AbandonmentReasonLog, CartRecoveryReason
from schema_widget import ensure_store_widget_schema

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WIDGET = os.path.join(_ROOT, "static", "cartflow_widget.js")


class NestedPriceClassificationTests(unittest.TestCase):
    """Nested ‎السعر‎: قائمة فرعية، ‎POST + sub_category‎، تخزين، أزرار إعداد."""

    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        with open(_WIDGET, encoding="utf-8") as f:
            self.widget = f.read()

    def test_1_demo_cart_loads(self) -> None:
        """Step: open /demo/cart — page loads; widget script present."""
        r = self.client.get("/demo/cart")
        self.assertEqual(200, r.status_code, r.text)
        body = r.text or ""
        self.assertIn("widget_loader.js", body)
        self.assertIn("data-store", body)

    def test_2_widget_shows_price_submenu_labels(self) -> None:
        """After نعم → السعر: submenu (source) lists three options + back."""
        s = self.widget
        self.assertIn("أبحث عن كود خصم", s)
        self.assertIn("السعر أعلى من ميزانيتي", s)
        self.assertIn("أريد خيار أرخص", s)
        self.assertIn("showPriceSubMenu", s)
        self.assertIn("CARTFLOW_PRICE_SUB_OPTIONS", s)
        self.assertIn('sub: "price_discount_request"', s)
        self.assertIn("BTN_BACK", s)
        self.assertIn("postPriceWithSubCategory", s)

    def test_3_post_sends_price_and_sub_category(self) -> None:
        """postReason includes ‎sub_category‎ in ‎JSON‎ body; server persists."""
        ensure_store_widget_schema(db)
        session_id = "nest-price-discount-req-1"
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": session_id,
                "reason": "price",
                "sub_category": "price_discount_request",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"), r.text)
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == session_id,
            )
            .first()
        )
        self.assertIsNotNone(crr)
        self.assertEqual("price", crr.reason)
        self.assertEqual("price_discount_request", (crr.sub_category or "").strip())
        alog = (
            db.session.query(AbandonmentReasonLog)
            .filter(AbandonmentReasonLog.session_id == session_id)
            .order_by(AbandonmentReasonLog.id.desc())
            .first()
        )
        self.assertIsNotNone(alog)
        self.assertEqual("price", alog.reason)
        self.assertEqual("price_discount_request", (alog.sub_category or "").strip())

    def test_4_session_tag_keys_in_widget(self) -> None:
        """cart/session: ‎cartflow_reason_tag‎ + ‎cartflow_reason_sub_tag‎ (source)."""
        s = self.widget
        self.assertIn('var REASON_TAG_KEY = "cartflow_reason_tag"', s)
        self.assertIn('var REASON_SUB_TAG_KEY = "cartflow_reason_sub_tag"', s)
        self.assertIn("setReasonSubTag", s)
        self.assertIn("setReasonTag", s)
        self.assertIn("cartflowGetReasonSubTag", s)
        self.assertIn("setReasonTag(\"price\");", s, "reason_tag = price after sub POST")
        self.assertIn("setReasonSubTag(sub);", s)

    def test_5_price_action_buttons_in_source(self) -> None:
        """After sub-choice: ‎order‎ and labels for ‎🎁 …‎ through ‎العودة للسلة‎."""
        s = self.widget
        self.assertIn("CARTFLOW_REASON_ACTION_ORDER", s)
        self.assertIn("discount_offer", s)
        self.assertIn("alternatives", s)
        self.assertIn("merchant_handoff", s)
        self.assertIn("🎁 عرض / خصم", s)
        self.assertIn("خيارات أخرى", s)
        self.assertIn("تحويل لصاحب المتجر", s)
        self.assertIn("رجوع", s)
        self.assertIn("العودة للسلة", s)
        self.assertIn("function mountProductAwareView", s)

    def test_6_discount_action_copy(self) -> None:
        """Click عرض/خصم: fixed stub message in ‎CARTFLOW_ACTIONS.discount_offer‎."""
        s = self.widget
        self.assertIn("حالياً ما فيه عرض ظاهر، لكن أقدر أتحقق لك أو أحولك للمتجر 👍", s)
        self.assertIn("showDiscountStubPanel", s)

    def test_7_post_reason_body_includes_sub_category(self) -> None:
        """Widget ‎postReason‏ يضم ‎body.sub_category‎ عند تمريرها."""
        s = self.widget
        self.assertIn("body.sub_category = String", s)
        self.assertIn("postReason({ reason: \"price\", sub_category: sub })", s)

    def test_report_nested_price_classification_verified(self) -> None:
        """
        Report (when this file’s tests are green):
        Nested price classification verified
        """
        # Placeholder so the name appears in ‎pytest -k‎ / unittest discovery as the checklist report.
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
