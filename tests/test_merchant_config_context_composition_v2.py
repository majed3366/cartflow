# -*- coding: utf-8 -*-
"""Merchant Configuration & Context Composition V2 — contracts."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME_JS = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
HOME_CSS = (ROOT / "static" / "merchant_ui_v2_home.css").read_text(encoding="utf-8")
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(encoding="utf-8")
COMMS_JS = (ROOT / "static" / "merchant_ui_v2_comms.js").read_text(encoding="utf-8")
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")
WA_MODE = (ROOT / "services" / "merchant_whatsapp_mode_v1.py").read_text(encoding="utf-8")
WA_PRES = (
    ROOT / "services" / "merchant_whatsapp_readiness_presentation_v1.py"
).read_text(encoding="utf-8")
MSG_PRES = (
    ROOT / "services" / "merchant_message_presentation_v1.py"
).read_text(encoding="utf-8")
PARTIAL = (
    ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html"
).read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
WIDGET_JS = (ROOT / "static" / "merchant_widget_panel.js").read_text(encoding="utf-8")


class HomeSummaryIndependent(unittest.TestCase):
    def test_overview_no_recovery_strip(self) -> None:
        self.assertIn("renderSummaryView", HOME_JS)
        self.assertIn("showView", HOME_JS)
        self.assertIn("cf2-home--summary", HOME_JS)
        render_match = re.search(
            r"function render\(pkg\) \{(.*?)\n  \}\n\n  function paint",
            HOME_JS,
            re.DOTALL,
        )
        self.assertIsNotNone(render_match, "expected render(pkg) function body")
        render_body = render_match.group(1) if render_match else ""
        self.assertNotIn("recoveryOutcomeHtml", render_body)
        self.assertNotIn("cf2-home__recovery", render_body)

    def test_home_ctx_wired(self) -> None:
        self.assertIn("CartFlowUiV2Home.showView", APP_JS)
        self.assertIn('"summary", label: "الملخص"', APP_JS)


class RecoveryReasonTemplates(unittest.TestCase):
    def test_recovery_panel_hosts_templates(self) -> None:
        self.assertIn('id="ma-tpl-root"', PARTIAL)
        self.assertIn("maEnsureTriggerTemplatesLoaded", SETTINGS_JS)
        self.assertIn('"trigger-templates": "recovery"', SETTINGS_JS)


class WidgetRenameAndConfig(unittest.TestCase):
    def test_widget_label_not_experience(self) -> None:
        self.assertIn('title: "الودجيت"', SETTINGS_JS)
        self.assertNotIn('title: "التجربة"', SETTINGS_JS)
        self.assertIn('{ id: "experience", label: "الودجيت"', APP_JS)
        self.assertIn("mw-widget-color", PARTIAL)
        self.assertIn("mw-hes-cond", PARTIAL)
        self.assertIn("maInitWidgetSettingsPage", WIDGET_JS)

    def test_setcomp2_cache_bust(self) -> None:
        self.assertIn("setcomp2", V2_HTML)


class EmojiFormsRemoved(unittest.TestCase):
    def test_whatsapp_mode_no_emoji(self) -> None:
        self.assertNotIn("🟢", WA_MODE)
        self.assertNotIn("💼", WA_MODE)
        self.assertNotIn("🔵", WA_MODE)
        self.assertNotIn("🟢", WA_PRES)

    def test_wa_settings_uses_cf_marker(self) -> None:
        wa_js = (ROOT / "static" / "merchant_whatsapp_settings.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("ma-wa-mode-marker", wa_js)
        self.assertIn("data-cf2-wa-mode", wa_js)


class MockSentPresentation(unittest.TestCase):
    def test_internal_body_stripped(self) -> None:
        from services.merchant_message_presentation_v1 import (
            merchant_visible_message_body,
        )

        self.assertEqual(
            merchant_visible_message_body("[SRS] mock_sent — no provider call"),
            "",
        )

    def test_falsification_cases(self) -> None:
        from services.merchant_message_presentation_v1 import (
            is_internal_merchant_message_body,
            merchant_visible_message_body,
        )

        genuine = "مرحباً، لاحظنا أنك تركت سلة مشتريات — هل نساعدك؟"
        self.assertEqual(merchant_visible_message_body(genuine), genuine)
        self.assertFalse(is_internal_merchant_message_body(genuine))

        srs = "[SRS] mock_sent — no provider call"
        self.assertEqual(merchant_visible_message_body(srs), "")
        self.assertTrue(is_internal_merchant_message_body(srs))

        recovery = "أهلاً {customer_name}، سلتك بانتظارك — أكمل الطلب الآن."
        self.assertEqual(
            merchant_visible_message_body(recovery, status="sent_real"), recovery
        )
        self.assertEqual(
            merchant_visible_message_body(recovery, status="mock_sent"), recovery
        )

        empty = merchant_visible_message_body("", status="mock_sent")
        self.assertEqual(empty, "")
        self.assertEqual(merchant_visible_message_body("—"), "")

        ordinary_with_mock_word = "تم إرسال mock_sent test في تجربة المتجر"
        self.assertEqual(
            merchant_visible_message_body(ordinary_with_mock_word),
            ordinary_with_mock_word,
        )

    def test_comms_js_filters_srs(self) -> None:
        self.assertIn("mock_sent", COMMS_JS)
        self.assertIn("no provider call", COMMS_JS)


class SidebarMaturity(unittest.TestCase):
    def test_ctx_counts_exported(self) -> None:
        self.assertIn("ctxCounts", CARTS_JS)
        self.assertIn("ctxCounts", COMMS_JS)
        self.assertIn("ctxHint", SETTINGS_JS)
        self.assertIn("refreshContextualSidebar", APP_JS)


class ProductsUnchanged(unittest.TestCase):
    def test_products_ctx_null(self) -> None:
        self.assertIn("products: null", APP_JS)


if __name__ == "__main__":
    unittest.main()
