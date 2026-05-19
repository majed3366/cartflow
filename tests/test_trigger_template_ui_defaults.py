# -*- coding: utf-8 -*-
"""عرض لوحة قوالب الاسترجاع — افتراضيات المراحل وإصلاح عرض السعر."""

from __future__ import annotations

import json
import unittest

from services.trigger_template_ui_defaults import (
    DASHBOARD_STAGE_TEXTS,
    enrich_reason_entry_for_dashboard,
    stage_texts_are_distinct,
)
from services.trigger_templates_dashboard import build_trigger_templates_get_payload


class TriggerTemplateUiDefaultsTests(unittest.TestCase):
    def test_price_quality_shipping_stages_are_distinct(self) -> None:
        for key in ("price", "quality", "shipping"):
            self.assertTrue(
                stage_texts_are_distinct(key),
                msg=f"duplicate stage text for {key}",
            )

    def test_enrich_price_repairs_offer_in_legacy_message_field(self) -> None:
        offer = DASHBOARD_STAGE_TEXTS["price"][1]
        ent = {
            "enabled": True,
            "message": offer,
            "message_count": 3,
            "messages": [
                {"delay": 1, "unit": "minute", "text": ""},
                {"delay": 2, "unit": "minute", "text": offer},
                {
                    "delay": 3,
                    "unit": "hour",
                    "text": DASHBOARD_STAGE_TEXTS["price"][2],
                },
            ],
        }
        out = enrich_reason_entry_for_dashboard("price", ent)
        self.assertEqual(out["message"], DASHBOARD_STAGE_TEXTS["price"][0])
        self.assertEqual(out["messages"][0]["text"], DASHBOARD_STAGE_TEXTS["price"][0])
        self.assertEqual(out["messages"][1]["text"], offer)

    def test_enrich_does_not_replace_custom_price_message(self) -> None:
        custom = "نص مخصص للتاجر لا يشبه الافتراضي"
        ent = {
            "enabled": True,
            "message": custom,
            "message_count": 2,
            "messages": [
                {"delay": 1, "unit": "minute", "text": custom},
                {"delay": 2, "unit": "minute", "text": "مرحلة ثانية مخصصة"},
            ],
        }
        out = enrich_reason_entry_for_dashboard("price", ent)
        self.assertEqual(out["message"], custom)
        self.assertEqual(out["messages"][0]["text"], custom)

    def test_get_payload_price_row_after_corrupt_store(self) -> None:
        offer = DASHBOARD_STAGE_TEXTS["price"][1]

        class _Mini:
            reason_templates_json = json.dumps(
                {
                    "price": {
                        "enabled": True,
                        "message": offer,
                        "message_count": 3,
                        "messages": [
                            {"delay": 1, "unit": "minute", "text": ""},
                            {"delay": 2, "unit": "minute", "text": offer},
                        ],
                    }
                }
            )

        rows = build_trigger_templates_get_payload(_Mini())["reason_rows"]
        price = next(r for r in rows if r["key"] == "price")
        self.assertEqual(price["message"], DASHBOARD_STAGE_TEXTS["price"][0])
        self.assertEqual(
            price["messages"][0]["text"],
            DASHBOARD_STAGE_TEXTS["price"][0],
        )
        self.assertEqual(
            price["messages"][1]["text"],
            offer,
        )


if __name__ == "__main__":
    unittest.main()
