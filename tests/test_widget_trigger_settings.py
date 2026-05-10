# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from extensions import db
from fastapi.testclient import TestClient

from main import app
from models import Store
from services.cartflow_widget_trigger_settings import (
    DEFAULT_WIDGET_TRIGGER_CONFIG,
    normalize_widget_trigger_config,
    widget_trigger_config_from_store_row,
)


class WidgetTriggerSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def test_recovery_settings_includes_widget_trigger_config_and_zid(self) -> None:
        db.create_all()
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"), body)
        self.assertIn("widget_trigger_config", body)
        self.assertIn("zid_store_id", body)
        wtc = body["widget_trigger_config"]
        self.assertIsInstance(wtc, dict)
        self.assertEqual(wtc.get("exit_intent_sensitivity"), "medium")

    def test_normalize_rejects_invalid_and_keeps_defaults(self) -> None:
        out = normalize_widget_trigger_config(
            {
                "exit_intent_sensitivity": "nope",
                "exit_intent_delay_seconds": 99,
                "hesitation_after_seconds": "bad",
            }
        )
        self.assertEqual(out["exit_intent_sensitivity"], "medium")
        self.assertEqual(out["exit_intent_delay_seconds"], 0)
        self.assertEqual(out["hesitation_after_seconds"], 20)

    def test_widget_trigger_partial_post_roundtrip(self) -> None:
        db.create_all()
        base = self.client.get("/api/recovery-settings").json()
        self.assertTrue(base.get("ok"), base)
        pr = self.client.post(
            "/api/recovery-settings",
            json={
                "widget_trigger_config": {
                    "exit_intent_enabled": False,
                    "exit_intent_delay_seconds": 5,
                    "hesitation_condition": "inactivity",
                }
            },
        )
        self.assertEqual(pr.status_code, 200, pr.text)
        out = pr.json()
        self.assertTrue(out.get("ok"), out)
        wtc = out["widget_trigger_config"]
        self.assertFalse(wtc["exit_intent_enabled"])
        self.assertEqual(wtc["exit_intent_delay_seconds"], 5)
        self.assertEqual(wtc["hesitation_condition"], "inactivity")
        self.assertEqual(wtc["exit_intent_sensitivity"], "medium")

    def test_row_invalid_json_falls_back_to_defaults(self) -> None:
        row = Store(zid_store_id="z_wtc_bad_json")
        row.cf_widget_trigger_settings_json = "{not json"
        self.assertEqual(
            widget_trigger_config_from_store_row(row)["exit_intent_frequency"],
            DEFAULT_WIDGET_TRIGGER_CONFIG["exit_intent_frequency"],
        )

    def test_public_config_includes_widget_trigger(self) -> None:
        db.create_all()
        r = self.client.get("/api/cartflow/public-config", params={"store_slug": "demo"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"), body)
        self.assertIn("widget_trigger_config", body)


if __name__ == "__main__":
    unittest.main()
