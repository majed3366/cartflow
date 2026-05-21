# -*- coding: utf-8 -*-
"""Recovery delay dispatcher — sole delay wait owner before execution boundary."""
from __future__ import annotations

import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import main  # noqa: F401

from extensions import db
from models import RecoverySchedule
from services.recovery_delay_dispatcher import dispatch_recovery_schedule
from services.recovery_restart_survival import (
    STATUS_SCHEDULED,
    persist_recovery_schedule_durable,
)


class RecoveryDelayDispatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        for row in db.session.query(RecoverySchedule).all():
            db.session.delete(row)
        db.session.commit()

    def _row(self) -> RecoverySchedule:
        rk = f"demo:disp-{uuid.uuid4().hex[:6]}"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-disp",
            cart_id="cart-disp",
            reason_tag="other",
            abandon_event_phone="+966501112233",
            delay_seconds_scheduled=120.0,
            schedule_timing={
                "effective_delay_seconds": 120.0,
                "source": "reason_templates.messages",
            },
            recovery_context={"recovery_key": rk, "store_slug": "demo"},
        )
        assert row is not None
        return row

    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch(
        "services.recovery_delay_dispatcher.execute_recovery_schedule",
        new_callable=AsyncMock,
        return_value={"ok": True, "reason": "finished"},
    )
    def test_dispatch_waits_then_executes(
        self, mock_exec: AsyncMock, mock_sleep: AsyncMock
    ) -> None:
        row = self._row()
        due = datetime.now(timezone.utc) + timedelta(seconds=45)
        row.due_at = due
        db.session.commit()
        out = asyncio.run(
            dispatch_recovery_schedule(int(row.id), due, "test_dispatch")
        )
        self.assertTrue(out["ok"])
        mock_sleep.assert_called_once()
        wait_arg = float(mock_sleep.call_args[0][0])
        self.assertGreater(wait_arg, 0.0)
        self.assertLess(wait_arg, 50.0)
        mock_exec.assert_called_once_with(
            schedule_id=int(row.id), source="test_dispatch"
        )

    @patch("main.asyncio.sleep", new_callable=AsyncMock)
    @patch(
        "services.recovery_delay_dispatcher.execute_recovery_schedule",
        new_callable=AsyncMock,
    )
    def test_dispatch_skips_terminal(
        self, mock_exec: AsyncMock, mock_sleep: AsyncMock
    ) -> None:
        row = self._row()
        row.status = "completed"
        db.session.commit()
        out = asyncio.run(
            dispatch_recovery_schedule(int(row.id), row.due_at, "test")
        )
        self.assertFalse(out["ok"])
        self.assertIn("already_terminal", out["reason"])
        mock_sleep.assert_not_called()
        mock_exec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
