# -*- coding: utf-8 -*-
"""Tests for dashboard attention / intervention presentation semantics."""

from __future__ import annotations

import unittest

from services.customer_lifecycle_states_v1 import (
    LABEL_SCHEDULE_NOT_MATERIALIZED_AR,
    LABEL_WAITING_CONTACT_COMPLETION_AR,
    STATE_COMPLETED,
    STATE_CUSTOMER_ENGAGED,
    STATE_CUSTOMER_REPLY,
    STATE_NEEDS_INTERVENTION,
    STATE_RETURN_TO_SITE,
)
from services.dashboard_attention_merchant_semantics_v1 import (
    FOLLOWUP_OPTIONAL_MANUAL_CONTACT_LINE_AR,
    LABEL_CANNOT_FOLLOW_NO_PHONE_AR,
    LABEL_INTERVENTION_AR,
    LABEL_NEEDS_SETUP_AR,
    LABEL_WAITING_PHONE_AR,
    LABEL_WAITING_READY_AR,
    apply_attention_merchant_semantics_v1,
    resolve_needs_intervention_display_label,
)
from services.merchant_decision_layer_v1 import (
    DECISION_CONTACT_CUSTOMER,
    DECISION_FIX_CHANNEL,
    DECISION_OBTAIN_CONTACT,
)


class AttentionMerchantSemanticsTests(unittest.TestCase):
    def test_customer_reply_stays_engagement_not_intervention(self) -> None:
        row = {
            "customer_lifecycle_state": STATE_CUSTOMER_REPLY,
            "customer_lifecycle_label_ar": "رد العميل",
            "customer_lifecycle_merchant_needed_ar": "لا",
            "merchant_has_customer_phone": True,
        }
        apply_attention_merchant_semantics_v1(
            row, customer_phone_raw="0512345678", is_vip_lane=False
        )
        self.assertEqual(row["customer_lifecycle_label_ar"], "رد العميل")
        self.assertFalse(row["merchant_intervention_executable"])
        self.assertEqual(row.get("merchant_attention_display_group"), "engagement")

    def test_customer_engaged_stays_engagement_not_intervention(self) -> None:
        row = {
            "customer_lifecycle_state": STATE_CUSTOMER_ENGAGED,
            "customer_lifecycle_label_ar": "تفاعل العميل — أرسل النظام متابعة",
            "customer_lifecycle_merchant_needed_ar": "لا",
            "merchant_has_customer_phone": True,
        }
        apply_attention_merchant_semantics_v1(row, customer_phone_raw="0512345678")
        self.assertNotIn("تحتاج تدخل", row["customer_lifecycle_label_ar"])
        self.assertFalse(row["merchant_intervention_executable"])

    def test_executable_contact_customer_shows_intervention_and_wa_link(self) -> None:
        row = {
            "customer_lifecycle_state": STATE_NEEDS_INTERVENTION,
            "customer_lifecycle_label_ar": "تحتاج تدخل",
            "customer_lifecycle_merchant_needed_ar": "نعم",
            "merchant_decision_key": DECISION_CONTACT_CUSTOMER,
            "merchant_has_customer_phone": True,
        }
        apply_attention_merchant_semantics_v1(
            row, customer_phone_raw="0512345678", cart_link="https://shop/cart/1"
        )
        self.assertEqual(row["customer_lifecycle_label_ar"], LABEL_INTERVENTION_AR)
        self.assertTrue(row["merchant_intervention_executable"])
        self.assertIn("wa.me/966512345678", row["merchant_intervention_contact_href"])
        self.assertEqual(row["merchant_intervention_action_ar"], "فتح واتساب")

    def test_no_phone_not_intervention_label(self) -> None:
        row = {
            "customer_lifecycle_state": STATE_NEEDS_INTERVENTION,
            "customer_lifecycle_label_ar": LABEL_WAITING_CONTACT_COMPLETION_AR,
            "customer_lifecycle_merchant_needed_ar": "نعم",
            "merchant_decision_key": DECISION_OBTAIN_CONTACT,
            "merchant_has_customer_phone": False,
        }
        apply_attention_merchant_semantics_v1(row, customer_phone_raw="")
        self.assertEqual(row["customer_lifecycle_label_ar"], LABEL_WAITING_PHONE_AR)
        self.assertFalse(row["merchant_intervention_executable"])
        self.assertNotIn("تحتاج تدخل", row["customer_lifecycle_label_ar"])

    def test_schedule_not_materialized_waiting_ready(self) -> None:
        row = {
            "customer_lifecycle_state": STATE_NEEDS_INTERVENTION,
            "customer_lifecycle_label_ar": LABEL_SCHEDULE_NOT_MATERIALIZED_AR,
            "customer_lifecycle_merchant_needed_ar": "لا",
            "merchant_has_customer_phone": True,
        }
        apply_attention_merchant_semantics_v1(row, customer_phone_raw="0512345678")
        self.assertEqual(row["customer_lifecycle_label_ar"], LABEL_WAITING_READY_AR)
        self.assertFalse(row["merchant_intervention_executable"])

    def test_fix_channel_needs_setup_not_intervention(self) -> None:
        label = resolve_needs_intervention_display_label(
            canonical_label_ar="تحتاج تدخل",
            merchant_needed_ar="نعم",
            decision_key=DECISION_FIX_CHANNEL,
            has_phone=True,
            log_statuses=["whatsapp_failed"],
        )
        self.assertEqual(label, LABEL_NEEDS_SETUP_AR)

    def test_completed_row_unchanged(self) -> None:
        row = {
            "customer_lifecycle_state": STATE_COMPLETED,
            "customer_lifecycle_label_ar": "تم الشراء",
            "customer_lifecycle_completed_variant": "purchased",
            "merchant_coarse_status": "converted",
        }
        apply_attention_merchant_semantics_v1(row, customer_phone_raw="0512345678")
        self.assertEqual(row["customer_lifecycle_label_ar"], "تم الشراء")
        self.assertFalse(row["merchant_intervention_executable"])

    def test_return_to_site_unchanged(self) -> None:
        row = {
            "customer_lifecycle_state": STATE_RETURN_TO_SITE,
            "customer_lifecycle_label_ar": "عاد العميل للموقع — نراقب هل يكمل الطلب",
        }
        apply_attention_merchant_semantics_v1(row, customer_phone_raw="0512345678")
        self.assertEqual(
            row["customer_lifecycle_label_ar"],
            "عاد العميل للموقع — نراقب هل يكمل الطلب",
        )

    def test_vip_lane_labels_unchanged(self) -> None:
        row = {
            "customer_lifecycle_state": STATE_NEEDS_INTERVENTION,
            "customer_lifecycle_label_ar": "تحتاج تدخل (VIP)",
            "customer_lifecycle_merchant_needed_ar": "نعم",
            "merchant_decision_key": DECISION_CONTACT_CUSTOMER,
            "merchant_has_customer_phone": True,
        }
        apply_attention_merchant_semantics_v1(
            row, customer_phone_raw="0512345678", is_vip_lane=True
        )
        self.assertEqual(row["customer_lifecycle_label_ar"], "تحتاج تدخل (VIP)")
        self.assertFalse(row["merchant_intervention_executable"])

    def test_no_phone_without_contact_key(self) -> None:
        label = resolve_needs_intervention_display_label(
            canonical_label_ar="تحتاج تدخل",
            merchant_needed_ar="نعم",
            decision_key="",
            has_phone=False,
        )
        self.assertEqual(label, LABEL_CANNOT_FOLLOW_NO_PHONE_AR)


