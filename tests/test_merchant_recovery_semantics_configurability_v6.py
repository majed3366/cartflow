# -*- coding: utf-8 -*-
"""Recovery Policy Semantics & Configurability V6 gates."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RecoverySemanticsConfigurabilityV6Tests(unittest.TestCase):
    def test_timing_copy_is_absolute_from_abandon(self) -> None:
        js = (ROOT / "static/merchant_trigger_templates.js").read_text(encoding="utf-8")
        html = (ROOT / "templates/partials/merchant_settings_canonical_v1.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("موعد الإرسال بعد ترك السلة", js)
        self.assertIn("من ترك السلة", js)
        self.assertIn("paintFirstMessageTimingSummary", js)
        self.assertIn("إعدادات احتياطية للمسارات بدون قالب سبب", html)
        self.assertIn("حد الانتظار الاحتياطي", html)
        self.assertNotIn("مدة الانتظار قبل أول رسالة", html)
        self.assertNotIn("أول رسالة بعد", html)

    def test_stage_count_cartflow_control(self) -> None:
        js = (ROOT / "static/merchant_trigger_templates.js").read_text(encoding="utf-8")
        css = (ROOT / "static/merchant_ui_v2_settings.css").read_text(encoding="utf-8")
        self.assertIn("cf2-rec-stage-count__opt", js)
        self.assertIn("data-cf2-stage-count", js)
        self.assertIn("cf2-rec-stage-count__native", js)
        self.assertIn("cf2-rec-stage-count__ctl", css)
        # Visible native select for V2 stage count must remain clipped/hidden
        self.assertIn("cf2-rec-stage-count__native", css)

    def test_reason_contract_still_seven_keys_no_add_ui(self) -> None:
        from services.trigger_templates_dashboard import TRIGGER_TEMPLATE_PAGE_KEYS

        self.assertEqual(len(TRIGGER_TEMPLATE_PAGE_KEYS), 7)
        html = (ROOT / "templates/partials/merchant_settings_canonical_v1.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("لا يمكن إضافة أو حذف أسباب جديدة", html)
        js = (ROOT / "static/merchant_trigger_templates.js").read_text(encoding="utf-8")
        self.assertNotRegex(js, re.compile(r"إضافة سبب|addReason|createReason", re.I))

    def test_internal_dev_copy_removed(self) -> None:
        html = (ROOT / "templates/partials/merchant_settings_canonical_v1.html").read_text(
            encoding="utf-8"
        )
        app = (ROOT / "templates/merchant_app_v2.html").read_text(encoding="utf-8")
        wa = (ROOT / "static/merchant_whatsapp_settings.js").read_text(encoding="utf-8")
        self.assertNotIn("لا تفتح واجهة قديمة", html)
        self.assertNotIn("Merchant UI V2", html)
        self.assertNotIn("شريحة V2", app)
        self.assertNotIn("CartFlow Managed للتشغيل التجريبي", wa)

    def test_v5_identity_markers_preserved(self) -> None:
        js = (ROOT / "static/merchant_trigger_templates.js").read_text(encoding="utf-8")
        pkg = (ROOT / "static/merchant_ui_v2_packages.js").read_text(encoding="utf-8")
        self.assertIn("cf2-rec-continuum", js)
        self.assertIn("cf2-rec-msg__surface", js)
        self.assertIn("cf2-rec-restore", js)
        self.assertIn('data-cf2-packages-compose="v5"', pkg)

    def test_products_untouched_nav(self) -> None:
        app = (ROOT / "static/merchant_ui_v2_app.js").read_text(encoding="utf-8")
        self.assertIn('{ id: "products", label: "المنتجات", slice: false }', app)


if __name__ == "__main__":
    unittest.main()
