# -*- coding: utf-8 -*-
"""
Validation: WhatsApp queue + retry (order, success, retry, final fail, conversion, dedup).
"""
from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.whatsapp_queue import (
    _queue_diagnostics_for_tests,
    enqueue_recovery_and_wait,
    start_whatsapp_queue_worker,
)
from tests.test_recovery_isolation import _reset_recovery_memory


def _abandon(store: str, session_id: str) -> dict:
    return {
        "event": "cart_abandoned",
        "store": store,
        "session_id": session_id,
        "cart": [{"name": "Item", "price": 10}],
    }


class WhatsappQueueValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        os.environ["WHATSAPP_QUEUE_RETRY_BACKOFF_SECONDS"] = "0"

    @patch("main._persist_cart_recovery_log")
    @patch("services.whatsapp_queue.send_whatsapp_real")
    @patch("main.recovery_uses_real_whatsapp", return_value=True)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_1_queued_before_send(
        self, _d: object, _ur: object, mock_real: object, mock_persist: object
    ) -> None:
        """Trigger recovery: log status=queued before any API send (first step)."""
        order: list = []

        def track_persist(*_a, **kw) -> None:
            st = kw.get("status", "")
            order.append(f"persist:{st}")

        def track_send(_phone: str, _message: str) -> dict:
            order.append("send")
            return {"ok": True}

        mock_persist.side_effect = track_persist
        mock_real.side_effect = track_send
        client = TestClient(app)
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

    @patch("main._persist_cart_recovery_log")
    @patch("services.whatsapp_queue.send_whatsapp_real")
    @patch("main.recovery_uses_real_whatsapp", return_value=True)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_2_successful_send_sent_real(
        self, _d: object, _ur: object, mock_real: object, mock_persist: object
    ) -> None:
        """Worker runs send; log includes sent_real."""
        mock_real.return_value = {"ok": True}
        statuses: list = []

        def cap(**kw) -> None:
            s = kw.get("status", "")
            if s:
                statuses.append(s)

        mock_persist.side_effect = cap
        client = TestClient(app)
        client.post(
            "/api/cart-event",
            json=_abandon("qval-2", "s2"),
        )
        self.assertIn("sent_real", statuses, statuses)
        self.assertIn("queued", statuses)
        mock_real.assert_called()

    @patch("main._persist_cart_recovery_log")
    @patch("services.whatsapp_queue.send_whatsapp_real")
    @patch("main.recovery_uses_real_whatsapp", return_value=True)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_3_retry_on_failure_and_failed_retry_status(
        self, _d: object, _ur: object, mock_real: object, mock_persist: object
    ) -> None:
        """Force API failure: up to 3 attempts, failed_retry appears."""
        mock_real.return_value = {"ok": False, "error": "forced_fail"}
        statuses: list = []

        def cap(**kw) -> None:
            s = kw.get("status", "")
            if s:
                statuses.append(s)

        mock_persist.side_effect = cap
        client = TestClient(app)
        client.post(
            "/api/cart-event",
            json=_abandon("qval-3", "s3"),
        )
        self.assertEqual(mock_real.call_count, 3, "three attempts for one job")
        self.assertIn("failed_retry", statuses, statuses)
        self.assertIn("failed_final", statuses, statuses)

    @patch("main._persist_cart_recovery_log")
    @patch("services.whatsapp_queue.send_whatsapp_real")
    @patch("main.recovery_uses_real_whatsapp", return_value=True)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_4_failed_final_after_max_retries(
        self, _d: object, _ur: object, mock_real: object, mock_persist: object
    ) -> None:
        """With failures kept, exactly one failed_final in logs per failed step job."""
        mock_real.return_value = {"ok": False}
        st_out: list = []

        def cap(**kw) -> None:
            s = kw.get("status", "")
            if s:
                st_out.append(s)

        mock_persist.side_effect = cap
        client = TestClient(app)
        client.post(
            "/api/cart-event",
            json=_abandon("qval-4", "s4"),
        )
        self.assertEqual(
            st_out.count("failed_final"), 1, f"one failed_final; got {st_out!r}"
        )
        self.assertIn("failed_retry", st_out, st_out)

    @patch("main._persist_cart_recovery_log", autospec=True)
    @patch("services.whatsapp_queue.send_whatsapp_real", autospec=True)
    @patch("main.recovery_uses_real_whatsapp", return_value=True)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_5_conversion_stop_before_send(
        self, _d: object, _ur: object, mock_real: object, mock_persist: object
    ) -> None:
        """
        POST /api/conversion (same store_slug + session_id) before cart abandons:
        recovery is skipped, log includes stopped_converted, no WhatsApp send.
        """
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
        self.assertIn(
            j.get("recovery_state"),
            ("converted",),
        )
        self.assertTrue(j.get("recovery_skipped"), j)
        st = [c.kwargs.get("status") for c in mock_persist.call_args_list if c.kwargs]
        self.assertIn("stopped_converted", st, st)
        mock_real.assert_not_called()

    async def test_5b_worker_stops_after_cooperative_yield(
        self,
    ) -> None:
        """
        If already converted when the job runs, queue worker does not call the API
        (see asyncio.sleep(0) + pre-send check in whatsapp_queue); log = stopped_converted.
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
                self.assertEqual(o, "stopped", o)
        mock_r.assert_not_called()
        st = [c.kwargs.get("status") for c in mock_p.call_args_list if c.kwargs]
        self.assertIn("stopped_converted", st, st)

    async def test_6_duplicate_protection_merges_enqueue(
        self,
    ) -> None:
        c = [0]

        def count_send(
            _use_real: object, _phone: str, _message: str
        ) -> dict:  # noqa: ARG001
            c[0] += 1
            return {"ok": True}

        with patch("main._persist_cart_recovery_log"):
            with patch("services.whatsapp_queue._one_send", side_effect=count_send):
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
        self.assertEqual(r1, "success", r1)
        self.assertEqual(r2, "success", r2)
        self.assertEqual(c[0], 1, "one logical _one_send for two duplicate enqueues")
        nq, ni = _queue_diagnostics_for_tests()
        self.assertEqual(ni, 0, "inflight map cleared after completion")
        self.assertEqual(nq, 0, "queue drained after completion")
