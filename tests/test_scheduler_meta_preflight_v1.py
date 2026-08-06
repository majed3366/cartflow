# -*- coding: utf-8 -*-
"""Scheduler Meta Preflight V1 — safe read-only provider config probe."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from services.meta_recovery_template_contract_v1 import TEMPLATE_NAME
from services.scheduler_meta_preflight_v1 import build_scheduler_meta_preflight


_COMPLETE_META_ENV = {
    "CARTFLOW_PROCESS_ROLE": "scheduler",
    "WHATSAPP_PROVIDER": "meta",
    "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": TEMPLATE_NAME,
    "WHATSAPP_ACCESS_TOKEN": "EAAB_test_token_not_real",
    "WHATSAPP_PHONE_NUMBER_ID": "123456789012345",
    "WHATSAPP_BUSINESS_ACCOUNT_ID": "152999999999766",
}


def _clear_meta_env() -> None:
    for key in (
        "CARTFLOW_PROCESS_ROLE",
        "WHATSAPP_PROVIDER",
        "WHATSAPP_META_RECOVERY_TEMPLATE_NAME",
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_API_TOKEN",
        "WHATSAPP_CLOUD_API_TOKEN",
        "META_WHATSAPP_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_PHONE_ID",
        "WHATSAPP_BUSINESS_ACCOUNT_ID",
        "WABA_ID",
    ):
        os.environ.pop(key, None)


class BuildSchedulerMetaPreflightTests(unittest.TestCase):
    def tearDown(self) -> None:
        _clear_meta_env()

    def test_complete_meta_config_ready_true(self) -> None:
        with patch.dict(os.environ, _COMPLETE_META_ENV, clear=False):
            out = build_scheduler_meta_preflight()
        self.assertEqual(out["role"], "scheduler")
        self.assertEqual(out["whatsapp_provider"], "meta")
        self.assertEqual(out["meta_template_name"], TEMPLATE_NAME)
        self.assertEqual(out["template_expected_name"], TEMPLATE_NAME)
        self.assertTrue(out["access_token_configured"])
        self.assertTrue(out["phone_number_id_configured"])
        self.assertTrue(out["waba_id_configured"])
        self.assertTrue(out["ready_for_meta_recovery"])
        self.assertIn("git_sha", out)

    def test_provider_twilio_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["WHATSAPP_PROVIDER"] = "twilio"
        with patch.dict(os.environ, env, clear=False):
            out = build_scheduler_meta_preflight()
        self.assertEqual(out["whatsapp_provider"], "twilio")
        self.assertFalse(out["ready_for_meta_recovery"])

    def test_wrong_template_name_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["WHATSAPP_META_RECOVERY_TEMPLATE_NAME"] = "cartflow_cart_reminder_ar_v1"
        with patch.dict(os.environ, env, clear=False):
            out = build_scheduler_meta_preflight()
        self.assertEqual(out["meta_template_name"], "cartflow_cart_reminder_ar_v1")
        self.assertFalse(out["ready_for_meta_recovery"])

    def test_missing_token_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env.pop("WHATSAPP_ACCESS_TOKEN")
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("WHATSAPP_ACCESS_TOKEN", None)
            os.environ.pop("WHATSAPP_API_TOKEN", None)
            os.environ.pop("WHATSAPP_CLOUD_API_TOKEN", None)
            os.environ.pop("META_WHATSAPP_TOKEN", None)
            out = build_scheduler_meta_preflight()
        self.assertFalse(out["access_token_configured"])
        self.assertFalse(out["ready_for_meta_recovery"])

    def test_api_role_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["CARTFLOW_PROCESS_ROLE"] = "api"
        with patch.dict(os.environ, env, clear=False):
            out = build_scheduler_meta_preflight()
        self.assertEqual(out["role"], "api")
        self.assertFalse(out["ready_for_meta_recovery"])

    def test_no_secret_values_in_response(self) -> None:
        with patch.dict(os.environ, _COMPLETE_META_ENV, clear=False):
            out = build_scheduler_meta_preflight()
        blob = json.dumps(out, ensure_ascii=False)
        self.assertNotIn("EAAB_test_token_not_real", blob)
        self.assertNotIn("123456789012345", blob)
        self.assertNotIn("152999999999766", blob)
        for key in out:
            self.assertNotIn("token", key.lower().replace("access_token_configured", ""))
        self.assertNotIn("access_token", out)
        self.assertNotIn("phone_number_id", out)
        self.assertNotIn("waba_id", out)
        # Only boolean configured flags — never raw IDs
        self.assertIsInstance(out["access_token_configured"], bool)
        self.assertIsInstance(out["phone_number_id_configured"], bool)
        self.assertIsInstance(out["waba_id_configured"], bool)

    def test_placeholder_token_not_configured(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["WHATSAPP_ACCESS_TOKEN"] = "your_token"
        with patch.dict(os.environ, env, clear=False):
            out = build_scheduler_meta_preflight()
        self.assertFalse(out["access_token_configured"])
        self.assertFalse(out["ready_for_meta_recovery"])


class SchedulerMetaPreflightRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_meta_env()
        from fastapi.testclient import TestClient

        from main import app

        self.client = TestClient(app)

    def tearDown(self) -> None:
        _clear_meta_env()

    def test_scheduler_role_returns_preflight(self) -> None:
        with patch.dict(os.environ, _COMPLETE_META_ENV, clear=False):
            r = self.client.get("/dev/scheduler-meta-preflight")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("role"), "scheduler")
        self.assertTrue(body.get("ready_for_meta_recovery"))
        blob = r.text
        self.assertNotIn("EAAB_test_token_not_real", blob)
        self.assertNotIn("123456789012345", blob)

    def test_api_role_rejected(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["CARTFLOW_PROCESS_ROLE"] = "api"
        with patch.dict(os.environ, env, clear=False):
            r = self.client.get("/dev/scheduler-meta-preflight")
        self.assertEqual(r.status_code, 403, r.text)
        body = r.json()
        self.assertEqual(body.get("error"), "role_not_scheduler")
        self.assertEqual(body.get("role"), "api")
        self.assertFalse(body.get("ready_for_meta_recovery"))


if __name__ == "__main__":
    unittest.main()
