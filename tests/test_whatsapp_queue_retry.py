# -*- coding: utf-8 -*-
"""
WhatsApp recovery queue: retries and statuses (failed_retry → failed_final).
"""
from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("WHATSAPP_QUEUE_RETRY_BACKOFF_SECONDS", "0")

from services.whatsapp_queue import (  # noqa: E402
    RecoveryWhatsappJob,
    _process_one_job,
)


class WhatsappQueueRetryTests(unittest.IsolatedAsyncioTestCase):
    @patch("services.whatsapp_queue._is_converted", return_value=False)
    @patch("main._persist_cart_recovery_log", autospec=True)
    @patch("services.whatsapp_queue._one_send", return_value={"ok": False})
    @patch("services.whatsapp_queue._persist")
    async def test_fails_out_after_max_attempts(
        self, m_persist_fn: object, _mock_ones: object, mock_persist: object, _ic: object
    ) -> None:
        m_persist_fn.return_value = mock_persist
        job = RecoveryWhatsappJob(
            store_slug="d",
            session_id="s",
            cart_id=None,
            phone="0",
            message="hi",
            step=1,
            recovery_key="d:s",
            use_real=True,
        )
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[str] = loop.create_future()
        await _process_one_job(job, fut)
        self.assertEqual(fut.result(), "failed_final")
        st = [c.kwargs.get("status") for c in mock_persist.call_args_list if c.kwargs]
        self.assertIn("failed_retry", st)
        self.assertIn("failed_final", st)
        self.assertEqual(st.count("failed_retry"), 2)
        self.assertEqual(st.count("failed_final"), 1)

    @patch("services.whatsapp_queue._is_converted", return_value=False)
    @patch("main._persist_cart_recovery_log", autospec=True)
    @patch(
        "services.whatsapp_queue._one_send",
        side_effect=[{"ok": False}, {"ok": False}, {"ok": True}],
    )
    @patch("services.whatsapp_queue._persist")
    async def test_succeeds_on_third_send(
        self, m_persist_fn: object, _os: object, mock_persist: object, _ic: object
    ) -> None:
        m_persist_fn.return_value = mock_persist
        job = RecoveryWhatsappJob(
            store_slug="d",
            session_id="s2",
            cart_id=None,
            phone="0",
            message="hi",
            step=1,
            recovery_key="d:s2",
            use_real=True,
        )
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        await _process_one_job(job, fut)
        self.assertEqual(fut.result(), "success")
        st = [c.kwargs.get("status") for c in mock_persist.call_args_list if c.kwargs]
        self.assertEqual(st.count("failed_retry"), 2)
        self.assertIn("sent_real", st)
