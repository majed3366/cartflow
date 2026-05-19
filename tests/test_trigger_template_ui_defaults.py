# -*- coding: utf-8 -*-
"""عرض لوحة قوالب الاسترجاع — افتراضيات المراحل وإصلاح مرحلة 1."""

from __future__ import annotations

import json
import unittest

from services.trigger_template_ui_defaults import (
    DASHBOARD_STAGE_DELAYS,
    DASHBOARD_STAGE_TEXTS,
    enrich_reason_entry_for_dashboard,
    format_delay_for_dashboard_ui,
    is_loadtest_placeholder,
    stage_default_delay_ui,
    stage_default_text,
    stage_texts_are_distinct,
)
from services.trigger_templates_dashboard import build_trigger_templates_get_payload

_ALL_REASONS = ("price", "quality", "shipping", "delivery", "warranty", "other")


class TriggerTemplateUiDefaultsTests(unittest.TestCase):
    def test_all_reasons_stage_texts_distinct(self) -> None:
        for key in _ALL_REASONS:
            self.assertTrue(stage_texts_are_distinct(key), msg=key)
            self.assertNotEqual(
                DASHBOARD_STAGE_TEXTS[key][0],
                DASHBOARD_STAGE_TEXTS[key][1],
                msg=f"stage1==stage2 for {key}",
            )

    def test_recommended_delays_per_reason(self) -> None:
        self.assertEqual(stage_default_delay_ui("price", 0), (60.0, "minute"))
        self.assertEqual(stage_default_delay_ui("price", 1), (5.0, "hour"))
        self.assertEqual(stage_default_delay_ui("price", 2), (5.0, "day"))
        self.assertEqual(stage_default_delay_ui("shipping", 0), (30.0, "minute"))
        self.assertEqual(stage_default_delay_ui("shipping", 2), (2.0, "day"))
        self.assertEqual(stage_default_delay_ui("quality", 0), (90.0, "minute"))
        self.assertEqual(stage_default_delay_ui("warranty", 0), (2.0, "hour"))
        self.assertEqual(stage_default_delay_ui("delivery", 1), (6.0, "hour"))
        self.assertEqual(stage_default_delay_ui("other", 2), (5.0, "day"))
        for key in _ALL_REASONS:
            row = DASHBOARD_STAGE_DELAYS[key]
            self.assertEqual(len(row), 3)
            self.assertNotEqual(row[0], row[1], msg=key)

    def test_empty_store_price_stage1_is_60_minutes(self) -> None:
        class _Mini:
            reason_templates_json = None

        rows = build_trigger_templates_get_payload(_Mini())["reason_rows"]
        price = next(r for r in rows if r["key"] == "price")
        self.assertEqual(price["delay_value"], 60.0)
        self.assertEqual(price["delay_unit"], "minute")
        self.assertEqual(price["messages"][0]["delay"], 60.0)
        self.assertEqual(
            format_delay_for_dashboard_ui(60.0, "minute"),
            "60 دقيقة",
        )

    def test_legacy_four_minutes_upgrades_when_text_is_defaultish(self) -> None:
        offer = DASHBOARD_STAGE_TEXTS["price"][1]
        ent = {
            "enabled": True,
            "message": offer,
            "message_count": 2,
            "messages": [
                {"delay": 4, "unit": "minute", "text": offer},
                {"delay": 5, "unit": "hour", "text": offer},
            ],
        }
        out = enrich_reason_entry_for_dashboard("price", ent)
        self.assertEqual(out["messages"][0]["delay"], 60.0)
        self.assertEqual(out["messages"][0]["unit"], "minute")
        self.assertEqual(out["messages"][1]["delay"], 5.0)
        self.assertEqual(out["messages"][1]["unit"], "hour")

    def test_legacy_four_minutes_kept_when_text_is_custom(self) -> None:
        custom = "نص مخصص للتاجر — ليس افتراضياً"
        ent = {
            "enabled": True,
            "message": custom,
            "message_count": 1,
            "messages": [{"delay": 4, "unit": "minute", "text": custom}],
        }
        out = enrich_reason_entry_for_dashboard("price", ent)
        self.assertEqual(out["messages"][0]["delay"], 4.0)

    def test_enrich_applies_recommended_delay_only_for_new_slots(self) -> None:
        ent = {
            "enabled": True,
            "message": "",
            "message_count": 2,
            "messages": [{"delay": 45, "unit": "minute", "text": "مخصص"}],
        }
        out = enrich_reason_entry_for_dashboard("price", ent)
        self.assertEqual(out["messages"][0]["delay"], 45.0)
        self.assertEqual(out["messages"][0]["unit"], "minute")
        self.assertEqual(out["messages"][1]["delay"], 5.0)
        self.assertEqual(out["messages"][1]["unit"], "hour")

    def test_shipping_delivery_stage3_defaults(self) -> None:
        self.assertEqual(
            stage_default_text("shipping", 2),
            "إذا حاب، نوضح لك آخر تحديثات الشحن أو الخيارات المتاحة بسرعة 👍",
        )
        self.assertEqual(
            stage_default_text("delivery", 1),
            "إذا فيه خيار أسرع أو أقرب لموعدك، نوضح لك المتاح باختصار.",
        )
        self.assertEqual(
            stage_default_text("delivery", 2),
            "إذا حاب، نوضح لك آخر موعد متوقع أو أي تحديث يفيد قرارك 👍",
        )

    def test_stage1_reassurance_copy_per_reason(self) -> None:
        expected = {
            "price": "نعرف إن السعر قرار مهم 👍 إذا عندك استفسار عن السعر أو الدفع نوضحه بسرعة.",
            "quality": "نحب نطمنك 👍 إذا عندك أي سؤال عن جودة المنتج أو تفاصيله نوضحها لك باختصار.",
            "shipping": "نوضح لك خيارات الشحن والتكلفة بكل اختصار 👍",
            "delivery": "نقدر نوضح لك مدة التوصيل المتوقعة قبل ما تكمل الطلب 👍",
            "warranty": "نوضح لك تفاصيل الضمان أو الاستبدال بكل بساطة 👍",
            "other": "نقدر نساعدك بأي استفسار قبل إكمال الطلب 👍",
        }
        for key, text in expected.items():
            self.assertEqual(stage_default_text(key, 0), text)

    def test_is_loadtest_placeholder(self) -> None:
        self.assertTrue(is_loadtest_placeholder("LOADTEST_STORE_020_quality"))
        self.assertTrue(is_loadtest_placeholder("prefix LOADTEST_STORE_003_delivery suffix"))
        self.assertFalse(is_loadtest_placeholder("نص مخصص للتاجر"))

    def test_enrich_strips_loadtest_from_stage1_and_message(self) -> None:
        marker = "LOADTEST_STORE_020_quality"
        ent = {
            "enabled": True,
            "message": marker,
            "message_count": 2,
            "messages": [
                {"delay": 1, "unit": "minute", "text": marker},
                {
                    "delay": 2,
                    "unit": "minute",
                    "text": DASHBOARD_STAGE_TEXTS["quality"][1],
                },
            ],
        }
        out = enrich_reason_entry_for_dashboard("quality", ent)
        self.assertEqual(out["message"], DASHBOARD_STAGE_TEXTS["quality"][0])
        self.assertEqual(out["messages"][0]["text"], DASHBOARD_STAGE_TEXTS["quality"][0])
        self.assertEqual(out["messages"][1]["text"], DASHBOARD_STAGE_TEXTS["quality"][1])

    def test_enrich_loadtest_stage2_only_leaves_stage2_default(self) -> None:
        marker = "LOADTEST_STORE_007_delivery"
        ent = {
            "enabled": True,
            "message": DASHBOARD_STAGE_TEXTS["delivery"][0],
            "message_count": 3,
            "messages": [
                {
                    "delay": 1,
                    "unit": "minute",
                    "text": DASHBOARD_STAGE_TEXTS["delivery"][0],
                },
                {"delay": 2, "unit": "minute", "text": marker},
                {
                    "delay": 3,
                    "unit": "hour",
                    "text": DASHBOARD_STAGE_TEXTS["delivery"][2],
                },
            ],
        }
        out = enrich_reason_entry_for_dashboard("delivery", ent)
        self.assertEqual(out["messages"][0]["text"], DASHBOARD_STAGE_TEXTS["delivery"][0])
        self.assertEqual(out["messages"][1]["text"], DASHBOARD_STAGE_TEXTS["delivery"][1])
        self.assertEqual(out["messages"][2]["text"], DASHBOARD_STAGE_TEXTS["delivery"][2])

    def test_enrich_repairs_offer_in_stage1_for_price(self) -> None:
        offer = DASHBOARD_STAGE_TEXTS["price"][1]
        ent = {
            "enabled": True,
            "message": offer,
            "message_count": 3,
            "messages": [
                {"delay": 1, "unit": "minute", "text": ""},
                {"delay": 2, "unit": "minute", "text": offer},
            ],
        }
        out = enrich_reason_entry_for_dashboard("price", ent)
        self.assertEqual(out["message"], DASHBOARD_STAGE_TEXTS["price"][0])
        self.assertEqual(out["messages"][0]["text"], DASHBOARD_STAGE_TEXTS["price"][0])

    def test_enrich_repairs_stage2_text_in_stage1_for_shipping(self) -> None:
        ent = {
            "enabled": True,
            "message": DASHBOARD_STAGE_TEXTS["shipping"][1],
            "message_count": 2,
            "messages": [
                {
                    "delay": 1,
                    "unit": "minute",
                    "text": DASHBOARD_STAGE_TEXTS["shipping"][1],
                },
                {
                    "delay": 2,
                    "unit": "minute",
                    "text": DASHBOARD_STAGE_TEXTS["shipping"][1],
                },
            ],
        }
        out = enrich_reason_entry_for_dashboard("shipping", ent)
        self.assertEqual(out["messages"][0]["text"], DASHBOARD_STAGE_TEXTS["shipping"][0])
        self.assertEqual(out["messages"][1]["text"], DASHBOARD_STAGE_TEXTS["shipping"][1])

    def test_enrich_does_not_replace_custom_message(self) -> None:
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

    def test_get_payload_all_reasons_after_loadtest_store_json(self) -> None:
        templates = {}
        for i, tag in enumerate(_ALL_REASONS):
            templates[tag] = {
                "enabled": True,
                "message": f"LOADTEST_STORE_020_{tag}",
                "message_count": 1 + (i % 2),
            }

        class _Mini:
            reason_templates_json = json.dumps(templates)

        rows = build_trigger_templates_get_payload(_Mini())["reason_rows"]
        by_key = {r["key"]: r for r in rows}
        for key in _ALL_REASONS:
            row = by_key[key]
            self.assertEqual(row["message"], DASHBOARD_STAGE_TEXTS[key][0])
            if row.get("messages"):
                self.assertEqual(
                    row["messages"][0]["text"],
                    DASHBOARD_STAGE_TEXTS[key][0],
                )
            self.assertNotIn("LOADTEST", row["message"])

    def test_enrich_does_not_throw_on_boolean_messages(self) -> None:
        ent = {
            "enabled": True,
            "message_count": 2,
            "messages": True,
            "message": "نص محفوظ",
        }
        out = enrich_reason_entry_for_dashboard("price", ent)
        self.assertEqual(out["message_count"], 2)
        self.assertIsInstance(out.get("messages"), list)
        self.assertEqual(len(out["messages"]), 2)


if __name__ == "__main__":
    unittest.main()