class AttentionMerchantDashboardHtmlTests(unittest.TestCase):
    def setUp(self) -> None:
        import os

        os.environ["ENV"] = "development"
        os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-for-merchant-dashboard")
        from fastapi.testclient import TestClient

        from main import app

        self.client = TestClient(app)

    def test_followup_page_uses_engagement_title_not_intervention(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        idx = html.find('id="page-followup"')
        self.assertGreater(idx, -1)
        section = html[idx : idx + 2500]
        self.assertIn("تفاعل العملاء", section)
        self.assertNotIn("تحتاج تدخل", section)

    def test_carts_filter_uses_engagement_label(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertIn('data-filter="attention">تفاعل العملاء', html)
        self.assertNotIn("يحتاج متابعة", html)

    def test_followup_compact_block_has_no_intervention_no_line(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertNotIn("<strong>تدخل:</strong> لا", html)

    def test_followup_optional_manual_contact_copy_in_lazy_js(self) -> None:
        from pathlib import Path

        js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_dashboard_lazy.js"
        ).read_text(encoding="utf-8")
        self.assertIn(FOLLOWUP_OPTIONAL_MANUAL_CONTACT_LINE_AR, js)
        self.assertIn("فتح واتساب", js)
        self.assertNotIn("تدخل مطلوب", js)
        self.assertNotIn("متابعة يدوية مطلوبة", js)

    def test_followup_template_optional_manual_contact_copy(self) -> None:
        from pathlib import Path

        tpl = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "partials"
            / "merchant_followup_compact_block.html"
        ).read_text(encoding="utf-8")
        self.assertIn(FOLLOWUP_OPTIONAL_MANUAL_CONTACT_LINE_AR, tpl)
        self.assertIn("fr.contact_wa_href", tpl)
        self.assertIn("فتح واتساب", tpl)


if __name__ == "__main__":
    unittest.main()
