# -*- coding: utf-8 -*-
"""Merchant IA & Ownership Reconciliation V3 — contracts."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIAL = (
    ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html"
).read_text(encoding="utf-8")
V2_HTML = (ROOT / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(encoding="utf-8")
VIP_JS = (ROOT / "static" / "merchant_vip_settings.js").read_text(encoding="utf-8")


class RecoveryOwnership(unittest.TestCase):
    def test_no_v1_trigger_templates_handoff(self) -> None:
        self.assertNotIn("cf_ui=v1", PARTIAL)
        self.assertNotIn("cf_ui=v1", V2_HTML)
        self.assertNotIn('href="/dashboard?cf_ui=v1#trigger-templates"', PARTIAL)

    def test_recovery_is_canonical_template_destination(self) -> None:
        self.assertIn('data-cf2-open-settings="recovery"', PARTIAL)
        self.assertIn('id="ma-tpl-root"', PARTIAL)
        self.assertIn("data-cf2-settings-panel=\"recovery\"", PARTIAL)
        self.assertIn('"trigger-templates": "recovery"', SETTINGS_JS)


class ShellInvariant(unittest.TestCase):
    def test_v2_merchant_shell_assets(self) -> None:
        self.assertIn('data-cf-ui="v2"', V2_HTML)
        self.assertIn("merchant_ui_v2_app.js", V2_HTML)
        self.assertNotIn("merchant_app.js", V2_HTML)


class ThresholdTerminology(unittest.TestCase):
    def test_no_merchant_facing_عتبة_in_v2_settings(self) -> None:
        self.assertNotIn("العتبة", PARTIAL)
        self.assertNotIn("عتبة", SETTINGS_JS)
        self.assertNotIn("عتبة", VIP_JS)
        self.assertIn("الحد الأدنى لقيمة السلة", PARTIAL)
        self.assertIn("الحد الأدنى لقيمة السلة", VIP_JS)


class AccountContext(unittest.TestCase):
    def test_account_drawer_has_current_store(self) -> None:
        self.assertIn('id="cf2-account-store-name"', V2_HTML)
        self.assertIn("المتجر الحالي", V2_HTML)
        self.assertIn("refreshAccountDrawer", APP_JS)
        self.assertIn("/api/merchant/session-identity", APP_JS)
        self.assertIn("/api/merchant/subscription", APP_JS)
        self.assertIn('data-cf2-util="settings-store"', V2_HTML)
        self.assertIn('data-cf2-util="settings-plan"', V2_HTML)
        self.assertNotIn("الملف والباقة", V2_HTML)


class ProductsUnchanged(unittest.TestCase):
    def test_products_ctx_null(self) -> None:
        self.assertIn("products: null", APP_JS)


if __name__ == "__main__":
    unittest.main()
