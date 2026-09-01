# -*- coding: utf-8 -*-
"""Merchant Product Composition Refinement V1 — contracts (no invented truth)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
HOME_CSS = (ROOT / "static" / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
COMMS_CSS = (ROOT / "static" / "merchant_ui_v2_comms.css").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(
    encoding="utf-8"
)
PARTIAL = (
    ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html"
).read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")


class ContextualSidebarCoverage(unittest.TestCase):
    def test_carts_comms_settings_have_page_specific_ctx(self) -> None:
        self.assertIn("carts: {", APP_JS)
        self.assertIn("comms: {", APP_JS)
        self.assertIn("settings: {", APP_JS)
        self.assertIn('label: "يحتاجني"', APP_JS)
        self.assertIn('label: "يحتاج متابعتي"', APP_JS)
        self.assertIn('label: "إعدادات واتساب"', APP_JS)
        self.assertNotIn("carts: null", APP_JS)
        self.assertNotIn("comms: null", APP_JS)
        self.assertNotIn("settings: null", APP_JS)

    def test_ctx_binds_page_filters(self) -> None:
        self.assertIn("applyCtxItem", APP_JS)
        self.assertIn("CartFlowUiV2Carts.setFilter", APP_JS)
        self.assertIn("CartFlowUiV2Comms.setFilter", APP_JS)
        self.assertIn("CartFlowUiV2Settings.showPanel", APP_JS)
        self.assertIn("setFilter: setFilter", CARTS_JS)
        self.assertIn("setFilter: setFilter", COMMS_JS)

    def test_products_ctx_still_null(self) -> None:
        self.assertIn("products: null", APP_JS)


class HomeRecoveryOutcome(unittest.TestCase):
    def test_operational_kpi_summary_only(self) -> None:
        self.assertIn("recoveryOutcomeHtml", HOME_JS)
        self.assertIn("cf2-home__recovery", HOME_JS)
        self.assertIn("merchant_kpi_recovered_fmt", HOME_JS)
        self.assertIn("merchant_kpi_revenue_fmt", HOME_JS)
        self.assertIn("operational-kpi-v1", HOME_JS)
        self.assertIn("وليس إسناد شراء منسوباً", HOME_JS)
        self.assertIn("cf2-home__recovery", HOME_CSS)

    def test_no_fabricated_attribution_claim(self) -> None:
        self.assertNotIn("purchase_attribution", HOME_JS.lower())


class CommsCanonicalForms(unittest.TestCase):
    def test_no_circular_status_ticks(self) -> None:
        tick_rule = re.search(
            r"body\[data-cf-ui=\"v2\"\] \.cf2-comms__tick \{([^}]+)\}",
            COMMS_CSS,
        )
        self.assertIsNotNone(tick_rule)
        body = tick_rule.group(1) if tick_rule else ""
        self.assertNotIn("border-radius: 50%", body)
        self.assertIn("clip-path", body)

    def test_lifecycle_forms_map_to_cf_grammar(self) -> None:
        self.assertIn('data-cf2-tick="send"', COMMS_CSS)
        self.assertIn('data-cf2-tick="delivery"', COMMS_CSS)
        self.assertIn('data-cf2-tick="response"', COMMS_CSS)
        self.assertIn('data-cf2-tick="wait"', COMMS_CSS)
        self.assertIn('data-cf2-tick="followup"', COMMS_CSS)


class CommsMessageContent(unittest.TestCase):
    def test_body_from_persisted_fields_only(self) -> None:
        self.assertIn("messageBodyFromRow", COMMS_JS)
        self.assertIn("full_message_ar", COMMS_JS)
        self.assertIn("preview_ar", COMMS_JS)
        self.assertIn("cf2-comms__body", COMMS_JS)
        self.assertIn("نص الرسالة غير متاح في السجل", COMMS_JS)
        self.assertNotIn("template_ar ||", COMMS_JS)


class SettingsWhatsAppNaming(unittest.TestCase):
    def test_settings_area_renamed_primary_preserved(self) -> None:
        self.assertIn('title: "إعدادات واتساب"', SETTINGS_JS)
        self.assertIn("إعدادات واتساب", PARTIAL)
        self.assertIn('{ id: "comms", label: "التواصل"', APP_JS)
        self.assertNotIn('title: "التواصل"', SETTINGS_JS)
        self.assertNotIn("واتساب والتواصل", PARTIAL)

    def test_mpcr_cache_bust(self) -> None:
        self.assertIn("mpcr1", V2_HTML)
