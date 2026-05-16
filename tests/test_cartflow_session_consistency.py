# -*- coding: utf-8 -*-
"""Session/cart runtime consistency diagnostics (read-only; no recovery behavior changes)."""

from __future__ import annotations

import os
import unittest

from unittest.mock import MagicMock

from services import cartflow_runtime_health as rh
from services import cartflow_session_consistency as sc


class CartflowSessionConsistencyTests(unittest.TestCase):
    def tearDown(self) -> None:
        sc.reset_session_consistency_for_tests()
        rh.clear_runtime_anomaly_buffer_for_tests()
        os.environ.pop("CARTFLOW_SESSION_CONSISTENCY_LOG", None)
        os.environ.pop("CARTFLOW_STRUCTURED_HEALTH_LOG", None)
        os.environ.pop("CARTFLOW_OBSERVABILITY_MODE", None)

    def test_validate_session_scope_missing_both(self) -> None:
        issues = sc.validate_session_runtime_consistency(session_id="", cart_id="")
        self.assertIn("missing_session_and_cart_scope", issues)

    def test_stale_behavioral_merge_intent_weaken_reply(self) -> None:
        hint = sc.detect_stale_behavioral_merge_intent(
            {"customer_replied": True},
            {"customer_replied": False},
        )
        self.assertEqual(hint, "weaken_terminal:customer_replied")

    def test_stale_behavioral_merge_intent_lifecycle_clear(self) -> None:
        hint = sc.detect_stale_behavioral_merge_intent(
            {"lifecycle_hint": "returned"},
            {"lifecycle_hint": ""},
        )
        self.assertEqual(hint, "lifecycle_hint_downgrade_intent")

    def test_dashboard_drift_converted_vs_phase(self) -> None:
        issues = sc.detect_dashboard_runtime_drift(
            phase_key="pending_send",
            latest_log_status="stopped_converted",
            behavioral={},
            sent_ct=0,
        )
        self.assertIn("log_converted_phase_mismatch", issues)

    def test_finalize_payload_marks_inconsistent(self) -> None:
        ac = MagicMock()
        ac.recovery_session_id = "s1"
        ac.zid_cart_id = "c1"
        payload: dict = {}
        sc.finalize_dashboard_session_payload(
            payload,
            ac=ac,
            phase_key="pending_send",
            coarse="pending",
            latest_log_status="stopped_converted",
            behavioral={},
            sent_ct=0,
            store_slug="demo",
        )
        self.assertFalse(payload.get("normal_recovery_session_runtime_consistent"))
        self.assertIn("log_converted_phase_mismatch", payload.get("normal_recovery_session_consistency_codes") or [])

    def test_finalize_payload_ok_no_trust_hint_key(self) -> None:
        ac = MagicMock()
        ac.recovery_session_id = "s1"
        ac.zid_cart_id = "c1"
        payload: dict = {}
        sc.finalize_dashboard_session_payload(
            payload,
            ac=ac,
            phase_key="stopped_purchase",
            coarse="complete",
            latest_log_status="stopped_converted",
            behavioral={},
            sent_ct=1,
            store_slug="demo",
        )
        self.assertTrue(payload.get("normal_recovery_session_runtime_consistent"))
        self.assertNotIn("normal_recovery_session_trust_hint_ar", payload)

    def test_provider_stale_callback_counter(self) -> None:
        sc.note_stale_provider_callback_intent(
            store_slug="x",
            session_id="a",
            cart_id="b",
            detected_state="late_ack",
        )
        d = sc.get_session_consistency_diagnostics_readonly()
        self.assertGreaterEqual(int(d["counters"].get("provider_stale_callbacks", 0)), 1)
        self.assertTrue(d.get("stale_state_detected"))

    def test_frontend_stale_emits_when_log_enabled(self) -> None:
        os.environ["CARTFLOW_OBSERVABILITY_MODE"] = "basic"
        os.environ["CARTFLOW_SESSION_CONSISTENCY_LOG"] = "1"
        with self.assertLogs("cartflow", level="INFO") as cm:
            sc.note_frontend_stale_state_intent(
                store_slug="demo", session_id="s", cart_id="c"
            )
        joined = "\n".join(cm.output)
        self.assertIn("[CARTFLOW SESSION]", joined)
        self.assertIn("frontend_state_stale", joined)

    def test_trust_signals_session_drift_warning(self) -> None:
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
                "lifecycle_consistency_runtime": {"lifecycle_runtime_ok": True},
                "session_consistency_runtime": {
                    "session_runtime_consistent": False,
                    "stale_state_detected": False,
                },
            },
            recent_anomaly_count=0,
        )
        self.assertTrue(s.get("runtime_warning") or s.get("runtime_degraded"))
        self.assertIn("session_runtime_consistent", s)

    def test_health_snapshot_includes_session_consistency(self) -> None:
        snap = rh.build_runtime_health_snapshot()
        self.assertIn("session_consistency_runtime", snap)
        self.assertIn("behavioral_state_consistent", snap["behavioral_runtime"])


if __name__ == "__main__":
    unittest.main()
