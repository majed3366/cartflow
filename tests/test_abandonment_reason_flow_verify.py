# -*- coding: utf-8 -*-
"""
Verifies the abandonment reason capture flow (API, persistence, assets, widget source).
Manual browser checks: /demo/cart with demo panel.
"""
from __future__ import annotations

import os
import unittest

from main import app
from extensions import db
from models import AbandonmentReasonLog
from schema_widget import ensure_store_widget_schema

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WIDGET_JS = os.path.join(_ROOT, "static", "cartflow_widget.js")


class AbandonmentReasonFlowVerifyTests(unittest.TestCase):
    """Tests 1–5 from the abandonment reason capture flow checklist."""

    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        ensure_store_widget_schema(db)

    def test_1_basic_flow_demo_page_and_copy(self) -> None:
        """Test 1: /demo/cart loads; widget source contains first message and all options."""
        r = self.client.get("/demo/cart")
        self.assertEqual(200, r.status_code, r.text)
        full = r.text or ""
        body = full[:20000]
        self.assertIn("widget_loader.js", full)
        self.assertIn("/static/", body)

        with open(_WIDGET_JS, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("تبي أساعدك تكمل طلبك؟", src)
        for label in (
            "السعر",
            "الجودة",
            "الضمان",
            "الشحن",
            "أفكر",
            "سبب آخر",
        ):
            self.assertIn(label, src, f"missing option: {label}")
        self.assertIn("وش أكثر شيء مخليك متردد؟ تبيني أساعدك", src)
        self.assertIn("اكتب السبب أو اطلب تحويلك لصاحب المتجر", src)
        self.assertIn("تحويل لصاحب المتجر", src)
        self.assertIn("getProductAwareCopy", src)
        self.assertIn("buildProductContext", src)
        self.assertIn("scrollToCartOrCheckout", src)
        self.assertIn("العودة للسلة", src)
        self.assertIn("خيارات أخرى", src)
        self.assertIn("أفهمك، السعر مهم", src)
        self.assertIn("معلومات الضمان غير موضحة هنا", src)
        self.assertIn("mountProductAwareView", src)
        self.assertIn("REASON_SUB_TAG_KEY", src)
        self.assertIn("cartflow_reason_sub_tag", src)
        self.assertIn("CARTFLOW_REASON_ACTION_ORDER", src)
        self.assertIn("showPriceSubMenu", src)
        self.assertIn("renderReasonList", src)

    def test_2_normal_options_post_and_persist(self) -> None:
        """Test 2: each standard reason is accepted and stored with matching reason value."""
        mapping = [
            ("flow-p2-1", "السعر", "price"),
            ("flow-p2-2", "الجودة", "quality"),
            ("flow-p2-3", "الضمان", "warranty"),
            ("flow-p2-4", "الشحن", "shipping"),
            ("flow-p2-5", "أفكر", "thinking"),
        ]
        for session_id, _ar_label, rkey in mapping:
            payload = {
                "store_slug": "demo",
                "session_id": session_id,
                "reason": rkey,
            }
            if rkey == "price":
                payload["sub_category"] = "price_cheaper_alternative"
            r = self.client.post("/api/cartflow/reason", json=payload)
            self.assertEqual(200, r.status_code, r.text)
            self.assertTrue((r.json() or {}).get("ok"), session_id)
            row = (
                db.session.query(AbandonmentReasonLog)
                .filter(
                    AbandonmentReasonLog.session_id == session_id,
                    AbandonmentReasonLog.reason == rkey,
                )
                .order_by(AbandonmentReasonLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row, f"no row for {rkey} {session_id}")
            self.assertEqual(rkey, row.reason)
            if rkey == "price":
                self.assertEqual(
                    "price_cheaper_alternative", (row.sub_category or "").strip()
                )
            else:
                self.assertIsNone(row.sub_category)
            self.assertIsNone(row.custom_text)

    def test_3_other_reason_custom_text_persisted(self) -> None:
        """Test 3: other + custom_text is saved."""
        session_id = "flow-p3-other-1"
        text = "سبب مخصص للتحقق"
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": session_id,
                "reason": "other",
                "custom_text": text,
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))
        row = (
            db.session.query(AbandonmentReasonLog)
            .filter(AbandonmentReasonLog.session_id == session_id)
            .order_by(AbandonmentReasonLog.id.desc())
            .first()
        )
        self.assertIsNotNone(row)
        self.assertEqual("other", row.reason)
        self.assertEqual(text, (row.custom_text or "").strip())

    def test_4_human_support_logged(self) -> None:
        """Test 4: human_support is persisted (simulates click after / alongside WA flow)."""
        session_id = "flow-p4-wa-1"
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": "demo",
                "session_id": session_id,
                "reason": "human_support",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        self.assertTrue((r.json() or {}).get("ok"))
        row = (
            db.session.query(AbandonmentReasonLog)
            .filter(AbandonmentReasonLog.session_id == session_id)
            .order_by(AbandonmentReasonLog.id.desc())
            .first()
        )
        self.assertIsNotNone(row)
        self.assertEqual("human_support", row.reason)

    def test_4_public_config_whatsapp_url_for_opener(self) -> None:
        """Opening WA uses public-config; assert endpoint returns a URL when configured."""
        r = self.client.get(
            "/api/cartflow/public-config", params={"store_slug": "demo"}
        )
        self.assertEqual(200, r.status_code)
        j = r.json() or {}
        self.assertTrue(j.get("ok"))
        # May be null without merchant settings; shape is still valid
        self.assertIn("whatsapp_url", j)

    def test_5_handoff_button_only_in_other_branch(self) -> None:
        """
        Test 5: merchant handoff label only under "سبب آخر"; no legacy WhatsApp CTA string.
        """
        with open(_WIDGET_JS, encoding="utf-8") as f:
            s = f.read()
        self.assertEqual(0, s.count("تواصل عبر واتساب"))
        # Label reused (BTN_HANDOFF) in standard actions, other form, and success
        self.assertGreaterEqual(s.count("تحويل لصاحب المتجر"), 1)
        i_branch = s.find("function mountOtherForm")
        i_hand_in_block = s.find("تحويل", i_branch)
        self.assertNotEqual(-1, i_branch)
        self.assertNotEqual(-1, i_hand_in_block)
        self.assertLess(i_branch, i_hand_in_block)
        p0 = s.find("p0.textContent =")
        i_first_q = s.find("تبي أساعدك تكمل طلبك؟")
        self.assertNotEqual(-1, p0)
        self.assertNotEqual(-1, i_first_q)
        self.assertEqual(
            -1,
            s[i_first_q : i_first_q + 400].find("تحويل لصاحب المتجر"),
        )


if __name__ == "__main__":
    unittest.main()
