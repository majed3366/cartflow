# -*- coding: utf-8 -*-
"""Merchant Recovery + Packages Visual Identity Assimilation V5 gates."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RecoveryPackagesVisualIdentityV5Tests(unittest.TestCase):
    def test_stage_continuum_uses_cartflow_co_not_wait_labels(self) -> None:
        js = (ROOT / "static/merchant_trigger_templates.js").read_text(encoding="utf-8")
        css = (ROOT / "static/merchant_ui_v2_settings.css").read_text(encoding="utf-8")
        self.assertIn("cf2-rec-continuum", js)
        self.assertIn("cf2-rec-stage-link", js)
        self.assertIn("cf2-co--recovery", js)
        self.assertIn('data-cf2-stage-state="', js)
        self.assertNotIn('v2 ? "انتظار"', js)
        self.assertIn("cf2-rec-continuum", css)
        self.assertIn("cf2-rec-stage-link", css)
        self.assertIn(".cf2-rec-stage-wait", css)

    def test_message_timing_restore_composition(self) -> None:
        js = (ROOT / "static/merchant_trigger_templates.js").read_text(encoding="utf-8")
        css = (ROOT / "static/merchant_ui_v2_settings.css").read_text(encoding="utf-8")
        self.assertIn("cf2-rec-msg__surface", js)
        self.assertIn("cf2-rec-msg__ta", js)
        self.assertIn("cf2-rec-delay__ctl", js)
        self.assertIn("cf2-rec-restore", js)
        self.assertIn("data-ma-tpl-restore-timing", js)
        self.assertIn("data-ma-tpl-delay", js)
        self.assertIn("data-ma-tpl-unit", js)
        self.assertIn("data-ma-tpl-msg", js)
        self.assertIn("cf2-rec-msg__surface", css)
        self.assertIn("cf2-rec-delay__ctl", css)
        self.assertIn("cf2-rec-restore", css)

    def test_packages_full_width_board_and_joints(self) -> None:
        pkg = (ROOT / "static/merchant_ui_v2_packages.js").read_text(encoding="utf-8")
        css = (ROOT / "static/merchant_ui_v2_settings.css").read_text(encoding="utf-8")
        self.assertIn('data-cf2-packages-compose="v5"', pkg)
        self.assertIn("cf2-packages__board", pkg)
        self.assertIn("cf2-plan-card__joint", pkg)
        self.assertIn("data-cf2-plan-mass", pkg)
        self.assertIn("cf2-plan-card__price-note", pkg)
        self.assertNotRegex(pkg, re.compile(r"ادفع الآن|اشترِ الآن|checkout", re.I))
        self.assertIn("max-width: none", css)
        self.assertIn("cf2-packages__board", css)
        self.assertIn("cf2-plan-card__joint", css)

    def test_v4_functional_contracts_retained(self) -> None:
        from services.trigger_templates_dashboard import TRIGGER_TEMPLATE_PAGE_KEYS
        from services.merchant_plans_catalog_v1 import build_merchant_plans_catalog

        self.assertEqual(len(TRIGGER_TEMPLATE_PAGE_KEYS), 7)
        html = (ROOT / "templates/partials/merchant_settings_canonical_v1.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('data-cf2-rec-compose="v4"', html)
        app = (ROOT / "templates/merchant_app_v2.html").read_text(encoding="utf-8")
        self.assertNotIn("cf_ui=v1", app)
        self.assertIn("recv5", app)
        self.assertIn("pkgv5", app)
        cat = build_merchant_plans_catalog()
        self.assertEqual([p["plan_id"] for p in cat["plans"]], ["starter", "growth", "pro"])
        self.assertFalse(cat["billing_available"])
        self.assertFalse(cat["upgrade_available"])

    def test_products_untouched(self) -> None:
        app = (ROOT / "static/merchant_ui_v2_app.js").read_text(encoding="utf-8")
        self.assertIn('{ id: "products", label: "المنتجات", slice: false }', app)


if __name__ == "__main__":
    unittest.main()
