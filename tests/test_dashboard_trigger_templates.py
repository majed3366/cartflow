# -*- coding: utf-8 -*-
"""GET/POST /api/dashboard/trigger-templates — قوالب سبب التردد فقط (استعلام خفيف)."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from main import app


class DashboardTriggerTemplatesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_get_returns_reason_rows_ordered(self) -> None:
        r = self.client.get("/api/dashboard/trigger-templates")
        self.assertEqual(r.status_code, 200, r.text[:400])
        p = r.json()
        self.assertTrue(p.get("ok"), msg=p)
        rows = p.get("reason_rows") or []
        self.assertEqual(len(rows), 6)
        keys = [x.get("key") for x in rows]
        self.assertEqual(
            keys,
            ["price", "quality", "shipping", "delivery", "warranty", "other"],
        )
        self.assertEqual(
            (p.get("section_title_ar") or "").strip(), "قوالب حسب سبب التردد"
        )

    def test_post_merges_one_reason_then_get_roundtrip(self) -> None:
        g = self.client.get("/api/dashboard/trigger-templates")
        self.assertEqual(g.status_code, 200)

        rid = None
        for row in g.json().get("reason_rows") or []:
            rid = row.get("key")
            break
        self.assertIsNotNone(rid)

        body = {
            "reason_templates": {
                str(rid): {
                    "enabled": True,
                    "message": "اختبار وحدة قوالب اللوحة",
                    "message_count": 1,
                    "messages": [
                        {"delay": 3, "unit": "minute", "text": "اختبار وحدة قوالب اللوحة"}
                    ],
                }
            }
        }
        rp = self.client.post(
            "/api/dashboard/trigger-templates",
            json=body,
        )
        self.assertEqual(rp.status_code, 200, rp.text[:400])
        out = rp.json()
        self.assertTrue(out.get("ok"), msg=out)
        self.assertTrue(out.get("save_ack"), msg=out)
        self.assertLess(len(rp.content), 8000, msg="POST should stay lightweight")
        g2 = self.client.get("/api/dashboard/trigger-templates")
        self.assertEqual(g2.status_code, 200)
        found = False
        for row in g2.json().get("reason_rows") or []:
            if row.get("key") != rid:
                continue
            found = True
            self.assertIn("اختبار", row.get("message") or "")
        self.assertTrue(found, msg=g2.json().get("reason_rows"))

    def test_post_save_five_minutes_persists_on_get(self) -> None:
        from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS

        stage1 = DASHBOARD_STAGE_TEXTS["price"][0]
        body = {
            "reason_templates": {
                "price": {
                    "enabled": True,
                    "message": stage1,
                    "message_count": 1,
                    "messages": [{"delay": 5, "unit": "minute", "text": stage1}],
                }
            },
            "selected_stage": 0,
        }
        rp = self.client.post("/api/dashboard/trigger-templates", json=body)
        self.assertEqual(rp.status_code, 200, rp.text[:400])
        self.assertTrue(rp.json().get("save_ack"))
        g = self.client.get("/api/dashboard/trigger-templates")
        price = next(r for r in g.json().get("reason_rows") or [] if r.get("key") == "price")
        self.assertEqual(price.get("delay_value"), 5.0)
        self.assertEqual(price["messages"][0]["delay"], 5.0)

    def test_post_warranty_and_other_timing_persist_on_get(self) -> None:
        from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS

        cases = (
            ("warranty", 7, "minute"),
            ("other", 11, "minute"),
        )
        for reason, delay, unit in cases:
            stage1 = DASHBOARD_STAGE_TEXTS[reason][0]
            body = {
                "reason_templates": {
                    reason: {
                        "enabled": True,
                        "message": stage1,
                        "message_count": 1,
                        "messages": [
                            {"delay": delay, "unit": unit, "text": stage1}
                        ],
                    }
                },
                "selected_stage": 0,
            }
            rp = self.client.post(
                "/api/dashboard/trigger-templates",
                json=body,
            )
            self.assertEqual(rp.status_code, 200, rp.text[:400])
            ack_row = next(
                r
                for r in rp.json().get("reason_rows") or []
                if r.get("key") == reason
            )
            self.assertEqual(ack_row.get("delay_value"), float(delay))
            g = self.client.get("/api/dashboard/trigger-templates")
            row = next(
                r for r in g.json().get("reason_rows") or [] if r.get("key") == reason
            )
            self.assertEqual(row.get("delay_value"), float(delay))
            self.assertEqual(row["messages"][0]["delay"], float(delay))


class TriggerTemplatesDashboardServiceTests(unittest.TestCase):
    def test_build_payload_for_empty_namespace(self) -> None:
        from services.trigger_templates_dashboard import build_trigger_templates_get_payload

        class _Mini:
            reason_templates_json = None

        p = build_trigger_templates_get_payload(_Mini())
        self.assertEqual(len(p["reason_rows"]), 6)
        sample = {r["key"]: r["message_count"] for r in p["reason_rows"]}
        self.assertEqual(sample["price"], 1)

    def test_build_payload_survives_non_list_messages(self) -> None:
        import json

        from services.trigger_templates_dashboard import build_trigger_templates_get_payload

        class _Mini:
            reason_templates_json = json.dumps(
                {
                    "price": {
                        "enabled": True,
                        "message_count": 2,
                        "messages": True,
                        "message": "نص مخصص",
                    }
                }
            )

        p = build_trigger_templates_get_payload(_Mini())
        self.assertEqual(len(p["reason_rows"]), 6)
        price = next(r for r in p["reason_rows"] if r["key"] == "price")
        self.assertEqual(price["message_count"], 2)
        self.assertIsInstance(price.get("messages"), list)

    def test_build_fallback_when_store_missing(self) -> None:
        from services.trigger_templates_dashboard import (
            build_fallback_trigger_templates_payload,
            build_trigger_templates_get_payload,
        )

        fb = build_fallback_trigger_templates_payload()
        self.assertEqual(len(fb["reason_rows"]), 6)
        self.assertTrue(fb.get("display_fallback"))

        none_p = build_trigger_templates_get_payload(None)
        self.assertEqual(len(none_p["reason_rows"]), 6)

    def test_enrich_roundtrip_keeps_custom_five_minute_price_stage1(self) -> None:
        from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS
        from services.trigger_templates_dashboard import build_trigger_templates_get_payload

        stage1 = DASHBOARD_STAGE_TEXTS["price"][0]
        stored = {
            "price": {
                "enabled": True,
                "message": stage1,
                "message_count": 1,
                "messages": [{"delay": 5, "unit": "minute", "text": stage1}],
            }
        }

        class _Mini:
            reason_templates_json = __import__("json").dumps(stored)

        price = next(
            r
            for r in build_trigger_templates_get_payload(_Mini())["reason_rows"]
            if r["key"] == "price"
        )
        self.assertEqual(price["delay_value"], 5.0)
        self.assertEqual(price["messages"][0]["delay"], 5.0)

    def test_build_save_ack_returns_patch_rows_only(self) -> None:
        import json

        from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS
        from services.trigger_templates_dashboard import build_trigger_templates_save_ack

        stage1 = DASHBOARD_STAGE_TEXTS["price"][0]

        class _Mini:
            reason_templates_json = json.dumps(
                {
                    "price": {
                        "enabled": True,
                        "message": stage1,
                        "message_count": 1,
                        "messages": [{"delay": 5, "unit": "minute", "text": stage1}],
                    }
                }
            )

        ack = build_trigger_templates_save_ack(
            saved_reason_keys=["price"], store_row=_Mini()
        )
        self.assertTrue(ack.get("save_ack"))
        self.assertEqual(ack.get("saved_reason_keys"), ["price"])
        self.assertEqual(len(ack.get("reason_rows") or []), 1)
        self.assertEqual(ack["reason_rows"][0]["delay_value"], 5.0)

