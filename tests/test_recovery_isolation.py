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
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import (
    _dev_delay_test_send_count,
    _recovery_session_lock,
    _session_recovery_converted,
    _session_recovery_logged,
    _session_recovery_multi_attempt_cap,
    _session_recovery_multi_logged,
    _session_recovery_multi_verified_indexes,
    _session_recovery_followup_next_due_at,
    _session_recovery_last_second_skip_reason,
    _session_recovery_returned,
    _session_recovery_send_count,
    _session_recovery_sent,
    _session_recovery_seq_logged,
    _session_recovery_started,
    app,
)
from models import CartRecoveryReason
from services.recovery_session_phone import recovery_phone_memory_clear


def _reset_recovery_memory() -> None:
    with _recovery_session_lock:
        _session_recovery_started.clear()
        _session_recovery_logged.clear()
        _session_recovery_sent.clear()
        _session_recovery_converted.clear()
        _session_recovery_returned.clear()
        _session_recovery_send_count.clear()
        _session_recovery_multi_logged.clear()
        _session_recovery_multi_attempt_cap.clear()
        _session_recovery_multi_verified_indexes.clear()
        _dev_delay_test_send_count.clear()
        _session_recovery_seq_logged.clear()
        _session_recovery_followup_next_due_at.clear()
        _session_recovery_last_second_skip_reason.clear()
    recovery_phone_memory_clear()
    try:
        from services.cartflow_duplicate_guard import reset_duplicate_guard_for_tests
        from services.cartflow_lifecycle_guard import reset_lifecycle_guard_for_tests

        reset_duplicate_guard_for_tests()
        reset_lifecycle_guard_for_tests()
    except Exception:
        pass


def _post_recovery_reason_for_session(
    client: TestClient,
    store_slug: str,
    session_id: str,
    reason_tag: str = "price",
    customer_phone: Optional[str] = None,
) -> None:
    """Persist widget reason so delayed recovery has reason_tag + updated_at (last_activity)."""
    r = client.post(
        "/api/cart-recovery/reason",
        json={
            "store_slug": store_slug,
            "session_id": session_id,
            "reason_tag": reason_tag,
        },
    )
    if r.status_code != 200:
        raise AssertionError(f"reason POST failed {r.status_code}: {r.text}")

    db.create_all()
    aged = datetime.now(timezone.utc) - timedelta(hours=3)
    patch_row: dict = {"updated_at": aged, "created_at": aged}
    if customer_phone is not None:
        patch_row["customer_phone"] = customer_phone
    upd = (
        db.session.query(CartRecoveryReason)
        .filter(
            CartRecoveryReason.store_slug == store_slug,
            CartRecoveryReason.session_id == session_id,
        )
        .update(patch_row, synchronize_session=False)
    )
    if int(upd or 0) < 1:
        raise AssertionError(
            f"CartRecoveryReason missing after POST store_slug={store_slug!r} "
            f"session_id={session_id!r}"
        )
    db.session.commit()


class RecoveryIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    @patch("main.should_send_whatsapp", return_value=True)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_demo_then_demo2_same_session_both_schedule(
        self, _mock_delay: object, _ur: object, _mock_wa: object, _mock_persist: object, _gate: object
    ) -> None:
        _mock_wa.return_value = {"ok": True}
        sid = "isol-session-verify-1"
        cart = [{"name": "Test", "price": 1}]
        base = {"event": "cart_abandoned", "session_id": sid, "cart": cart}

        _post_recovery_reason_for_session(
            self.client,
            "demo",
            sid,
            customer_phone="9665444555666",
        )
        r_demo = self.client.post(
            "/api/cart-event",
            json={**base, "store": "demo"},
        )
        self.assertEqual(r_demo.status_code, 200, r_demo.text)
        j_demo = r_demo.json()
        self.assertTrue(j_demo.get("recovery_scheduled"), j_demo)
        self.assertEqual(j_demo.get("recovery_state"), "scheduled")

        _post_recovery_reason_for_session(self.client, "demo2", sid)
        r_demo2 = self.client.post(
            "/api/cart-event",
            json={**base, "store": "demo2", "phone": "9665444555666"},
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
