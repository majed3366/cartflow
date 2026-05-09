# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from services import cartflow_duplicate_guard as dg
from services import cartflow_runtime_health as rh
from services.recovery_blocker_display import get_recovery_blocker_display_state
from tests.test_recovery_isolation import _reset_recovery_memory


class CartflowDuplicatePreventionTests(unittest.TestCase):
    def tearDown(self) -> None:
        dg.reset_duplicate_guard_for_tests()
        rh.clear_runtime_anomaly_buffer_for_tests()

    def test_canonical_signatures_stable(self) -> None:
        s1 = dg.canonical_recovery_schedule_signature(
            store_slug="demo", session_id="s1", cart_id="c1"
        )
        self.assertIn("demo", s1)
        self.assertIn("s1", s1)
        s2 = dg.canonical_recovery_send_signature(
            store_slug="demo", session_id="s1", cart_id="c1", attempt_index=2
        )
        self.assertIn("step=2", s2)

    def test_inflight_send_second_claim_blocked(self) -> None:
        rk = "store:x|session:y|cid:z"
        self.assertTrue(dg.try_begin_outbound_whatsapp_inflight(rk, 1, ttl_seconds=30.0))
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertFalse(dg.try_begin_outbound_whatsapp_inflight(rk, 1, ttl_seconds=30.0))
        self.assertIn("[CARTFLOW DUPLICATE]", buf.getvalue())
        self.assertIn("send_duplicate_blocked", buf.getvalue())
        dg.release_outbound_whatsapp_inflight(rk, 1)
        self.assertTrue(dg.try_begin_outbound_whatsapp_inflight(rk, 1, ttl_seconds=30.0))
        dg.release_outbound_whatsapp_inflight(rk, 1)

    def test_behavioral_merge_idempotent_window(self) -> None:
        sig = "beh_ret:test|sig|v1"
        self.assertTrue(dg.try_consume_behavioral_return_merge(signature=sig, ttl_seconds=60.0))
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertFalse(dg.try_consume_behavioral_return_merge(signature=sig, ttl_seconds=60.0))
        self.assertIn("duplicate_behavioral_merge", buf.getvalue())

    def test_cart_event_burst_suppresses_second(self) -> None:
        self.assertTrue(
            dg.should_process_cart_event_burst(
                store_slug="s",
                session_id="a",
                cart_id="b",
                event_norm="cart_abandoned",
                min_interval_seconds=1.0,
            )
        )
        self.assertFalse(
            dg.should_process_cart_event_burst(
                store_slug="s",
                session_id="a",
                cart_id="b",
                event_norm="cart_abandoned",
                min_interval_seconds=1.0,
            )
        )

    def test_lifecycle_conflict_log_line(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            dg.log_lifecycle_conflict_pattern(
                "send_after_return",
                recovery_key="rk",
                session_id="sid",
                cart_id="cid",
                step=1,
            )
        out = buf.getvalue()
        self.assertIn("[CARTFLOW DUPLICATE]", out)
        self.assertIn("lifecycle_conflict", out)
        self.assertIn("send_after_return", out)

    def test_runtime_health_duplicate_section(self) -> None:
        dg.note_recovery_schedule_duplicate(
            store_slug="demo",
            session_id="s",
            cart_id="c",
            recovery_key="rk",
        )
        snap = rh.build_runtime_health_snapshot()
        dpr = snap.get("duplicate_protection_runtime")
        self.assertIsInstance(dpr, dict)
        self.assertIn("duplicate_anomaly_count", dpr)
        self.assertIn("duplicate_send_blocked_recently", dpr)
        admin = rh.build_admin_runtime_summary()
        self.assertIn("duplicate_protection", admin)
        self.assertIn("duplicate_anomaly_count", admin["duplicate_protection"])

    def test_dashboard_blocker_duplicate_merchant_safe(self) -> None:
        d = get_recovery_blocker_display_state("duplicate_attempt_blocked")
        desc = str(d.get("description_ar") or "")
        self.assertIn("مكررة", desc)
        self.assertIn("إرسال", desc)

    def test_schedule_duplicate_after_memory_reset_integration(self) -> None:
        _reset_recovery_memory()
        buf = io.StringIO()
        with redirect_stdout(buf):
            dg.note_recovery_schedule_duplicate(
                store_slug="demo",
                session_id="s-int",
                cart_id="c-int",
                recovery_key="demo|s-int",
            )
        self.assertIn("recovery_schedule_duplicate", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
