# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import unittest

from services import cartflow_provider_readiness as pr
from services import cartflow_runtime_health as rh
from services.recovery_blocker_display import recovery_blocker_from_latest_log_status


class CartflowProviderReadinessTests(unittest.TestCase):
    def tearDown(self) -> None:
        pr.reset_provider_readiness_log_throttle_for_tests()
        for k in (
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_WHATSAPP_FROM",
            "PRODUCTION_MODE",
            "CARTFLOW_PROVIDER_READINESS_LOG",
        ):
            os.environ.pop(k, None)

    def test_twilio_missing_env_not_configured(self) -> None:
        os.environ.pop("TWILIO_ACCOUNT_SID", None)
        os.environ.pop("TWILIO_AUTH_TOKEN", None)
        os.environ.pop("TWILIO_WHATSAPP_FROM", None)
        tw = pr.get_twilio_readiness()
        self.assertFalse(tw["configured"])
        self.assertEqual(tw["failure_class"], pr.FAILURE_PROVIDER_NOT_CONFIGURED)

    def test_twilio_configured_structure(self) -> None:
        os.environ["TWILIO_ACCOUNT_SID"] = "ACaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        os.environ["TWILIO_AUTH_TOKEN"] = "tok"
        os.environ["TWILIO_WHATSAPP_FROM"] = "+14155555555"
        tw = pr.get_twilio_readiness()
        self.assertTrue(tw["configured"])
        self.assertEqual(tw["failure_class"], "ok")

    def test_classify_sandbox_join(self) -> None:
        self.assertEqual(
            pr.classify_provider_failure("Error 63016: sandbox not joined"),
            pr.FAILURE_SANDBOX_RECIPIENT,
        )

    def test_classify_auth(self) -> None:
        self.assertEqual(
            pr.classify_provider_failure("Authenticate", None),
            pr.FAILURE_PROVIDER_AUTH,
        )

    def test_runtime_health_provider_summary(self) -> None:
        snap = rh.build_runtime_health_snapshot()
        prt = snap.get("provider_runtime") or {}
        self.assertIn("provider_readiness_summary", prt)
        self.assertIn("provider_failure_class", prt)

    def test_whatsapp_failed_blocker_enrichment_not_configured(self) -> None:
        os.environ.pop("TWILIO_ACCOUNT_SID", None)
        b = recovery_blocker_from_latest_log_status("whatsapp_failed")
        self.assertIsNotNone(b)
        enriched = pr.enrich_whatsapp_failed_blocker(
            b,
            readiness=pr.get_whatsapp_provider_readiness(),
        )
        self.assertIsNotNone(enriched)
        self.assertEqual(enriched.get("label_ar"), b.get("label_ar"))
        self.assertIn("provider_issue_hint_ar", enriched)
        self.assertIn("غير", str(enriched.get("provider_issue_hint_ar") or ""))


if __name__ == "__main__":
    unittest.main()
