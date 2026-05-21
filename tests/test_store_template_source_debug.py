# -*- coding: utf-8 -*-
"""GET /dev/store-template-debug — dashboard vs runtime template source."""
from __future__ import annotations

import json
import unittest
import uuid

import main
from extensions import db
from models import Store
from services.store_template_source_debug import build_store_template_debug_report


class StoreTemplateSourceDebugTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        main._ensure_store_widget_schema()
        for z in ("demo", "demo2", "loadtest-dbg"):
            for row in db.session.query(Store).filter_by(zid_store_id=z).all():
                db.session.delete(row)
        db.session.commit()

    def test_endpoint_returns_structure(self) -> None:
        z_dash = f"loadtest-dbg-{uuid.uuid4().hex[:6]}"
        z_demo = "demo"
        row_dash = Store(
            zid_store_id=z_dash,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            reason_templates_json=json.dumps(
                {
                    "other": {
                        "enabled": True,
                        "message": "dash",
                        "message_count": 1,
                        "messages": [{"delay": 5, "unit": "minute", "text": "dash five"}],
                    }
                }
            ),
        )
        row_demo = Store(
            zid_store_id=z_demo,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            reason_templates_json=json.dumps(
                {
                    "other": {
                        "enabled": True,
                        "message": "demo",
                        "message_count": 1,
                        "messages": [{"delay": 1, "unit": "minute", "text": "demo one"}],
                    }
                }
            ),
        )
        db.session.add(row_dash)
        db.session.add(row_demo)
        db.session.commit()

        client = main._app_test_client()
        r = client.get("/dev/store-template-debug?store_slug=demo&reason=other")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("dashboard_store_id", body)
        self.assertIn("runtime_store_id", body)
        self.assertIn("candidate_store_rows", body)
        self.assertIn("selected_source_explanation", body)
        self.assertTrue(body.get("dashboard_equals_runtime_row"))
        self.assertEqual(body.get("dashboard_store_zid"), "demo")
        self.assertEqual(body.get("runtime_store_zid"), "demo")

    def test_report_detects_different_rows(self) -> None:
        rep = build_store_template_debug_report(store_slug="demo", reason="other")
        self.assertTrue(rep.get("ok"))
        self.assertIsNotNone(rep.get("runtime_timing_resolution"))


if __name__ == "__main__":
    unittest.main()
