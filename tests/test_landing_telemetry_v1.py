# -*- coding: utf-8 -*-
"""Landing Page Reality Validation V1 — anonymous telemetry."""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/cartflow_landing_telemetry_test.db")


class LandingTelemetryV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from extensions import db
        from services.landing_telemetry_v1 import reset_landing_telemetry_schema_guard_for_tests

        reset_landing_telemetry_schema_guard_for_tests()
        import models  # noqa: F401

        models.LandingPageEventV1.__table__.drop(bind=db.engine, checkfirst=True)
        models.LandingPageEventV1.__table__.create(bind=db.engine, checkfirst=True)

    def test_rejects_unknown_event(self) -> None:
        from services.landing_telemetry_v1 import record_landing_event

        out = record_landing_event(event="hack_event", device="mobile")
        self.assertFalse(out.get("ok"))

    def test_records_allowed_event_and_summary(self) -> None:
        from services.landing_telemetry_v1 import (
            record_landing_event,
            summarize_landing_telemetry,
        )

        self.assertTrue(
            record_landing_event(
                event="landing_opened",
                device="desktop",
                session_key="s_testsession01",
            ).get("ok")
        )
        self.assertTrue(
            record_landing_event(
                event="hero_cta_clicked",
                section="hero",
                device="desktop",
                session_key="s_testsession01",
            ).get("ok")
        )
        summary = summarize_landing_telemetry(hours=24)
        self.assertTrue(summary.get("ok"))
        self.assertGreaterEqual(summary.get("landing_opened", 0), 1)
        self.assertIn("hero_cta_clicked", summary.get("by_event", {}))

    def test_public_endpoint_allows_anonymous_post(self) -> None:
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        r = client.post(
            "/api/landing/event",
            json={
                "event": "scroll_50",
                "section": "page",
                "device": "mobile",
                "session_key": "s_mobileabc",
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

        bad = client.post("/api/landing/event", json={"event": "not_real"})
        self.assertEqual(bad.status_code, 400)


if __name__ == "__main__":
    unittest.main()
