# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import Store


class TemplateTruthDebugTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_template_truth_endpoint_fields(self) -> None:
        db.create_all()
        row = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
        if row is None:
            row = Store(zid_store_id="demo", recovery_attempts=1)
            db.session.add(row)
            db.session.commit()
        prev = getattr(row, "reason_templates_json", None)
        row.reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message_count": 2,
                    "messages": [
                        {"delay": 1, "unit": "minute", "text": "m1"},
                        {"delay": 2, "unit": "minute", "text": "m2"},
                    ],
                }
            }
        )
        db.session.commit()
        try:
            r = self.client.get("/dev/template-truth?store_slug=demo&reason=price")
            self.assertEqual(200, r.status_code, r.text)
            body = r.json()
            self.assertTrue(body.get("ok"), body)
            self.assertTrue(body.get("store_found"), body)
            self.assertEqual("price", body.get("runtime_lookup_key"))
            self.assertTrue(body.get("template_entry_found"), body)
            self.assertEqual("price", body.get("entry_key_found"))
            self.assertGreaterEqual(int(body.get("message_count") or 0), 2)
            self.assertGreaterEqual(int(body.get("materialized_len") or 0), 2)
        finally:
            row2 = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
            if row2 is not None:
                row2.reason_templates_json = prev
                db.session.commit()


if __name__ == "__main__":
    unittest.main()

