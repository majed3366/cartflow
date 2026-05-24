# -*- coding: utf-8 -*-
"""Operational truth for CartRecoveryLog.status after WhatsApp outbound."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from services.whatsapp_send import (
    log_wa_send_truth,
    resolve_whatsapp_recovery_log_status,
    whatsapp_send_truth_context,
)


class TestWhatsappSendTruthV1(unittest.TestCase):
    def test_mock_path_ok_without_sid(self) -> None:
        self.assertEqual(
            resolve_whatsapp_recovery_log_status({"ok": True}),
            "mock_sent",
        )

    def test_twilio_accepted_with_sid(self) -> None:
        self.assertEqual(
            resolve_whatsapp_recovery_log_status(
                {"ok": True, "sid": "SM123", "status": "queued"}
            ),
            "sent_real",
        )

    def test_failed_send(self) -> None:
        self.assertEqual(
            resolve_whatsapp_recovery_log_status({"ok": False, "error": "boom"}),
            "whatsapp_failed",
        )

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=True)
    def test_truth_context_production_mode(self, _prod: object) -> None:
        ctx = whatsapp_send_truth_context({"ok": True, "sid": "SM99"})
        self.assertEqual(ctx["provider"], "twilio")
        self.assertEqual(ctx["mode"], "production")
        self.assertEqual(ctx["status_written"], "sent_real")
        self.assertEqual(ctx["message_sid"], "SM99")

    @patch("services.whatsapp_send.recovery_uses_real_whatsapp", return_value=False)
    def test_truth_context_sandbox_mock(self, _prod: object) -> None:
        ctx = whatsapp_send_truth_context({"ok": True})
        self.assertEqual(ctx["provider"], "mock")
        self.assertEqual(ctx["mode"], "sandbox")
        self.assertEqual(ctx["status_written"], "mock_sent")

    def test_log_wa_send_truth_returns_status(self) -> None:
        st = log_wa_send_truth(
            wa_result={"ok": True, "sid": "SMabc"},
            recovery_key="demo:sess-1",
        )
        self.assertEqual(st, "sent_real")


if __name__ == "__main__":
    unittest.main()
