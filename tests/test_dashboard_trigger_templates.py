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
        found = False
        for row in out.get("reason_rows") or []:
            if row.get("key") != rid:
                continue
            found = True
            self.assertIn("اختبار", row.get("message") or "")
        self.assertTrue(found, msg=out.get("reason_rows"))


class TriggerTemplatesDashboardServiceTests(unittest.TestCase):
    def test_build_payload_for_empty_namespace(self) -> None:
        from services.trigger_templates_dashboard import build_trigger_templates_get_payload

        class _Mini:
            reason_templates_json = None

        p = build_trigger_templates_get_payload(_Mini())
        self.assertEqual(len(p["reason_rows"]), 6)
        sample = {r["key"]: r["message_count"] for r in p["reason_rows"]}
        self.assertEqual(sample["price"], 1)

