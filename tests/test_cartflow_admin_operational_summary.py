# -*- coding: utf-8 -*-
"""Admin operational summary (read-only aggregates)."""

from __future__ import annotations

import os
import unittest

from services import cartflow_admin_operational_summary as aos
from services import cartflow_runtime_health as rh


class CartflowAdminOperationalSummaryTests(unittest.TestCase):
    def tearDown(self) -> None:
        rh.clear_runtime_anomaly_buffer_for_tests()
        os.environ.pop("ENV", None)

    def test_map_platform_category_degraded_trust(self) -> None:
        cat = aos.map_platform_admin_category(
            trust_signals={"runtime_degraded": True, "runtime_warning": True},
            health_snapshot={},
            aggregate_onboarding={"total_stores_scanned": 0},
        )
        self.assertEqual(cat, aos.ADMIN_PLATFORM_CATEGORY_DEGRADED)

    def test_map_platform_category_healthy(self) -> None:
        cat = aos.map_platform_admin_category(
            trust_signals={
                "runtime_degraded": False,
                "runtime_warning": False,
                "runtime_stable": True,
            },
            health_snapshot={
                "provider_runtime": {"provider_readiness_ready": True},
                "onboarding_runtime": {
                    "sandbox_mode_active": False,
                    "onboarding_ready": True,
                },
            },
            aggregate_onboarding={
                "total_stores_scanned": 2,
                "onboarding_blocked_ratio": 0.1,
                "sandbox_store_ratio": 0.0,
            },
        )
        self.assertEqual(cat, aos.ADMIN_PLATFORM_CATEGORY_HEALTHY)

    def test_trust_bucket_deterministic(self) -> None:
        b, s = aos._store_trust_score_and_bucket(
            onboarding_eval={"ready": True, "completion_percent": 90},
            provider_ready_globally=True,
            need_real_whatsapp=True,
            lifecycle_ok=True,
            dup_ok=True,
            session_ok=True,
        )
        self.assertEqual(b, aos.TRUST_READY)
        self.assertGreaterEqual(s, 82)

        b2, _ = aos._store_trust_score_and_bucket(
            onboarding_eval={"ready": False, "completion_percent": 40},
            provider_ready_globally=False,
            need_real_whatsapp=True,
            lifecycle_ok=True,
            dup_ok=True,
            session_ok=True,
        )
        self.assertIn(b2, (aos.TRUST_DEGRADED, aos.TRUST_UNSTABLE, aos.TRUST_PARTIAL))

    def test_build_summary_has_core_keys(self) -> None:
        payload = aos.build_admin_operational_summary_readonly()
        for k in (
            "platform_admin_category",
            "aggregate_onboarding",
            "anomaly_visibility",
            "degradation_flags",
            "admin_operational_hints_ar",
            "trust_signals_summary",
        ):
            self.assertIn(k, payload, msg=k)
        self.assertTrue(payload.get("runtime_health_reused"))

    def test_anomaly_visibility_increases_hint_pressure(self) -> None:
        rh.record_runtime_anomaly(rh.ANOMALY_PROVIDER_SEND_FAILURE, source="t", detail="x")
        rh.record_runtime_anomaly(rh.ANOMALY_PROVIDER_SEND_FAILURE, source="t", detail="y")
        rh.record_runtime_anomaly(rh.ANOMALY_PROVIDER_SEND_FAILURE, source="t", detail="z")
        p = aos.build_admin_operational_summary_readonly()
        self.assertTrue(p.get("degradation_flags", {}).get("repeated_provider_failures"))
        hints = " ".join(p.get("admin_operational_hints_ar") or [])
        self.assertIn("واتساب", hints)

    def test_dev_endpoint_development_only(self) -> None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)
        os.environ["ENV"] = "production"
        r = client.get("/dev/admin-operational-summary")
        self.assertEqual(r.status_code, 404)
        os.environ["ENV"] = "development"
        r2 = client.get("/dev/admin-operational-summary")
        self.assertEqual(r2.status_code, 200, r2.text[:500])
        body = r2.json()
        self.assertIn("platform_admin_category", body)


if __name__ == "__main__":
    unittest.main()
