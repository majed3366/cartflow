# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from extensions import db
from fastapi.testclient import TestClient

from main import app


class CartflowWidgetRecoveryGateSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def test_recovery_settings_contains_widget_recovery_gate_fields(self) -> None:
        db.create_all()
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200)
        base = r.json()
        self.assertTrue(base.get("ok"), base)
        self.assertIn("cartflow_widget_enabled", base)
        self.assertIn("cartflow_widget_delay_value", base)
        self.assertIn("cartflow_widget_delay_unit", base)

    def test_recovery_settings_roundtrip_widget_gate_fields(self) -> None:
        db.create_all()
        base = self.client.get("/api/recovery-settings").json()
        self.assertTrue(base.get("ok"), base)
        payload = {k: v for k, v in base.items() if k != "ok"}
        payload["cartflow_widget_enabled"] = False
        payload["cartflow_widget_delay_value"] = 5
        payload["cartflow_widget_delay_unit"] = "minutes"

        pr = self.client.post("/api/recovery-settings", json=payload)
        self.assertEqual(pr.status_code, 200, pr.text)
        out = pr.json()
        self.assertTrue(out.get("ok"), out)
        self.assertFalse(out.get("cartflow_widget_enabled"))
        self.assertEqual(out.get("cartflow_widget_delay_value"), 5)
        self.assertEqual(out.get("cartflow_widget_delay_unit"), "minutes")

    def test_public_config_contains_widget_recovery_gate_fields(self) -> None:
        db.create_all()
        r = self.client.get("/api/cartflow/public-config?store_slug=test")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body.get("ok"), body)
        self.assertIn("cartflow_widget_enabled", body)
        self.assertIn("cartflow_widget_delay_value", body)
        self.assertIn("cartflow_widget_delay_unit", body)


if __name__ == "__main__":
    unittest.main()
