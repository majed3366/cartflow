# -*- coding: utf-8 -*-
"""Production readiness report (read-only; no product behavior changes)."""

from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from services import cartflow_production_readiness as pr


class CartflowProductionReadinessTests(unittest.TestCase):
    def tearDown(self) -> None:
        for k in (
            "ENV",
            "PRODUCTION_MODE",
            "SECRET_KEY",
            "DATABASE_URL",
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_WHATSAPP_FROM",
            "WA_RECOVERY_SEND_TRACE",
        ):
            os.environ.pop(k, None)

    def test_payload_shape_core_keys(self) -> None:
        os.environ["ENV"] = "development"
        body = pr.build_cartflow_production_readiness_report()
        for k in (
            "production_ready",
            "blocking_issues",
            "warnings",
            "safe_to_demo",
            "safe_to_onboard_merchant",
            "recommended_next_action_ar",
            "environment",
            "safety_gates",
            "operational",
        ):
            self.assertIn(k, body, msg=k)
        self.assertIsInstance(body["blocking_issues"], list)
        self.assertIsInstance(body["warnings"], list)
        self.assertIsInstance(body["recommended_next_action_ar"], list)

    def test_missing_secret_key_reported_when_unset(self) -> None:
        os.environ.pop("SECRET_KEY", None)
        rep = pr._collect_env_report()
        self.assertIn("SECRET_KEY", rep["missing_required_keys"])

    def test_production_mode_adds_debug_route_blocker(self) -> None:
        os.environ["PRODUCTION_MODE"] = "1"
        os.environ["SECRET_KEY"] = "non-default-test-secret-key-please"
        os.environ["DATABASE_URL"] = "sqlite:////tmp/cartflow_test.db"
        os.environ["TWILIO_ACCOUNT_SID"] = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        os.environ["TWILIO_AUTH_TOKEN"] = "not-a-real-token-for-tests"
        os.environ["TWILIO_WHATSAPP_FROM"] = "whatsapp:+14155238886"
        body = pr.build_cartflow_production_readiness_report()
        self.assertTrue(body["safety_gates"]["production_mode_flag"])
        msgs = " ".join(body["blocking_issues"])
        self.assertIn("/debug/db", msgs)

    def test_development_mode_not_blocked_by_debug_db_rule(self) -> None:
        os.environ["ENV"] = "development"
        os.environ.pop("PRODUCTION_MODE", None)
        body = pr.build_cartflow_production_readiness_report()
        self.assertFalse(body["safety_gates"]["production_mode_flag"])
        dbg_block = any("/debug/db" in x for x in body["blocking_issues"])
        self.assertFalse(dbg_block)

    def test_dev_route_middleware_allowlist_and_production_readiness_route(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        os.environ.pop("ENV", None)
        r_block = client.get("/dev/run-flow")
        self.assertEqual(r_block.status_code, 404)
        r_list = client.get("/dev/routes")
        self.assertEqual(r_list.status_code, 404)
        r_pr = client.get("/dev/production-readiness")
        self.assertEqual(r_pr.status_code, 404)
        os.environ["ENV"] = "development"
        r_pr2 = client.get("/dev/production-readiness")
        self.assertEqual(r_pr2.status_code, 200, r_pr2.text[:400])
        j2 = r_pr2.json()
        self.assertIn("production_ready", j2)

    def test_admin_init_warning_in_production_mode_payload(self) -> None:
        os.environ["PRODUCTION_MODE"] = "true"
        os.environ["SECRET_KEY"] = "custom-prod-key-xxxxxxxx"
        os.environ["DATABASE_URL"] = "postgresql://u:p@db.example/test"
        os.environ["TWILIO_ACCOUNT_SID"] = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        os.environ["TWILIO_AUTH_TOKEN"] = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        os.environ["TWILIO_WHATSAPP_FROM"] = "whatsapp:+10000000000"
        body = pr.build_cartflow_production_readiness_report()
        joined = " ".join(body["warnings"])
        self.assertIn("admin/init-db", joined.lower())
        gate = body["safety_gates"]["admin_init_db_uses_shared_key"]
        self.assertTrue(gate.get("documented_default_key_literal"))

    @mock.patch("services.cartflow_provider_readiness.get_whatsapp_provider_readiness")
    def test_provider_not_ready_blocks_when_real_whatsapp(
        self, mock_prv: mock.Mock
    ) -> None:
        mock_prv.return_value = {
            "provider": "twilio",
            "configured": True,
            "ready": False,
            "failure_class": "provider_auth_failed",
            "missing_env": [],
            "mode": "production",
        }
        os.environ["PRODUCTION_MODE"] = "1"
        os.environ["SECRET_KEY"] = "custom-prod-key-xxxxxxxx"
        os.environ["DATABASE_URL"] = "postgresql://u:p@db.example/test"
        os.environ["TWILIO_ACCOUNT_SID"] = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        os.environ["TWILIO_AUTH_TOKEN"] = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        os.environ["TWILIO_WHATSAPP_FROM"] = "whatsapp:+10000000000"
        body = pr.build_cartflow_production_readiness_report()
        joined = " ".join(body["blocking_issues"])
        self.assertIn("provider readiness", joined.lower())

    def test_no_leak_of_long_secrets_in_serialized_report(self) -> None:
        os.environ["ENV"] = "development"
        secret = "superlongtwiliosecretvalue99999999"
        os.environ["TWILIO_AUTH_TOKEN"] = secret
        os.environ["TWILIO_ACCOUNT_SID"] = "ACtesttesttesttesttesttesttesttest"
        os.environ["TWILIO_WHATSAPP_FROM"] = "whatsapp:+10000000000"
        os.environ["SECRET_KEY"] = "anotherlongsecretforunittestonly9999"
        body = pr.build_cartflow_production_readiness_report()
        blob = json.dumps(body, default=str)
        self.assertNotIn(secret, blob)
        self.assertNotIn(os.environ["SECRET_KEY"], blob)


if __name__ == "__main__":
    unittest.main()
