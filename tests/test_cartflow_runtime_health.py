# -*- coding: utf-8 -*-
"""Runtime health visibility foundation (read-only; no recovery behavior changes)."""

from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stdout

from services import cartflow_runtime_health as rh


class CartflowRuntimeHealthTests(unittest.TestCase):
    def tearDown(self) -> None:
        rh.clear_runtime_anomaly_buffer_for_tests()
        os.environ.pop("CARTFLOW_STRUCTURED_HEALTH_LOG", None)

    def test_build_runtime_health_snapshot_sections(self) -> None:
        snap = rh.build_runtime_health_snapshot()
        for key in (
            "recovery_runtime",
            "whatsapp_runtime",
            "identity_runtime",
            "dashboard_runtime",
            "duplicate_protection_runtime",
            "lifecycle_consistency_runtime",
            "behavioral_runtime",
            "provider_runtime",
        ):
            self.assertIn(key, snap)
            self.assertIsInstance(snap[key], dict)
        self.assertIn("runtime_active", snap["recovery_runtime"])
        self.assertIn("whatsapp_provider_configured", snap["whatsapp_runtime"])
        self.assertIn("recent_send_failures_24h", snap["provider_runtime"])
        self.assertIn("provider_readiness_summary", snap["provider_runtime"])
        lc = snap["lifecycle_consistency_runtime"]
        for k in (
            "lifecycle_runtime_ok",
            "lifecycle_conflict_detected",
            "invalid_transition_recently",
        ):
            self.assertIn(k, lc)
        for k in (
            "duplicate_anomaly_count",
            "duplicate_send_blocked_recently",
            "duplicate_prevention_runtime_ok",
        ):
            self.assertIn(k, snap["duplicate_protection_runtime"])

    def test_aggregate_anomaly_symbols(self) -> None:
        self.assertEqual(
            rh.aggregate_anomaly_symbols(["a", "a", "b"]),
            {"a": 2, "b": 1},
        )

    def test_map_conflict_codes_to_anomalies(self) -> None:
        out = rh.map_conflict_codes_to_anomalies(
            ["identity_trust_failed_with_send_success_log", "unknown_x"]
        )
        self.assertIn(rh.ANOMALY_IDENTITY_MERGE_BLOCKED, out)
        self.assertIn("unknown_x", out)

    def test_record_and_count_anomalies(self) -> None:
        rh.record_runtime_anomaly(
            rh.ANOMALY_PROVIDER_SEND_FAILURE, source="test", detail="x"
        )
        counts = rh.recent_anomaly_type_counts()
        self.assertGreaterEqual(counts.get(rh.ANOMALY_PROVIDER_SEND_FAILURE, 0), 1)
        snap = rh.build_runtime_health_snapshot()
        self.assertGreater(int(snap.get("_buffered_anomaly_events") or 0), 0)

    def test_identity_conflict_flag_from_buffer(self) -> None:
        rh.record_runtime_anomaly(rh.ANOMALY_IDENTITY_MERGE_BLOCKED)
        snap = rh.build_runtime_health_snapshot()
        self.assertTrue(snap["identity_runtime"].get("identity_conflict_detected"))

    def test_admin_summary_shape(self) -> None:
        summary = rh.build_admin_runtime_summary()
        for k in (
            "recovery_runtime_ok",
            "identity_runtime_ok",
            "provider_runtime_ok",
            "dashboard_runtime_ok",
            "recent_anomaly_count",
            "trust",
            "provider",
            "duplicate_protection",
            "lifecycle_consistency",
        ):
            self.assertIn(k, summary)
        self.assertIn("runtime_trust_label_ar", summary["trust"])
        self.assertIn("duplicate_anomaly_count", summary["duplicate_protection"])
        self.assertIn("lifecycle_conflict_detected", summary["lifecycle_consistency"])

    def test_trust_signals_lifecycle_degraded(self) -> None:
        s = rh.derive_runtime_trust_signals(
            {
                "provider_runtime": {
                    "whatsapp_provider_ready": True,
                    "provider_effectively_disabled": False,
                },
                "recovery_runtime": {"runtime_active": True},
                "identity_runtime": {
                    "identity_resolution_ok": True,
                    "identity_conflict_detected": False,
                },
                "duplicate_protection_runtime": {
                    "duplicate_prevention_runtime_ok": True,
                },
                "lifecycle_consistency_runtime": {
                    "lifecycle_runtime_ok": False,
                },
            },
            recent_anomaly_count=0,
        )
        self.assertTrue(s.get("runtime_degraded") or s.get("runtime_warning"))

    def test_trust_signals_duplicate_degraded(self) -> None:
        s = rh.derive_runtime_trust_signals(
            {
                "provider_runtime": {
                    "whatsapp_provider_ready": True,
                    "provider_effectively_disabled": False,
                },
                "recovery_runtime": {"runtime_active": True},
                "identity_runtime": {
                    "identity_resolution_ok": True,
                    "identity_conflict_detected": False,
                },
                "duplicate_protection_runtime": {
                    "duplicate_prevention_runtime_ok": False,
                },
            },
            recent_anomaly_count=0,
        )
        self.assertTrue(s.get("runtime_degraded") or s.get("runtime_warning"))

    def test_trust_signals_keys(self) -> None:
        s = rh.derive_runtime_trust_signals(
            {
                "provider_runtime": {
                    "whatsapp_provider_ready": True,
                    "provider_effectively_disabled": False,
                },
                "recovery_runtime": {"runtime_active": True},
                "identity_runtime": {
                    "identity_resolution_ok": True,
                    "identity_conflict_detected": False,
                },
            },
            recent_anomaly_count=0,
        )
        self.assertIn("runtime_stable", s)
        self.assertIn("runtime_degraded", s)
        self.assertIn("runtime_warning", s)

    def test_structured_health_log_emits_when_enabled(self) -> None:
        os.environ["CARTFLOW_STRUCTURED_HEALTH_LOG"] = "1"
        buf = io.StringIO()
        with redirect_stdout(buf):
            rh.emit_health_log("ping", recovery_runtime_active=True)
        self.assertIn("[CARTFLOW HEALTH]", buf.getvalue())
        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            rh.emit_anomaly_log("test_type", foo="bar")
        self.assertIn("[CARTFLOW ANOMALY]", buf2.getvalue())
        buf3 = io.StringIO()
        with redirect_stdout(buf3):
            rh.emit_provider_log("twilio_check", configured=True)
        self.assertIn("[CARTFLOW PROVIDER]", buf3.getvalue())

    def test_no_health_log_when_disabled(self) -> None:
        os.environ.pop("CARTFLOW_STRUCTURED_HEALTH_LOG", None)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rh.emit_health_log("silent")
        self.assertEqual(buf.getvalue().strip(), "")


if __name__ == "__main__":
    unittest.main()
