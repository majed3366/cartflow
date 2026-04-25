# -*- coding: utf-8 -*-
"""
Verifies recovery keys are scoped by store_slug + session_id.

Manual flow (browser): /demo/store/cart then /demo/store2/cart with cart abandon.
This module asserts the same via POST /api/cart-event.

When tests pass: isolation between demo and demo2 is confirmed (no cross-store
"recovery already scheduled, skipping").
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import (
    _recovery_session_lock,
    _session_recovery_converted,
    _session_recovery_logged,
    _session_recovery_sent,
    _session_recovery_started,
    app,
)


def _reset_recovery_memory() -> None:
    with _recovery_session_lock:
        _session_recovery_started.clear()
        _session_recovery_logged.clear()
        _session_recovery_sent.clear()
        _session_recovery_converted.clear()


class RecoveryIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    @patch("main._persist_cart_recovery_log")
    @patch("services.whatsapp_queue.send_whatsapp_mock")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_demo_then_demo2_same_session_both_schedule(
        self, _mock_delay: object, _ur: object, _mock_wa: object, _mock_persist: object
    ) -> None:
        _mock_wa.return_value = {"ok": True}
        sid = "isol-session-verify-1"
        cart = [{"name": "Test", "price": 1}]
        base = {"event": "cart_abandoned", "session_id": sid, "cart": cart}

        r_demo = self.client.post(
            "/api/cart-event",
            json={**base, "store": "demo"},
        )
        self.assertEqual(r_demo.status_code, 200, r_demo.text)
        j_demo = r_demo.json()
        self.assertTrue(j_demo.get("recovery_scheduled"), j_demo)
        self.assertEqual(j_demo.get("recovery_state"), "scheduled")

        r_demo2 = self.client.post(
            "/api/cart-event",
            json={**base, "store": "demo2"},
        )
        self.assertEqual(r_demo2.status_code, 200, r_demo2.text)
        j2 = r_demo2.json()
        self.assertTrue(
            j2.get("recovery_scheduled"),
            "demo2 must schedule independently of demo; got: %r" % (j2,),
        )
        self.assertEqual(j2.get("recovery_state"), "scheduled")

        r_demo_again = self.client.post(
            "/api/cart-event",
            json={**base, "store": "demo"},
        )
        self.assertEqual(
            r_demo_again.json().get("recovery_state"),
            "sent",
            "second demo should be blocked after first completes",
        )

        r_demo2_again = self.client.post(
            "/api/cart-event",
            json={**base, "store": "demo2"},
        )
        self.assertEqual(r_demo2_again.json().get("recovery_state"), "sent")

    def test_recovery_key_format_demo_and_demo2(self) -> None:
        from main import _recovery_key_from_payload

        sid = "k-1"
        cart = [{"n": 1}]
        self.assertEqual(
            _recovery_key_from_payload(
                {"store": "demo", "session_id": sid, "cart": cart}
            ),
            "demo:k-1",
        )
        self.assertEqual(
            _recovery_key_from_payload(
                {"store": "demo2", "session_id": sid, "cart": cart}
            ),
            "demo2:k-1",
        )


if __name__ == "__main__":
    unittest.main()
