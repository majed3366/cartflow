# -*- coding: utf-8 -*-
"""Scheduler Meta Runtime startup log V2 — single-line Railway evidence."""
from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from services.meta_recovery_template_contract_v1 import TEMPLATE_NAME
from services.runtime_startup_v1 import _log_scheduler_meta_runtime
from services.scheduler_meta_preflight_v1 import (
    format_scheduler_meta_runtime_log_line,
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


class SchedulerMetaRuntimeSingleLineTests(unittest.TestCase):
    def tearDown(self) -> None:
        _clear_meta_env()

    def _capture(self, env: dict[str, str]) -> tuple[str, dict | None]:
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False):
            with redirect_stdout(buf):
                payload = log_scheduler_meta_runtime(role="scheduler")
        return buf.getvalue(), payload

    def _one_line(self, text: str) -> str:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, text)
        return lines[0]

    def test_complete_meta_ready_true_single_line(self) -> None:
        text, payload = self._capture(_COMPLETE_META_ENV)
        assert payload is not None
        self.assertTrue(payload["ready_for_meta_recovery"])
        line = self._one_line(text)
        expected = (
            "[SCHEDULER META RUNTIME] "
            "role=scheduler "
            "whatsapp_provider=meta "
            f"meta_template_name={TEMPLATE_NAME} "
            "access_token_configured=true "
            "phone_number_id_configured=true "
            "waba_id_configured=true "
            "ready_for_meta_recovery=true"
        )
        self.assertEqual(line, expected)
        self.assertEqual(line.count("[SCHEDULER META RUNTIME]"), 1)

    def test_twilio_provider_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["WHATSAPP_PROVIDER"] = "twilio"
        text, payload = self._capture(env)
        assert payload is not None
        self.assertFalse(payload["ready_for_meta_recovery"])
        line = self._one_line(text)
        self.assertIn("whatsapp_provider=twilio", line)
        self.assertIn("ready_for_meta_recovery=false", line)

    def test_wrong_template_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env["WHATSAPP_META_RECOVERY_TEMPLATE_NAME"] = "cartflow_cart_reminder_ar_v1"
        text, payload = self._capture(env)
        assert payload is not None
        self.assertFalse(payload["ready_for_meta_recovery"])
        line = self._one_line(text)
        self.assertIn("meta_template_name=cartflow_cart_reminder_ar_v1", line)
        self.assertIn("ready_for_meta_recovery=false", line)

    def test_missing_access_token_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env.pop("WHATSAPP_ACCESS_TOKEN")
        _clear_meta_env()
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False):
            for k in (
                "WHATSAPP_ACCESS_TOKEN",
                "WHATSAPP_API_TOKEN",
                "WHATSAPP_CLOUD_API_TOKEN",
                "META_WHATSAPP_TOKEN",
            ):
                os.environ.pop(k, None)
            with redirect_stdout(buf):
                payload = log_scheduler_meta_runtime(role="scheduler")
        assert payload is not None
        self.assertFalse(payload["access_token_configured"])
        self.assertFalse(payload["ready_for_meta_recovery"])
        line = self._one_line(buf.getvalue())
        self.assertIn("access_token_configured=false", line)
        self.assertIn("ready_for_meta_recovery=false", line)

    def test_missing_phone_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env.pop("WHATSAPP_PHONE_NUMBER_ID")
        _clear_meta_env()
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("WHATSAPP_PHONE_NUMBER_ID", None)
            os.environ.pop("WHATSAPP_PHONE_ID", None)
            with redirect_stdout(buf):
                payload = log_scheduler_meta_runtime(role="scheduler")
        assert payload is not None
        self.assertFalse(payload["phone_number_id_configured"])
        self.assertFalse(payload["ready_for_meta_recovery"])
        self.assertIn("phone_number_id_configured=false", self._one_line(buf.getvalue()))

    def test_missing_waba_ready_false(self) -> None:
        env = dict(_COMPLETE_META_ENV)
        env.pop("WHATSAPP_BUSINESS_ACCOUNT_ID")
        _clear_meta_env()
        buf = io.StringIO()
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("WHATSAPP_BUSINESS_ACCOUNT_ID", None)
            os.environ.pop("WABA_ID", None)
            with redirect_stdout(buf):
                payload = log_scheduler_meta_runtime(role="scheduler")
        assert payload is not None
        self.assertFalse(payload["waba_id_configured"])
        self.assertFalse(payload["ready_for_meta_recovery"])
        self.assertIn("waba_id_configured=false", self._one_line(buf.getvalue()))

    def test_api_role_emits_nothing(self) -> None:
        buf = io.StringIO()
        with patch.dict(os.environ, _COMPLETE_META_ENV, clear=False):
            with redirect_stdout(buf):
                out = log_scheduler_meta_runtime(role="api")
                _log_scheduler_meta_runtime("api")
        self.assertIsNone(out)
        self.assertEqual(buf.getvalue(), "")

    def test_exception_emits_safe_error_line(self) -> None:
        buf = io.StringIO()
        with patch.dict(os.environ, _COMPLETE_META_ENV, clear=False):
            with patch(
                "services.scheduler_meta_preflight_v1.build_scheduler_meta_preflight",
                side_effect=RuntimeError("secret=EAAB_should_not_leak"),
            ):
                with redirect_stdout(buf):
                    out = log_scheduler_meta_runtime(role="scheduler")
        self.assertIsNone(out)
        line = self._one_line(buf.getvalue())
        self.assertEqual(line, "[SCHEDULER META RUNTIME ERROR] error=RuntimeError")
        self.assertNotIn("EAAB", line)
        self.assertNotIn("secret", line)

    def test_wrapper_exception_emits_error_and_continues(self) -> None:
        buf = io.StringIO()
        with patch(
            "services.scheduler_meta_preflight_v1.log_scheduler_meta_runtime",
            side_effect=ImportError("boom"),
        ):
            with redirect_stdout(buf):
                _log_scheduler_meta_runtime("scheduler")
        line = self._one_line(buf.getvalue())
        self.assertTrue(line.startswith("[SCHEDULER META RUNTIME ERROR] error="))
        self.assertNotIn("boom", line)

    def test_no_secret_values_in_logs(self) -> None:
        text, payload = self._capture(_COMPLETE_META_ENV)
        line = self._one_line(text)
        self.assertNotIn("EAAB_secret_token_must_not_appear", line)
        self.assertNotIn("999888777666555", line)
        self.assertNotIn("152111222333766", line)
        self.assertNotIn("Authorization", line)
        self.assertNotIn("Bearer", line)
        formatted = format_scheduler_meta_runtime_log_line(payload)
        self.assertNotIn("EAAB_secret_token_must_not_appear", formatted)
        self.assertEqual(formatted.count("\n"), 0)


if __name__ == "__main__":
    unittest.main()
