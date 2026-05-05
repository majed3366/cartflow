# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from extensions import db
from fastapi.testclient import TestClient

from main import app
from models import Store


class VipOfferRecoverySettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    def test_recovery_settings_roundtrip_vip_offer_fields(self) -> None:
        db.create_all()
        r = self.client.get("/api/recovery-settings")
        self.assertEqual(r.status_code, 200)
        base = r.json()
        self.assertTrue(base.get("ok"), base)
        self.assertIn("vip_offer_enabled", base)
        self.assertIn("vip_offer_type", base)
        self.assertIn("vip_offer_value", base)

        payload = {k: v for k, v in base.items() if k != "ok"}
        payload["vip_offer_enabled"] = True
        payload["vip_offer_type"] = "discount"
        payload["vip_offer_value"] = "12"

        pr = self.client.post("/api/recovery-settings", json=payload)
        self.assertEqual(pr.status_code, 200, pr.text)
        out = pr.json()
        self.assertTrue(out.get("ok"), out)
        self.assertTrue(out.get("vip_offer_enabled"))
        self.assertEqual(out.get("vip_offer_type"), "discount")
        self.assertEqual(out.get("vip_offer_value"), "12")


if __name__ == "__main__":
    unittest.main()
