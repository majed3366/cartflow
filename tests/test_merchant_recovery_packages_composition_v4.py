# -*- coding: utf-8 -*-
"""Merchant Recovery Policy Composition + Packages Experience V4 gates."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RecoveryPolicyCompositionV4Tests(unittest.TestCase):
    def test_canonical_seven_reasons_in_dashboard_keys(self) -> None:
        from services.trigger_templates_dashboard import TRIGGER_TEMPLATE_PAGE_KEYS

        self.assertEqual(
            list(TRIGGER_TEMPLATE_PAGE_KEYS),
            [
                "price",
                "shipping",
                "warranty",
                "thinking",
                "quality",
                "delivery",
                "other",
            ],
        )
        self.assertEqual(len(TRIGGER_TEMPLATE_PAGE_KEYS), 7)

    def test_v2_compose_marker_and_one_reason_picker(self) -> None:
        html = (ROOT / "templates/partials/merchant_settings_canonical_v1.html").read_text(
            encoding="utf-8"
        )
        js = (ROOT / "static/merchant_trigger_templates.js").read_text(encoding="utf-8")
        self.assertIn('data-cf2-rec-compose="v4"', html)
        self.assertIn("cf2-rec-summary", html)
        self.assertIn("reasonPickerHtml", js)
        self.assertIn("selectReasonCard", js)
        self.assertIn("isV2RecoveryCompose", js)
        self.assertIn("cf2-rec-flow", js)
        # Long theory intro suppressed in V2 path
        self.assertIn("if (isV2RecoveryCompose())", js)
        self.assertIn('return \'<div id="ma-tpl-meta-policy-banner"', js)

    def test_no_merchant_v1_recovery_handoff(self) -> None:
        html = (ROOT / "templates/merchant_app_v2.html").read_text(encoding="utf-8")
        settings = (ROOT / "templates/partials/merchant_settings_canonical_v1.html").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("cf_ui=v1", html)
        self.assertNotIn("cf_ui=v1", settings)

    def test_packages_account_destination(self) -> None:
        html = (ROOT / "templates/merchant_app_v2.html").read_text(encoding="utf-8")
        app = (ROOT / "static/merchant_ui_v2_app.js").read_text(encoding="utf-8")
        pkg = (ROOT / "static/merchant_ui_v2_packages.js").read_text(encoding="utf-8")
        self.assertIn('data-cf2-page="packages"', html)
        self.assertIn('data-cf2-util="packages"', html)
        self.assertIn("merchant_ui_v2_packages.js", html)
        self.assertIn('h === "packages"', app)
        self.assertIn("/api/merchant/plans-catalog", pkg)
        self.assertIn("upgrade_available", pkg)
        self.assertIn("billing_available", pkg)
        # No fake checkout CTA
        self.assertNotRegex(pkg, re.compile(r"ادفع الآن|اشترِ الآن|checkout", re.I))

    def test_catalog_authoritative_three_plans(self) -> None:
        from services.merchant_plans_catalog_v1 import build_merchant_plans_catalog

        cat = build_merchant_plans_catalog()
        self.assertTrue(cat["read_only"])
        self.assertFalse(cat["billing_available"])
        self.assertFalse(cat["upgrade_available"])
        ids = [p["plan_id"] for p in cat["plans"]]
        self.assertEqual(ids, ["starter", "growth", "pro"])

    def test_products_untouched_marker(self) -> None:
        app = (ROOT / "static/merchant_ui_v2_app.js").read_text(encoding="utf-8")
        self.assertIn('{ id: "products", label: "المنتجات", slice: false }', app)


if __name__ == "__main__":
    unittest.main()
