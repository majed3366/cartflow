# -*- coding: utf-8 -*-
"""
Validation: WhatsApp queue + retry (order, success, retry, final fail, conversion, dedup).

Cart abandonment calls ``main.send_whatsapp`` (Layer D.3); queue retries / ``sent_real`` are
covered via direct ``enqueue_recovery_and_wait`` tests.
"""
from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
import services.whatsapp_queue as whatsapp_queue
from services.whatsapp_queue import (
    MAX_WA_SEND_ATTEMPTS,
    _queue_diagnostics_for_tests,
    enqueue_recovery_and_wait,
    start_whatsapp_queue_worker,
)
from tests.test_recovery_isolation import (
    _post_recovery_reason_for_session,
    _reset_recovery_memory,
)


def _abandon(store: str, session_id: str) -> dict:
    return {
        "event": "cart_abandoned",
        "store": store,
        "session_id": session_id,
        "cart": [{"name": "Item", "price": 10}],
        "phone": "9665333444555",
    }


class WhatsappQueueValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        os.environ["WHATSAPP_QUEUE_RETRY_BACKOFF_SECONDS"] = "0"

    @patch("main.should_send_whatsapp", return_value=True)
    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.get_recovery_delay", return_value=0)
    def test_1_queued_before_send(
        self, _d: object, mock_send: object, mock_persist: object, _gate: object
    ) -> None:
        """Abandoned cart: log queued before send_whatsapp."""
        order: list = []

        def track_persist(*_a, **kw) -> None:
            st = kw.get("status", "")
            order.append(f"persist:{st}")

        def track_sw(_phone: str, _message: str, **_kw: object) -> dict:
            order.append("send")
            return {"ok": True}

        mock_persist.side_effect = track_persist
        mock_send.side_effect = track_sw
        client = TestClient(app)
        _post_recovery_reason_for_session(client, "qval-1", "s1")
        client.post(
            "/api/cart-event",
            json=_abandon("qval-1", "s1"),
        )
        self.assertIn("persist:queued", order, order)
        self.assertIn("send", order, order)
        self.assertLess(
            order.index("persist:queued"),
            order.index("send"),
            "queued must be logged before send",
        )

    async def test_2_successful_send_sent_real(self) -> None:
        """Worker calls send_whatsapp_real; persistence gets sent_real."""
        statuses: list = []

        def cap(**kw) -> None:
            s = kw.get("status", "")
            if s:
                statuses.append(s)

        with patch.object(
            whatsapp_queue, "send_whatsapp_real", return_value={"ok": True}
        ):
            with patch("main._persist_cart_recovery_log", side_effect=cap):
                await start_whatsapp_queue_worker()
                await enqueue_recovery_and_wait(
                    store_slug="qval-2",
                    session_id="s2-q",
                    cart_id=None,
                    phone="9665788899900",
                    message="m",
                    step=1,
                    recovery_key="qval-2:s2-q",
                    use_real=True,
                )
        self.assertIn("sent_real", statuses, statuses)

    async def test_3_retry_on_failure_and_failed_retry_status(self) -> None:
        """Forced API failure: up to MAX attempts; failed_retry recorded."""
        statuses: list = []

        def cap(**kw) -> None:
            s = kw.get("status", "")
            if s:
                statuses.append(s)

        with patch.object(
            whatsapp_queue,
            "send_whatsapp_real",
            return_value={"ok": False, "error": "forced_fail"},
        ) as mock_real:
            with patch("main._persist_cart_recovery_log", side_effect=cap):
                await start_whatsapp_queue_worker()
                await enqueue_recovery_and_wait(
                    store_slug="qval-3",
                    session_id="s3-q",
                    cart_id=None,
                    phone="9665788899900",
                    message="m",
                    step=1,
                    recovery_key="qval-3:s3-q",
                    use_real=True,
                )

        self.assertEqual(mock_real.call_count, MAX_WA_SEND_ATTEMPTS)
        self.assertIn("failed_retry", statuses)
        self.assertIn("failed_final", statuses)

    async def test_4_failed_final_after_max_retries(self) -> None:
        """Repeated failures yield exactly one failed_final per exhausted job."""
        st_out: list = []

        def cap_collect(**kw) -> None:
            s = kw.get("status", "")
            if s:
                st_out.append(s)

        with patch.object(whatsapp_queue, "send_whatsapp_real", return_value={"ok": False}):
            with patch("main._persist_cart_recovery_log", side_effect=cap_collect):
                await start_whatsapp_queue_worker()
                await enqueue_recovery_and_wait(
                    store_slug="qval-4",
                    session_id="s4-q",
                    cart_id=None,
                    phone="9665788899900",
                    message="m",
                    step=1,
                    recovery_key="qval-4:s4-q",
                    use_real=True,
                )

        self.assertEqual(st_out.count("failed_final"), 1, f"one failed_final; got {st_out!r}")
        self.assertIn("failed_retry", st_out)

    @patch("main._persist_cart_recovery_log", autospec=True)
    @patch("main.send_whatsapp", autospec=True)
    @patch("main.get_recovery_delay", return_value=0)
    def test_5_conversion_stop_before_send(
        self, _d: object, mock_send: object, mock_persist: object
    ) -> None:
        """Convert first; abandon does not call send_whatsapp."""
        client = TestClient(app)
        r = client.post(
            "/api/conversion",
            json={
                "store_slug": "qval-5",
                "session_id": "s5",
                "purchase_completed": True,
            },
        )
        self.assertTrue(r.json().get("ok"), r.text)
        out = client.post(
            "/api/cart-event",
            json=_abandon("qval-5", "s5"),
        )
        self.assertEqual(200, out.status_code, out.text)
        j = out.json()
        self.assertEqual(j.get("recovery_state"), "converted")
        self.assertTrue(j.get("recovery_skipped"), j)
        st = [c.kwargs.get("status") for c in mock_persist.call_args_list if c.kwargs]
        self.assertIn("stopped_converted", st)
        mock_send.assert_not_called()

    async def test_5b_worker_stops_after_cooperative_yield(self) -> None:
        """
        Already converted when the job runs: worker skips API (pre-send check).
        """
        with patch("main._persist_cart_recovery_log", autospec=True) as mock_p:
            with patch("services.whatsapp_queue.send_whatsapp_real") as mock_r:
                with patch("main._is_user_converted", return_value=True):
                    await start_whatsapp_queue_worker()
                    o = await enqueue_recovery_and_wait(
                        store_slug="a",
                        session_id="b",
                        cart_id=None,
                        phone="0",
                        message="m2",
                        step=1,
                        recovery_key="a:b",
                        use_real=True,
                    )
                self.assertEqual(o, "stopped")
        mock_r.assert_not_called()
        st = [c.kwargs.get("status") for c in mock_p.call_args_list if c.kwargs]
        self.assertIn("stopped_converted", st)

    async def test_6_duplicate_protection_merges_enqueue(self) -> None:
        c = [0]

        def count_send(
            _use_real: object, _phone: str, _message: str, **_kw: object
        ) -> dict:  # noqa: ARG001
            c[0] += 1
            return {"ok": True}

        with patch("main._persist_cart_recovery_log"):
            with patch.object(whatsapp_queue, "_one_send", side_effect=count_send):
                await start_whatsapp_queue_worker()
                t1 = asyncio.create_task(
                    enqueue_recovery_and_wait(
                        store_slug="d6",
                        session_id="e6",
                        cart_id=None,
                        phone="0",
                        message="dupmsg",
                        step=1,
                        recovery_key="d6:e6",
                        use_real=True,
                    )
                )
                t2 = asyncio.create_task(
                    enqueue_recovery_and_wait(
                        store_slug="d6",
                        session_id="e6",
                        cart_id=None,
                        phone="0",
                        message="dupmsg",
                        step=1,
                        recovery_key="d6:e6",
                        use_real=True,
                    )
                )
                r1, r2 = await asyncio.gather(t1, t2)
        self.assertEqual(r1, "success")
        self.assertEqual(r2, "success")
        self.assertEqual(c[0], 1)
        nq, ni = _queue_diagnostics_for_tests()
        self.assertEqual(ni, 0)
        self.assertEqual(nq, 0)
