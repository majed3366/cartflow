# -*- coding: utf-8 -*-
"""GET/POST /api/dashboard/trigger-templates — قوالب سبب التردد فقط (استعلام خفيف)."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import Store


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

    def test_post_two_message_price_persists_reason_templates_json(self) -> None:
        import json

        from services.store_reason_templates import parse_reason_templates_column

        body = {
            "store_slug": "demo",
            "reason_templates": {
                "price": {
                    "enabled": True,
                    "message": "رسالة أولى",
                    "message_count": 2,
                    "messages": [
                        {"delay": 3, "unit": "minute", "text": "رسالة أولى"},
                        {"delay": 1, "unit": "hour", "text": "رسالة ثانية"},
                    ],
                }
            },
        }
        db.create_all()
        row = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
        if row is None:
            row = Store(zid_store_id="demo", recovery_attempts=1)
            db.session.add(row)
            db.session.commit()
        prev = getattr(row, "reason_templates_json", None)
        try:
            rp = self.client.post("/api/dashboard/trigger-templates", json=body)
            self.assertEqual(rp.status_code, 200, rp.text[:400])
            db.session.refresh(row)
            parsed = parse_reason_templates_column(row.reason_templates_json)
            self.assertIn("price", parsed)
            self.assertEqual(parsed["price"]["message_count"], 2)
            self.assertEqual(len(parsed["price"]["messages"]), 2)
            truth = self.client.get("/dev/template-truth?store_slug=demo&reason=price")
            self.assertEqual(truth.status_code, 200, truth.text[:400])
            rep = truth.json()
            self.assertIsNotNone(rep.get("raw_reason_templates_json"))
            self.assertTrue(rep.get("template_entry_found"))
            self.assertEqual(rep.get("entry_key_found"), "price")
            self.assertEqual(rep.get("message_count"), 2)
            self.assertEqual(rep.get("messages_array_len"), 2)
            self.assertEqual(rep.get("materialized_len"), 2)
            self.assertGreaterEqual(int(rep.get("slots_len") or 0), 2)
            self.assertIsNone(rep.get("miss_reason"))
        finally:
            row2 = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
            if row2 is not None:
                row2.reason_templates_json = prev
                db.session.commit()

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

    def test_twenty_consecutive_saves_across_reasons(self) -> None:
        from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS

        rotation = ("price", "quality", "warranty", "other", "shipping", "delivery")
        last_delay_by_reason: dict[str, float] = {}
        for i in range(20):
            reason = rotation[i % len(rotation)]
            delay = 3 + (i % 7)
            last_delay_by_reason[reason] = float(delay)
            stage1 = DASHBOARD_STAGE_TEXTS[reason][0]
            body = {
                "reason_templates": {
                    reason: {
                        "enabled": True,
                        "message": stage1,
                        "message_count": 1,
                        "messages": [
                            {"delay": delay, "unit": "minute", "text": stage1}
                        ],
                    }
                },
                "selected_stage": 0,
            }
            rp = self.client.post(
                "/api/dashboard/trigger-templates",
                json=body,
            )
            self.assertEqual(rp.status_code, 200, (i, reason, rp.text[:200]))
            self.assertTrue(rp.json().get("save_ack"), (i, reason, rp.json()))
            ack = next(
                r
                for r in rp.json().get("reason_rows") or []
                if r.get("key") == reason
            )
            self.assertEqual(ack.get("delay_value"), float(delay), (i, reason))
        g = self.client.get("/api/dashboard/trigger-templates")
        self.assertEqual(g.status_code, 200)
        for reason, expected in last_delay_by_reason.items():
            row = next(
                r for r in g.json().get("reason_rows") or [] if r.get("key") == reason
            )
            self.assertEqual(row.get("delay_value"), expected, reason)


class TriggerTemplatesDashboardServiceTests(unittest.TestCase):
    def test_empty_store_rows_marked_defaults_not_stored(self) -> None:
        from services.trigger_templates_dashboard import build_trigger_templates_get_payload

        class _Mini:
            reason_templates_json = None

        rows = build_trigger_templates_get_payload(_Mini())["reason_rows"]
        for row in rows:
            self.assertEqual(row.get("config_source"), "defaults")

    def test_stored_price_row_marked_stored(self) -> None:
        import json

        from services.trigger_templates_dashboard import build_trigger_templates_get_payload

        class _Mini:
            reason_templates_json = json.dumps(
                {
                    "price": {
                        "enabled": True,
                        "message": "محفوظ",
                        "message_count": 2,
                        "messages": [
                            {"delay": 1, "unit": "minute", "text": "أولى"},
                            {"delay": 2, "unit": "hour", "text": "ثانية"},
                        ],
                    }
                }
            )

        price = next(
            r
            for r in build_trigger_templates_get_payload(_Mini())["reason_rows"]
            if r["key"] == "price"
        )
        self.assertEqual(price.get("config_source"), "stored")
        self.assertEqual(price.get("message_count"), 2)
        self.assertEqual(len(price.get("messages") or []), 2)

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


class DashboardTriggerTemplatesCanonicalStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        import json
        import uuid

        self.client = TestClient(app)
        z_latest = f"tpl-latest-{uuid.uuid4().hex[:8]}"
        z_demo = "demo"
        demo_rt = json.dumps(
            {
                "other": {
                    "enabled": True,
                    "message": "demo",
                    "message_count": 1,
                    "messages": [{"delay": 5, "unit": "minute", "text": "demo five"}],
                }
            }
        )
        latest_rt = json.dumps(
            {
                "other": {
                    "enabled": True,
                    "message": "latest",
                    "message_count": 1,
                    "messages": [{"delay": 99, "unit": "minute", "text": "latest"}],
                }
            }
        )
        db.create_all()
        db.session.rollback()
        for row in db.session.query(Store).filter_by(zid_store_id=z_demo).all():
            db.session.delete(row)
        db.session.commit()
        row_demo = Store(zid_store_id=z_demo, reason_templates_json=demo_rt)
        row_latest = Store(zid_store_id=z_latest, reason_templates_json=latest_rt)
        db.session.add(row_demo)
        db.session.add(row_latest)
        db.session.commit()
        self._z_latest = z_latest

    def test_get_uses_demo_not_latest_store_when_slug_demo(self) -> None:
        r = self.client.get("/api/dashboard/trigger-templates?store_slug=demo")
        self.assertEqual(r.status_code, 200, r.text[:400])
        p = r.json()
        self.assertEqual(p.get("store_slug"), "demo")
        other = next(x for x in p.get("reason_rows") or [] if x.get("key") == "other")
        self.assertEqual(other.get("delay_value"), 5.0)

    def test_post_and_debug_align_with_runtime_demo_row(self) -> None:
        from services.trigger_template_ui_defaults import DASHBOARD_STAGE_TEXTS

        stage1 = DASHBOARD_STAGE_TEXTS["other"][0]
        body = {
            "store_slug": "demo",
            "reason_templates": {
                "other": {
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
        dbg = self.client.get("/dev/store-template-debug?store_slug=demo&reason=other")
        self.assertEqual(dbg.status_code, 200)
        rep = dbg.json()
        self.assertTrue(rep.get("dashboard_equals_runtime_row"))
        self.assertEqual(rep.get("dashboard_store_zid"), "demo")
        self.assertEqual(rep.get("runtime_store_zid"), "demo")
        timing = rep.get("runtime_timing_resolution") or {}
        self.assertEqual(timing.get("effective_delay_seconds"), 300)

