# -*- coding: utf-8 -*-
"""Provider send timeout protection v1 — Twilio boundary, recovery safety."""
from __future__ import annotations

import io
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from services.cartflow_provider_readiness import classify_provider_failure
from services.provider_send_timeout_v1 import (
    clear_provider_send_events_for_tests,
    drain_recent_provider_send_events,
    execute_provider_call_with_timeout,
    provider_send_timeout_seconds,
    twilio_messages_create,
)
from services.whatsapp_send import (
    resolve_whatsapp_recovery_log_status,
    send_whatsapp,
)


class ProviderSendTimeoutV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        clear_provider_send_events_for_tests()
        try:
            from services.cartflow_runtime_health import clear_runtime_anomaly_buffer_for_tests

            clear_runtime_anomaly_buffer_for_tests()
        except Exception:  # noqa: BLE001
            pass

    def tearDown(self) -> None:
        clear_provider_send_events_for_tests()

    def test_timeout_returns_structured_failure(self) -> None:
        def _slow() -> str:
            time.sleep(2.0)
            return "never"

        out = execute_provider_call_with_timeout(
            _slow,
            provider="twilio",
            recovery_key="demo:s-timeout",
            timeout_seconds=0.05,
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "provider_timeout")
        self.assertEqual(out.get("provider"), "twilio")

    def test_timeout_logs_and_records_event(self) -> None:
        buf = io.StringIO()

        def _slow() -> str:
            time.sleep(2.0)
            return "never"

        with redirect_stdout(buf):
            execute_provider_call_with_timeout(
                _slow,
                provider="twilio",
                recovery_key="demo:s-log",
                timeout_seconds=0.05,
            )
        text = buf.getvalue()
        self.assertIn("[PROVIDER TIMEOUT]", text)
        self.assertIn("provider=twilio", text)
        self.assertIn("recovery_key=demo:s-log", text)
        self.assertIn("timeout_seconds=", text)
        self.assertIn("[PROVIDER FAILURE]", text)
        self.assertIn("reason=provider_timeout", text)
        events = drain_recent_provider_send_events()
        self.assertTrue(any(e.get("kind") == "timeout" for e in events))

    def test_success_path_unblocked(self) -> None:
        out = execute_provider_call_with_timeout(
            lambda: {"sid": "SM1"},
            provider="twilio",
            timeout_seconds=1.0,
        )
        self.assertTrue(out.get("ok"))
        self.assertEqual(out["result"]["sid"], "SM1")

    @patch.dict(
        "os.environ",
        {
            "PRODUCTION_MODE": "true",
            "TWILIO_ACCOUNT_SID": "ACtest",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
            "PROVIDER_SEND_TIMEOUT_SECONDS": "0.05",
        },
        clear=False,
    )
    @patch(
        "services.whatsapp_production_reality_v2.enforce_whatsapp_template_window_before_send",
        return_value=None,
    )
    @patch("services.whatsapp_send.twilio_messages_create")
    @patch("services.whatsapp_send.build_twilio_client")
    def test_send_whatsapp_maps_timeout_to_whatsapp_failed(
        self,
        mock_client: MagicMock,
        mock_create: MagicMock,
        _gate: MagicMock,
    ) -> None:
        mock_client.return_value = MagicMock()
        mock_create.return_value = {
            "ok": False,
            "error": "provider_timeout",
            "provider": "twilio",
            "timeout_seconds": 0.05,
            "failure_class": "provider_unavailable",
        }
        out = send_whatsapp(
            "+966500000001",
            "hello",
            recovery_key="demo:s-wa",
            wa_trace_store_slug="demo",
            wa_trace_session_id="s-wa",
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "provider_timeout")
        self.assertEqual(
            resolve_whatsapp_recovery_log_status(out),
            "whatsapp_failed",
        )

    @patch.dict(
        "os.environ",
        {
            "PRODUCTION_MODE": "true",
            "TWILIO_ACCOUNT_SID": "ACtest",
            "TWILIO_AUTH_TOKEN": "tok",
            "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
        },
        clear=False,
    )
    @patch(
        "services.whatsapp_production_reality_v2.enforce_whatsapp_template_window_before_send",
        return_value=None,
    )
    @patch(
        "services.whatsapp_delivery_truth_v1.record_provider_acceptance_from_send",
    )
    @patch("services.whatsapp_send.twilio_messages_create")
    @patch("services.whatsapp_send.build_twilio_client")
    def test_send_whatsapp_success_unchanged(
        self,
        mock_client: MagicMock,
        mock_create: MagicMock,
        _record: MagicMock,
        _gate: MagicMock,
    ) -> None:
        msg = MagicMock()
        msg.sid = "SM999"
        msg.status = "queued"
        mock_client.return_value = MagicMock()
        mock_create.return_value = {"ok": True, "msg": msg}
        out = send_whatsapp(
            "+966500000001",
            "hello",
            wa_trace_store_slug="demo",
            wa_trace_session_id="s-ok",
        )
        self.assertTrue(out.get("ok"))
        self.assertEqual(out.get("sid"), "SM999")
        self.assertEqual(
            resolve_whatsapp_recovery_log_status(out),
            "sent_real",
        )

    def test_twilio_messages_create_timeout_boundary(self) -> None:
        client = MagicMock()

        def _hang(**_kwargs: object) -> None:
            time.sleep(2.0)

        client.messages.create.side_effect = _hang
        with patch(
            "services.provider_send_timeout_v1.provider_send_timeout_seconds",
            return_value=0.05,
        ):
            out = twilio_messages_create(
                client,
                recovery_key="demo:s-twilio",
                from_="whatsapp:+1",
                to="whatsapp:+966500000001",
                body="hi",
            )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "provider_timeout")

    def test_classify_provider_timeout(self) -> None:
        self.assertEqual(
            classify_provider_failure("provider_timeout", None),
            "provider_unavailable",
        )

    def test_queue_treats_timeout_as_send_failure(self) -> None:
        import services.whatsapp_queue as wq

        self.assertFalse(
            wq._is_send_ok({"ok": False, "error": "provider_timeout"})
        )
        self.assertEqual(
            resolve_whatsapp_recovery_log_status(
                {"ok": False, "error": "provider_timeout"}
            ),
            "whatsapp_failed",
        )

    def test_default_timeout_constant(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(provider_send_timeout_seconds(), 30.0)


if __name__ == "__main__":
    unittest.main()
