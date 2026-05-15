# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from extensions import db
from fastapi.testclient import TestClient

from main import app


class MerchantWidgetPanelApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def test_post_merchant_widget_settings_returns_panel(self) -> None:
        db.create_all()
        r = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={
                "widget_name": "ودجيت الاختبار",
                "widget_primary_color": "#112233",
                "cartflow_widget_enabled": True,
                "exit_intent_template_mode": "preset",
                "exit_intent_template_tone": "friendly",
                "widget_trigger_config": {
                    "exit_intent_enabled": False,
                    "widget_phone_capture_mode": "immediate",
                    "widget_brand_line_ar": "سطر العلامة",
                },
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"), j)
        panel = j.get("merchant_widget_panel")
        self.assertIsInstance(panel, dict)
        self.assertEqual(panel.get("widget_name"), "ودجيت الاختبار")
        self.assertEqual(panel.get("widget_primary_color"), "#112233")
        self.assertFalse(panel["trigger"]["exit_intent_enabled"])
        self.assertEqual(panel["trigger"]["widget_phone_capture_mode"], "immediate")
        self.assertEqual(panel["trigger"]["widget_brand_line_ar"], "سطر العلامة")

    def test_post_reason_labels_merge(self) -> None:
        db.create_all()
        r = self.client.post(
            "/api/dashboard/merchant-widget-settings",
            json={
                "reason_templates": {
                    "price": {
                        "enabled": False,
                        "widget_reason_label_ar": "السعر غير مناسب",
                    },
                },
                "widget_trigger_config": {
                    "reason_display_order": [
                        "other",
                        "price",
                        "shipping",
                        "delivery",
                        "quality",
                        "warranty",
                        "thinking",
                    ],
                },
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        panel = r.json().get("merchant_widget_panel") or {}
        rows = panel.get("reason_rows") or []
        keys = [x.get("key") for x in rows]
        self.assertEqual(keys[0], "other")
        price_row = next(x for x in rows if x.get("key") == "price")
        self.assertFalse(price_row.get("enabled"))
        self.assertIn("غير مناسب", str(price_row.get("label_ar") or ""))


if __name__ == "__main__":
    unittest.main()
