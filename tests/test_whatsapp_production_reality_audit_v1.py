# -*- coding: utf-8 -*-
"""
WhatsApp Production Reality v1 — audit guards (read-only).

Ensures audit commit does not alter send paths or add external calls.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from services.cartflow_provider_readiness import (
    get_twilio_readiness,
    get_whatsapp_provider_readiness,
)
from services.cartflow_production_readiness import build_cartflow_production_readiness_report
from services.whatsapp_send import recovery_uses_real_whatsapp, send_whatsapp


class WhatsAppProductionRealityAuditTests(unittest.TestCase):
    def test_import_main_succeeds(self) -> None:
        import main  # noqa: F401

        self.assertTrue(hasattr(main, "app"))

    def test_twilio_readiness_shape_unchanged(self) -> None:
        tw = get_twilio_readiness()
        self.assertEqual(tw.get("provider"), "twilio")
        self.assertIn("configured", tw)
        self.assertIn("ready", tw)
        self.assertIn("missing_env", tw)

    def test_whatsapp_provider_readiness_includes_meta_stub(self) -> None:
        r = get_whatsapp_provider_readiness()
        self.assertIn(r.get("provider"), ("twilio", "meta", "unknown"))
        self.assertIn("twilio", r)
        self.assertIn("meta", r)
        meta = r.get("meta") or {}
        self.assertFalse(meta.get("ready"))

    def test_production_readiness_reports_provider(self) -> None:
        report = build_cartflow_production_readiness_report()
        op = report.get("operational") or {}
        pr = op.get("provider_readiness") or {}
        self.assertIn("configured", pr)
        self.assertIn("ready", pr)

    def test_send_whatsapp_no_network_on_missing_twilio(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "TWILIO_ACCOUNT_SID": "",
                "TWILIO_AUTH_TOKEN": "",
                "TWILIO_WHATSAPP_FROM": "",
            },
            clear=False,
        ):
            out = send_whatsapp("+966500000000", "test", reason_tag="price")
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error"), "twilio_not_configured")

    def test_recovery_uses_real_whatsapp_requires_production_mode(self) -> None:
        with patch.dict("os.environ", {"PRODUCTION_MODE": ""}, clear=False):
            with patch(
                "services.whatsapp_send.whatsapp_real_configured",
                return_value=True,
            ):
                self.assertFalse(recovery_uses_real_whatsapp())

    def test_no_requests_in_provider_readiness_module(self) -> None:
        import services.cartflow_provider_readiness as mod

        src = open(mod.__file__, encoding="utf-8").read()
        self.assertNotIn("requests.get", src)
        self.assertNotIn("requests.post", src)
        self.assertNotIn("Client(", src)


if __name__ == "__main__":
    unittest.main()
