# -*- coding: utf-8 -*-
"""
Conversion: POST /api/conversion and purchase_completed stop further recovery.

Manual: trigger step1, then POST /api/conversion; steps 2–3 must not send.
"""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from main import app


def _reset() -> None:
    with main._recovery_session_lock:
        main._session_recovery_started.clear()
        main._session_recovery_logged.clear()
        main._session_recovery_sent.clear()
        main._session_recovery_converted.clear()


class ConversionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset()
        self.client = TestClient(app)

    def test_post_conversion_marks_session(self) -> None:
        r = self.client.post(
            "/api/conversion",
            json={
                "store_slug": "demo",
                "session_id": "c-session-1",
                "purchase_completed": True,
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        j = r.json()
        self.assertTrue(j.get("ok"))
        self.assertIs(True, j.get("purchase_completed"))
        self.assertEqual(j.get("recovery_key"), "demo:c-session-1")
        self.assertTrue(
            main._is_user_converted("demo:c-session-1"),
        )

    def test_post_conversion_requires_fields(self) -> None:
        r = self.client.post("/api/conversion", json={})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json().get("ok"))


class ConversionStopsAsyncSequenceTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset()

    @patch("main.send_whatsapp_mock")
    @patch("main._persist_cart_recovery_log")
    def test_no_sends_if_converted_after_initial_delay(
        self, _mock_persist: object, mock_send: object
    ) -> None:
        _reset()
        main._mark_session_converted("demo", "no-send-1")
        k = "demo:no-send-1"

        async def run() -> None:
            await main._run_recovery_sequence_after_cart_abandoned(
                k, 0.0, "demo", "no-send-1", None
            )

        asyncio.run(run())
        mock_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
