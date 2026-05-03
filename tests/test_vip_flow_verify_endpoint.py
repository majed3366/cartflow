# -*- coding: utf-8 -*-
"""GET /dev/vip-flow-verify — proof harness for VIP runtime (dry-run merchant WhatsApp)."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from extensions import db
from main import app
from tests.test_recovery_isolation import _reset_recovery_memory


class VipFlowVerifyEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    def test_vip_flow_verify_json_shape(self) -> None:
        db.create_all()
        r = self.client.get("/dev/vip-flow-verify")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"), body)
        self.assertTrue(body.get("vip_detected"), body)
        self.assertTrue(body.get("customer_recovery_skipped"), body)
        self.assertEqual(body.get("status"), "vip_manual_handling")
        self.assertTrue(body.get("merchant_alert_attempted"), body)


if __name__ == "__main__":
    unittest.main()
