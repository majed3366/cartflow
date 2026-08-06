# -*- coding: utf-8 -*-
"""Scheduler Meta Runtime startup log — sanitized provider evidence."""
from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from services.meta_recovery_template_contract_v1 import TEMPLATE_NAME
from services.scheduler_meta_preflight_v1 import (
    format_scheduler_meta_runtime_log_lines,
    log_scheduler_meta_runtime,
)


_COMPLETE_META_ENV = {
    "CARTFLOW_PROCESS_ROLE": "scheduler",
    "WHATSAPP_PROVIDER": "meta",
    "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": TEMPLATE_NAME,
    "WHATSAPP_ACCESS_TOKEN": "EAAB_secret_token_must_not_appear",
    "WHATSAPP_PHONE_NUMBER_ID": "999888777666555",
    "WHATSAPP_BUSINESS_ACCOUNT_ID": "152111222333766",
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


class SchedulerMetaRuntimeLogTests(unittest.TestCase):
    def tearDown(self) -> None:
        _clear_meta_env()

    def _capture(self, env: dict[str, str]) -> tuple[str, dict | None]:
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False):
            with redirect_stdout(buf):
                payload = log_scheduler_meta_runtime(role="scheduler")
        return buf.getvalue(), payload

    def test_complete_meta_scheduler_config_ready_true(self) -> None:
        text, payload = self._capture(_COMPLETE_META_ENV)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertTrue(payload["ready_for_meta_recovery"])
        self.assertIn("[SCHEDULER META RUNTIME]", text)
        self.assertIn("role=scheduler", text)
        self.assertIn("whatsapp_provider=meta", text)
        self.assertIn(f"meta_template_name={TEMPLATE_NAME}", text)
        self.assertIn("access_token_configured=true", text)
        self.assertIn("phone_number_id_configured=true", text)
        self.assertIn("waba_id_configured=true", text)
        self.assertIn("ready_for_meta_recovery=true", text)

    def test_twilio_provider_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["WHATSAPP_PROVIDER"] = "twilio"
        text, payload = self._capture(env)
        assert payload is not None
        self.assertFalse(payload["ready_for_meta_recovery"])
        self.assertIn("whatsapp_provider=twilio", text)
        self.assertIn("ready_for_meta_recovery=false", text)

    def test_wrong_template_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["WHATSAPP_META_RECOVERY_TEMPLATE_NAME"] = "cartflow_cart_reminder_ar_v1"
        text, payload = self._capture(env)
        assert payload is not None
        self.assertFalse(payload["ready_for_meta_recovery"])
        self.assertIn("meta_template_name=cartflow_cart_reminder_ar_v1", text)
        self.assertIn("ready_for_meta_recovery=false", text)

    def test_missing_token_phone_waba_ready_false(self) -> None:
        env = {
            "CARTFLOW_PROCESS_ROLE": "scheduler",
            "WHATSAPP_PROVIDER": "meta",
            "WHATSAPP_META_RECOVERY_TEMPLATE_NAME": TEMPLATE_NAME,
        }
        _clear_meta_env()
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False):
            for k in (
                "WHATSAPP_ACCESS_TOKEN",
                "WHATSAPP_API_TOKEN",
                "WHATSAPP_CLOUD_API_TOKEN",
                "META_WHATSAPP_TOKEN",
                "WHATSAPP_PHONE_NUMBER_ID",
                "WHATSAPP_PHONE_ID",
                "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "WABA_ID",
            ):
                os.environ.pop(k, None)
            with redirect_stdout(buf):
                payload = log_scheduler_meta_runtime(role="scheduler")
            text = buf.getvalue()
        assert payload is not None
        self.assertFalse(payload["access_token_configured"])
        self.assertFalse(payload["phone_number_id_configured"])
        self.assertFalse(payload["waba_id_configured"])
        self.assertFalse(payload["ready_for_meta_recovery"])
        self.assertIn("access_token_configured=false", text)
        self.assertIn("phone_number_id_configured=false", text)
        self.assertIn("waba_id_configured=false", text)
        self.assertIn("ready_for_meta_recovery=false", text)

    def test_api_role_emits_nothing(self) -> None:
        buf = io.StringIO()
        with patch.dict(os.environ, _COMPLETE_META_ENV, clear=False):
            with redirect_stdout(buf):
                out = log_scheduler_meta_runtime(role="api")
        self.assertIsNone(out)
        self.assertEqual(buf.getvalue(), "")

    def test_no_secret_values_in_logs(self) -> None:
        text, payload = self._capture(_COMPLETE_META_ENV)
        self.assertNotIn("EAAB_secret_token_must_not_appear", text)
        self.assertNotIn("999888777666555", text)
        self.assertNotIn("152111222333766", text)
        self.assertNotIn("Authorization", text)
        self.assertNotIn("Bearer", text)
        joined = "\n".join(format_scheduler_meta_runtime_log_lines(payload))
        self.assertNotIn("EAAB_secret_token_must_not_appear", joined)
        self.assertNotIn("999888777666555", joined)


if __name__ == "__main__":
    unittest.main()
