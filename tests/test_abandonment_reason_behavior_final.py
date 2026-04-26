# -*- coding: utf-8 -*-
"""
Final verification: abandonment reason widget behavior (source + API + storage).
Complements browser checks on /demo/cart.
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

_EXPECTED_MESSAGE_SNIPPETS = {
    "price": "أفهمك، السعر مهم",
    "quality": "نأكد لك اهتمامك بالجودة",
    "warranty": "معلومات الضمان غير موضحة",
    "shipping": "مدة الشحن تختلف",
    "thinking": "خذ وقتك",
}


class AbandonmentReasonBehaviorFinalTests(unittest.TestCase):
    """Test 1–6: widget open, response copy, storage, other flow, send, handoff."""

    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        ensure_store_widget_schema(db)
        with open(_WIDGET, encoding="utf-8") as f:
            self.widget_src = f.read()

    def test_1_widget_stays_open_after_reason(self) -> None:
        """
        No bubble dismiss on option pick: only 'لا' removes the bubble from DOM.
        showStandardResponse leads to mountProductAwareView (no bubble remove).
        """
        # Whole bubble is removed for minimize, "لا", and × only — not for reason pick
        n_close = self.widget_src.count("w.parentNode.removeChild(w)")
        self.assertEqual(3, n_close, "minimize, No, and × remove the bubble from DOM")
        # Standard path: no parentNode.removeChild near showStandardResponse
        self.assertIn("function showStandardResponse", self.widget_src)
        self.assertIn("function mountProductAwareView", self.widget_src)
        start = self.widget_src.find("function showStandardResponse")
        self.assertNotEqual(-1, start)
        self.assertNotIn(
            "parentNode.removeChild(w)", self.widget_src[start : start + 420]
        )
        # Demo page for manual step 1
        r = self.client.get("/demo/cart")
        self.assertEqual(200, r.status_code)
        self.assertIn("widget_loader.js", (r.text or ""))

    def test_2_response_message_per_reason(self) -> None:
        """getProductAwareCopy + fallback substrings + actions + back for each key."""
        self.assertIn("getProductAwareCopy", self.widget_src)
        self.assertIn("buildProductContext", self.widget_src)
        for _rkey, needle in _EXPECTED_MESSAGE_SNIPPETS.items():
            self.assertIn(needle, self.widget_src, needle[:20])
        self.assertIn("رجوع", self.widget_src)
        self.assertIn("تحويل لصاحب المتجر", self.widget_src)
        self.assertIn("✔ تم تسجيل سبب التردد", self.widget_src)
        self.assertIn("appendReasonPersonalizationBlock", self.widget_src)

    def test_3_post_and_cart_recovery_reason_and_tag_key(self) -> None:
        """Each POST updates CartRecoveryReason; source sets sessionStorage key."""
        self.assertIn("cartflow_reason_tag", self.widget_src)
        self.assertIn("cartflow_reason_sub_tag", self.widget_src)
        self.assertIn("setReasonSubTag", self.widget_src)
        self.assertIn("setReasonTag", self.widget_src)
        for i, (rkey, rlabel) in enumerate(
            [
                ("price", "p"),
                ("quality", "q"),
                ("warranty", "w"),
                ("shipping", "s"),
                ("thinking", "t"),
            ]
        ):
            part = f"crr-3-final-{i}-{rkey}"
            body: dict = {
                "store_slug": "demo",
                "session_id": part,
                "reason": rkey,
            }
            if rkey == "price":
                body["sub_category"] = "price_discount_request"
            r = self.client.post(
                "/api/cartflow/reason",
                json=body,
            )
            self.assertEqual(200, r.status_code, f"{rlabel} {r.text}")
            self.assertTrue((r.json() or {}).get("ok"), rkey)
            crr = (
                db.session.query(CartRecoveryReason)
                .filter(
                    CartRecoveryReason.store_slug == "demo",
                    CartRecoveryReason.session_id == part,
                )
                .first()
            )
            self.assertIsNotNone(crr, f"CartRecoveryReason {rkey}")
            self.assertEqual(rkey, crr.reason)
            if rkey == "price":
                self.assertEqual("price_discount_request", (crr.sub_category or "").strip())
            else:
                self.assertIsNone(crr.sub_category)
            alog = (
                db.session.query(AbandonmentReasonLog)
                .filter(AbandonmentReasonLog.session_id == part)
                .order_by(AbandonmentReasonLog.id.desc())
                .first()
            )
            self.assertIsNotNone(alog)
            self.assertEqual(rkey, alog.reason)
            if rkey == "price":
                self.assertEqual(
                    "price_discount_request", (alog.sub_category or "").strip()
                )
            else:
                self.assertIsNone(alog.sub_category)

    def test_4_other_path_ui(self) -> None:
        """سبب آخر: textarea, buttons, no 'تواصل عبر واتساب'."""
        s = self.widget_src
        self.assertEqual(0, s.count("تواصل عبر واتساب"))
        i_o = s.find("function mountOtherForm")
        i_ta = s.find("createElement(\"textarea\"")
        i_send = s.find("bSend.textContent =", i_o)
        i_ho = s.find("bHandoffO", i_o)
        self.assertNotEqual(-1, i_o, "other form")
        self.assertNotEqual(-1, s.find("createElement(\"textarea\"", i_o))
        self.assertNotEqual(-1, i_send)
        self.assertNotEqual(-1, i_ho)
        self.assertNotEqual(-1, s.find("إرسال السبب", i_o))
        self.assertIn("showOtherSuccessView", s)
        self.assertIn("bSend.type", s)
        self.assertIn("اكتب السبب أو اطلب تحويلك لصاحب المتجر", s)

    def test_5_send_other_persist_and_message(self) -> None:
        """reason=other, custom_text in DB; confirmation copy in widget."""
        session_id = "final-5-other"
        custom = "نص اختباري"
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": session_id,
                "reason": "other",
                "custom_text": custom,
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.session_id == session_id,
            )
            .first()
        )
        self.assertIsNotNone(crr)
        self.assertEqual("other", crr.reason)
        self.assertEqual(custom, (crr.custom_text or "").strip())
        alog = (
            db.session.query(AbandonmentReasonLog)
            .filter(AbandonmentReasonLog.session_id == session_id)
            .order_by(AbandonmentReasonLog.id.desc())
            .first()
        )
        self.assertIsNotNone(alog)
        self.assertEqual("other", alog.reason)
        # Widget shows personalization confirmation; does not close bubble on this path
        self.assertIn("data-cf-reason-confirm", self.widget_src)
        self.assertIn("showOtherSuccessView", self.widget_src)

    def test_6_merchant_handoff_human_support(self) -> None:
        """human_support stored; public-config for WhatsApp; widget continues."""
        session_id = "final-6-handoff"
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": session_id,
                "reason": "human_support",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json() or {}
        self.assertTrue(j.get("ok"))
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.session_id == session_id)
            .first()
        )
        self.assertIsNotNone(crr)
        self.assertEqual("human_support", crr.reason)
        g = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": "demo"}
        )
        self.assertEqual(200, g.status_code)
        jg = g.json() or {}
        self.assertTrue(jg.get("ok"))
        self.assertIn("whatsapp_url", jg)
        # Handoff: postReason then fetch public-config in widget
        self.assertIn("postReason({ reason: \"human_support\" })", self.widget_src)


if __name__ == "__main__":
    unittest.main()
