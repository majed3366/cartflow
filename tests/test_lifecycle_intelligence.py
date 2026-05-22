# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import AsyncMock, patch

from services.lifecycle_intelligence import (
    BEHAVIOR_CUSTOMER_REPLIED,
    BEHAVIOR_IGNORED,
    BEHAVIOR_PURCHASE_COMPLETED,
    BEHAVIOR_RETURNED_TO_SITE,
    DECISION_CONTINUE,
    DECISION_FALLBACK,
    DECISION_HANDOFF,
    DECISION_STOP,
    decide_lifecycle_recovery,
    log_lifecycle_decision,
)


class LifecycleIntelligenceDecisionTests(unittest.TestCase):
    def test_returned_to_site_stops_recovery(self) -> None:
        r = decide_lifecycle_recovery(returned=True, attempt_count=1)
        self.assertEqual(r["behavior"], BEHAVIOR_RETURNED_TO_SITE)
        self.assertEqual(r["decision"], DECISION_STOP)
        self.assertEqual(r["reason"], "user_returned")
        self.assertEqual(r["action"], "no_send")

    def test_purchase_completed_stops_and_closes_lifecycle(self) -> None:
        r = decide_lifecycle_recovery(purchased=True, attempt_count=2)
        self.assertEqual(r["behavior"], BEHAVIOR_PURCHASE_COMPLETED)
        self.assertEqual(r["decision"], DECISION_STOP)
        self.assertEqual(r["action"], "close_lifecycle")

    def test_purchase_beats_returned(self) -> None:
        r = decide_lifecycle_recovery(returned=True, purchased=True)
        self.assertEqual(r["behavior"], BEHAVIOR_PURCHASE_COMPLETED)
        self.assertEqual(r["decision"], DECISION_STOP)

    def test_customer_replied_handoff(self) -> None:
        r = decide_lifecycle_recovery(replied=True, attempt_count=1)
        self.assertEqual(r["behavior"], BEHAVIOR_CUSTOMER_REPLIED)
        self.assertEqual(r["decision"], DECISION_HANDOFF)
        self.assertEqual(r["action"], "handoff_continuation")

    def test_ignored_continues_with_next_step(self) -> None:
        r = decide_lifecycle_recovery(ignored=True, attempt_count=1)
        self.assertEqual(r["behavior"], BEHAVIOR_IGNORED)
        self.assertEqual(r["decision"], DECISION_CONTINUE)
        self.assertEqual(r["next_step"], "attempt_2")

    def test_unknown_fallback_uses_reason_tag(self) -> None:
        r = decide_lifecycle_recovery(reason_tag="shipping")
        self.assertEqual(r["decision"], DECISION_FALLBACK)
        self.assertIn("shipping", r["reason"])

    def test_log_emits_decision_and_action_lines(self) -> None:
        r = decide_lifecycle_recovery(returned=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            log_lifecycle_decision(r, session_id="sess-1")
        out = buf.getvalue()
        self.assertIn("[LIFECYCLE DECISION]", out)
        self.assertIn("behavior=returned_to_site", out)
        self.assertIn("decision=STOP", out)
        self.assertIn("[LIFECYCLE ACTION]", out)
        self.assertIn("action=no_send", out)


class LifecycleIntelligenceDevDelayIntegrationTests(unittest.TestCase):
    """Real dev-delay path: lifecycle logs precede anti-spam; send blocked when STOP."""

    def setUp(self) -> None:
        import os

        os.environ.setdefault("CARTFLOW_ADMIN_PASSWORD", "test-admin-pass")
        from main import app

        self.app = app
        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

    @patch("main.send_whatsapp")
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    def test_simulate_return_logs_stop_and_blocks_send(
        self, _sleep: AsyncMock, mock_send: object
    ) -> None:
        import asyncio
        import io
        from contextlib import redirect_stdout

        from main import _run_dev_cartflow_delay_test_send

        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(
                _run_dev_cartflow_delay_test_send(
                    0.0,
                    "+966500000001",
                    "price",
                    simulate_user_return=True,
                    simulate_purchase=False,
                )
            )
        out = buf.getvalue()
        self.assertIn("[LIFECYCLE DECISION]", out)
        self.assertIn("decision=STOP", out)
        self.assertIn("behavior=returned_to_site", out)
        self.assertIn("should_send=", out)
        self.assertRegex(out, r"should_send=\s*False")
        mock_send.assert_not_called()

    @patch("main.send_whatsapp")
    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    def test_simulate_purchase_logs_stop_close_and_blocks_send(
        self, _sleep: AsyncMock, mock_send: object
    ) -> None:
        import asyncio
        import io
        from contextlib import redirect_stdout

        from main import _run_dev_cartflow_delay_test_send

        buf = io.StringIO()
        with redirect_stdout(buf):
            asyncio.run(
                _run_dev_cartflow_delay_test_send(
                    0.0,
                    "+966500000002",
                    "price",
                    simulate_user_return=False,
                    simulate_purchase=True,
                )
            )
        out = buf.getvalue()
        self.assertIn("decision=STOP", out)
        self.assertIn("close_lifecycle", out)
        self.assertIn("behavior=purchase_completed", out)
        mock_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
